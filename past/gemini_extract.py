#!/usr/bin/env python3
"""
Extract articles from a Railsplitter PDF using Gemini Vision.

Sends all PDF pages as images in a single Gemini request, letting the model
resolve multi-page articles internally. Writes a draft JSON file by default;
use --apply to merge into content.json.

Usage:
    GEMINI_API_KEY=<key> python3 gemini_extract.py <pdf> [options]

    # Dry run — inspect draft JSON before committing anything:
    python3 gemini_extract.py past/RailsplitterIssue3December2026.pdf

    # Merge into content.json after reviewing the draft:
    python3 gemini_extract.py past/RailsplitterIssue3December2026.pdf --apply

    # Skip the interactive issue-metadata prompt:
    python3 gemini_extract.py my.pdf --issue-id issue-3 --issue-date "December 2025"

Requires:
    pip install google-genai pdf2image Pillow
    export GEMINI_API_KEY=<your key from https://aistudio.google.com/>

Model note:
    Default model is gemini-2.5-flash-lite. If that ID is not yet GA, try
    gemini-2.5-flash or pass --model with a specific preview ID.
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CONTENT_JSON = Path(__file__).parent.parent / 'content.json'
VALIDATE_SCRIPT = Path(__file__).parent.parent / '.github' / 'scripts' / 'validate_content.py'

VALID_SECTIONS = {'news', 'features', 'opinion', 'sports', 'reviews'}

EXTRACT_PROMPT = """\
You are extracting articles from a scanned student newspaper called The Railsplitter \
published by Lincoln High School in Los Angeles, CA.

I am providing ALL pages of one issue in order. Extract EVERY article from the entire issue.

For each article return a JSON object with these exact fields:
- "title": The headline (string, required)
- "dek": Subheadline/deck text beneath the headline if present, else null
- "author": Author name only, without "By" / "Written By" prefix (string or null)
- "section": Exactly one of: "news", "features", "opinion", "sports", "reviews" — \
infer from section banner or article content
- "body": Complete article text as HTML using only <p>...</p> tags, \
one paragraph per tag (string, required)
- "credit": Photo credit if visible near an image (string or null)
- "low_confidence": true if you are uncertain about the title, section, \
or accuracy of the body text; false otherwise

Rules:
1. Newspaper text flows in columns — read each column top-to-bottom, left to right
2. An article may span multiple pages — combine all of its text into one "body" field
3. Skip: front-page nameplate, table of contents, ads, staff boxes, \
pull quotes that duplicate body text, page numbers, headers/footers
4. Do not repeat text that already appeared in another article
5. Strip line-break hyphens, OCR artifacts, and stray characters from body text
6. Return ONLY a valid JSON array — no markdown fences, no explanation, no trailing text

Example:
[{"title":"Students Rally for New Gym","dek":"Over 300 students signed petition",\
"author":"Jane Smith","section":"news",\
"body":"<p>First paragraph.</p><p>Second paragraph.</p>",\
"credit":null,"low_confidence":false}]"""


# ---------------------------------------------------------------------------
# Issue metadata helpers
# ---------------------------------------------------------------------------

_FNAME_ISSUE_RE = re.compile(r'Issue\s*#?(\d+)([A-Za-z]+)?(\d{4})', re.IGNORECASE)
_FNAME_YEAR_ISSUE_RE = re.compile(r'(\d{4}).*?Issue\s*#?(\d+)', re.IGNORECASE)


def parse_issue_from_filename(stem: str) -> dict | None:
    m = _FNAME_ISSUE_RE.search(stem)
    if m and int(m.group(1)) <= 20:
        number = m.group(1)
        season = (m.group(2) or '').strip()
        year = m.group(3)
        date_str = f'{season} {year}'.strip() if season else year
        return {'id': f'issue-{number}', 'title': f'Issue {number}', 'date': date_str}
    m = _FNAME_YEAR_ISSUE_RE.search(stem)
    if m and int(m.group(2)) <= 20:
        year, number = m.group(1), m.group(2)
        return {'id': f'issue-{number}', 'title': f'Issue {number}', 'date': year}
    return None


def confirm_issue_metadata(detected: dict | None, pdf_stem: str) -> dict:
    if detected:
        print(f'\nDetected issue metadata from "{pdf_stem}":')
        print(f'  ID:    {detected["id"]}')
        print(f'  Title: {detected["title"]}')
        print(f'  Date:  {detected["date"]}')
        ans = input('Is this correct? [Y/n] ').strip().lower()
        if ans in ('', 'y', 'yes'):
            return detected

    print('\nEnter issue details manually:')
    issue_id = input('  Issue ID (e.g. issue-3): ').strip()
    if not issue_id:
        print('Error: issue ID is required.')
        sys.exit(1)
    default_title = issue_id.replace('-', ' ').title()
    issue_title = input(f'  Issue title [{default_title}]: ').strip() or default_title
    issue_date = input('  Issue date (e.g. December 2025): ').strip()
    if not issue_date:
        print('Error: issue date is required.')
        sys.exit(1)
    return {'id': issue_id, 'title': issue_title, 'date': issue_date}


# ---------------------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------------------

def _make_schema(types):
    return types.Schema(
        type=types.Type.ARRAY,
        items=types.Schema(
            type=types.Type.OBJECT,
            properties={
                'title': types.Schema(type=types.Type.STRING),
                'dek': types.Schema(type=types.Type.STRING, nullable=True),
                'author': types.Schema(type=types.Type.STRING, nullable=True),
                'section': types.Schema(type=types.Type.STRING),
                'body': types.Schema(type=types.Type.STRING),
                'credit': types.Schema(type=types.Type.STRING, nullable=True),
                'low_confidence': types.Schema(type=types.Type.BOOLEAN),
            },
            required=['title', 'section', 'body', 'low_confidence'],
        ),
    )


def _call_batch(client, batch: list, model: str, config, label: str) -> list:
    last_err = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[*batch, EXTRACT_PROMPT],
                config=config,
            )
            return json.loads(response.text)
        except Exception as exc:
            last_err = exc
            if attempt < 2:
                wait = 4 * (attempt + 1)
                print(f'    {label} attempt {attempt + 1} failed: {exc}. Waiting {wait}s...')
                time.sleep(wait)
    raise RuntimeError(f'{label} failed after 3 attempts: {last_err}') from last_err


def _call_batch_splitting(client, batch: list, model: str, config, label: str) -> list:
    """Call Gemini on a batch; if it fails, split the batch in half and retry each half."""
    try:
        return _call_batch(client, batch, model, config, label)
    except RuntimeError:
        if len(batch) <= 1:
            raise
        mid = len(batch) // 2
        print(f'    {label}: splitting into 2 sub-batches ({mid} + {len(batch) - mid} pages)')
        left = _call_batch_splitting(client, batch[:mid], model, config, f'{label}a')
        right = _call_batch_splitting(client, batch[mid:], model, config, f'{label}b')
        return left + right


def call_gemini(images: list, model: str, api_key: str, batch_size: int = 5) -> list:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        print('Error: google-genai is not installed.')
        print('  Run: pip install google-genai')
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=_make_schema(types),
        max_output_tokens=65536,
    )

    # Split pages into batches to stay within output token limits.
    # 1-page overlap between batches catches articles that span a boundary.
    batches: list[list] = []
    i = 0
    while i < len(images):
        end = min(i + batch_size, len(images))
        batches.append(images[i:end])
        if end == len(images):
            break
        i = end - 1  # overlap last page of this batch into next

    total = len(batches)
    print(f'  {len(images)} page(s) → {total} batch(es) of up to {batch_size}')

    all_articles: list = []
    for idx, batch in enumerate(batches):
        start_page = sum(len(b) for b in batches[:idx]) - idx + 1
        label = f'Batch {idx + 1}/{total}'
        print(f'  {label}...')
        articles = _call_batch_splitting(client, batch, model, config, label)
        all_articles.extend(articles)

    return all_articles


# ---------------------------------------------------------------------------
# Article building
# ---------------------------------------------------------------------------

_BYLINE_PARA_RE = re.compile(
    r'^<p>\s*(?:Written\s+By|BY|By)\s+[^<]{1,80}</p>\s*', re.IGNORECASE
)
_BY_PREFIX_RE = re.compile(r'^(?:Written\s+By|BY|By)\s+', re.IGNORECASE)
_STRIP_TAGS_RE = re.compile(r'<[^>]+>')


def _dek_from_body(html: str) -> str:
    """Extract a short dek from body HTML when the article has no subheadline."""
    text = _STRIP_TAGS_RE.sub(' ', html).strip()
    # Take up to first sentence boundary within 150 chars
    for end in range(min(150, len(text)), 30, -1):
        if text[end - 1] in '.!?':
            return text[:end].strip()
    return text[:120].rsplit(' ', 1)[0].strip() + '…' if len(text) > 120 else text


def sanitize_body(html: str) -> str:
    if not html:
        return ''
    html = html.strip()
    if not html.startswith('<p>'):
        html = f'<p>{html}</p>'
    # Strip any tags other than <p> and </p>
    html = re.sub(r'<(?!/?p[ >])[^>]*>', '', html)
    # Strip leading "By [author]" paragraph that Gemini sometimes adds
    html = _BYLINE_PARA_RE.sub('', html)
    return html.strip()


def strip_by_prefix(name: str | None) -> str | None:
    if not name:
        return name
    return _BY_PREFIX_RE.sub('', name.strip()).strip() or None


def build_articles(raw_list: list, issue: dict, base_ts: int) -> tuple[list[dict], list[str]]:
    """Convert Gemini output to content.json article format.
    Returns (articles, warnings).
    """
    articles: list[dict] = []
    warnings: list[str] = []

    # Collect existing article IDs to avoid timestamp collisions
    try:
        existing_ids = {a['id'] for a in json.loads(CONTENT_JSON.read_text())['articles']}
    except Exception:
        existing_ids = set()

    seen_titles: set[str] = set()
    ts = base_ts
    for i, raw in enumerate(raw_list):
        title = (raw.get('title') or '').strip()
        if not title:
            warnings.append(f'Item {i + 1}: missing title — skipped')
            continue

        # Deduplicate by normalized title (Gemini re-extracts continuation pages)
        norm_title = re.sub(r'[^a-z0-9]', '', title.lower())
        if norm_title in seen_titles:
            warnings.append(f'Duplicate skipped: "{title}"')
            continue
        seen_titles.add(norm_title)

        section = (raw.get('section') or '').lower().strip()
        if section not in VALID_SECTIONS:
            warnings.append(f'"{title}": unknown section "{section}" → defaulting to "news"')
            section = 'news'

        raw_author = strip_by_prefix(raw.get('author'))
        author = (raw_author or '').strip() or 'The Railsplitter'
        dek = (raw.get('dek') or '').strip()
        body = sanitize_body(raw.get('body') or '')
        if not dek:
            dek = _dek_from_body(body) if body else title
        credit = (raw.get('credit') or '').strip() or 'The Railsplitter'
        low_conf = bool(raw.get('low_confidence', False))

        if not body:
            warnings.append(f'"{title}": empty body — marking low_confidence')
            low_conf = True

        # Generate a unique ID (increment until clear of existing)
        while f'article-{ts}' in existing_ids:
            ts += 1
        article_id = f'article-{ts}'
        existing_ids.add(article_id)
        ts += 1

        article: dict = {
            'id': article_id,
            'title': title,
            'author': author,
            'section': section,
            'issue': f'{issue["title"]}, {issue["date"]}',
            'issueId': issue['id'],
            'dek': dek,
            'body': body,
            'ph': f'img-ph--{section}',
            'credit': credit,
            'published': not low_conf,
        }
        if low_conf:
            article['low_confidence'] = True

        articles.append(article)

    return articles, warnings


# ---------------------------------------------------------------------------
# content.json merge
# ---------------------------------------------------------------------------

def validate_against_script(merged_path: Path) -> bool:
    if not VALIDATE_SCRIPT.exists():
        return True
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(merged_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print('  Validation output:')
        for line in (result.stdout + result.stderr).splitlines()[:30]:
            print(f'    {line}')
    return result.returncode == 0


def apply_to_content_json(articles: list[dict], issue: dict) -> int:
    """Merge articles and issue into content.json. Returns count of articles added."""
    import tempfile

    data = json.loads(CONTENT_JSON.read_text(encoding='utf-8'))
    existing_article_ids = {a['id'] for a in data['articles']}
    existing_issue_ids = {i['id'] for i in data['issues']}

    new_articles = [a for a in articles if a['id'] not in existing_article_ids]

    # Validate against a temp merged copy first
    merged = dict(data)
    merged['articles'] = data['articles'] + new_articles
    if issue['id'] not in existing_issue_ids:
        merged['issues'] = data['issues'] + [{
            'id': issue['id'],
            'title': issue['title'],
            'date': issue['date'],
            'coverArticle': articles[0]['id'] if articles else '',
        }]

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    ) as tf:
        json.dump(merged, tf, indent=2, ensure_ascii=False)
        temp_path = Path(tf.name)

    print('  Validating merged content.json...')
    ok = validate_against_script(temp_path)
    temp_path.unlink(missing_ok=True)

    if not ok:
        print('  Validation failed — not applying. Fix warnings above, then retry.')
        sys.exit(1)
    print('  Validation passed.')

    # Backup
    backup = CONTENT_JSON.with_suffix('.json.bak')
    shutil.copy2(CONTENT_JSON, backup)
    print(f'  Backed up → {backup.name}')

    # Write
    CONTENT_JSON.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding='utf-8'
    )
    return len(new_articles)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract articles from a Railsplitter PDF using Gemini Vision',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Set GEMINI_API_KEY env var before running.',
    )
    parser.add_argument('pdf', help='Path to the PDF file')
    parser.add_argument('--issue-id', help='Issue ID, e.g. issue-3')
    parser.add_argument('--issue-title', help='Issue title, e.g. "Issue 3"')
    parser.add_argument('--issue-date', help='Issue date, e.g. "December 2025"')
    parser.add_argument(
        '--model', default='gemini-2.5-flash-lite',
        help='Gemini model ID (default: gemini-2.5-flash-lite)',
    )
    parser.add_argument(
        '--dpi', type=int, default=200,
        help='PDF render DPI (default: 200; increase to 300 for better quality)',
    )
    parser.add_argument(
        '--batch-size', type=int, default=5,
        help='Pages per Gemini API call (default: 5; reduce if you get truncation errors)',
    )
    parser.add_argument(
        '--output',
        help='Draft output path (default: past/draft-<pdf-stem>.json)',
    )
    parser.add_argument(
        '--apply', action='store_true',
        help='Merge draft into content.json (default is dry-run only)',
    )
    args = parser.parse_args()

    api_key = os.environ.get('GEMINI_API_KEY', 'AIzaSyCe1eJyvKVZw5Y3SSgQDx70GbpJ4RtIhNo')

    # PDF check
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f'Error: PDF not found: {pdf_path}')
        sys.exit(1)

    # Output path
    output_path = (
        Path(args.output)
        if args.output
        else Path(__file__).parent / f'draft-{pdf_path.stem}.json'
    )

    # Issue metadata
    if args.issue_id and args.issue_date:
        issue = {
            'id': args.issue_id,
            'title': args.issue_title or args.issue_id.replace('-', ' ').title(),
            'date': args.issue_date,
        }
        print(f'Issue: {issue["title"]}, {issue["date"]} ({issue["id"]})')
    else:
        partial: dict | None = None
        if args.issue_id or args.issue_title or args.issue_date:
            partial = parse_issue_from_filename(pdf_path.stem) or {}
            if args.issue_id:
                partial['id'] = args.issue_id
            if args.issue_title:
                partial['title'] = args.issue_title
            if args.issue_date:
                partial['date'] = args.issue_date
        else:
            partial = parse_issue_from_filename(pdf_path.stem)
        issue = confirm_issue_metadata(partial, pdf_path.stem)

    # Convert PDF to images
    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        print('Error: pdf2image not installed. Run: pip install pdf2image')
        sys.exit(1)

    print(f'\nConverting {pdf_path.name} ({args.dpi} DPI)...')
    images = convert_from_path(str(pdf_path), dpi=args.dpi)
    print(f'  {len(images)} page(s) loaded')

    # Call Gemini (returns parsed list via JSON output mode)
    print(f'\nCalling Gemini ({args.model})...')
    raw_articles = call_gemini(images, args.model, api_key, batch_size=args.batch_size)
    print(f'  {len(raw_articles)} article(s) extracted')

    # Build content.json-shaped articles
    base_ts = int(time.time() * 1000)
    articles, warnings = build_articles(raw_articles, issue, base_ts)

    if warnings:
        print('\nWarnings:')
        for w in warnings:
            print(f'  ⚠  {w}')

    # Write draft
    draft = {
        '_note': 'Review this file before running with --apply.',
        'issue': issue,
        'model': args.model,
        'source_pdf': str(pdf_path.resolve()),
        'extracted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'articles': articles,
    }
    output_path.write_text(json.dumps(draft, indent=2, ensure_ascii=False), encoding='utf-8')

    low_conf = sum(1 for a in articles if a.get('low_confidence'))
    ready = len(articles) - low_conf
    print(f'\nDraft → {output_path}')
    print(f'  {len(articles)} article(s): {ready} ready (published=true), {low_conf} flagged (published=false)')

    if not args.apply:
        print('\nDry run complete. Review the draft, then rerun with --apply to merge into content.json.')
        return

    # Apply
    print('\nApplying to content.json...')
    added = apply_to_content_json(articles, issue)
    print(f'  Done — {added} new article(s) added.')


if __name__ == '__main__':
    main()
