#!/usr/bin/env python3
"""
Validates internal query-param links across all HTML files and content.json.

The site routes everything through:
  section.html?s=<slug>    — must match a slug in content.json sections
  article.html?id=<id>     — must match an id in content.json articles

Hardcoded static values are validated. Dynamic JS concatenations
(e.g. 'article.html?id=' + esc(a.id)) are skipped — those values
come from content.json at runtime and are inherently consistent.

Also scans string fields inside content.json itself (e.g. breaking.link)
for the same patterns.
"""

import glob
import json
import re
import sys

# Matches static ?s=slug — stops at quote, whitespace, &, #
# Won't match dynamic JS like '?s=' + variable because the value
# would be a quote character, not [a-z].
RE_SECTION = re.compile(r"section\.html[^+]*?[?&]s=([a-z]+)")

# Matches static ?id=article-<digits>
RE_ARTICLE = re.compile(r"article\.html[^+]*?[?&]id=(article-\d+)")

ERRORS = []


def err(source, line_num, message):
    ERRORS.append(f"  {source}:{line_num}: {message}")


def scan_text(source, text, valid_slugs, valid_article_ids):
    lines = text.splitlines()
    for line_num, line in enumerate(lines, 1):
        for m in RE_SECTION.finditer(line):
            slug = m.group(1)
            if slug not in valid_slugs:
                err(source, line_num,
                    f"section.html?s={slug!r} — unknown slug "
                    f"(valid: {sorted(valid_slugs)})")

        for m in RE_ARTICLE.finditer(line):
            article_id = m.group(1)
            if article_id not in valid_article_ids:
                err(source, line_num,
                    f"article.html?id={article_id!r} — no article with this id")


def scan_json_strings(obj, valid_slugs, valid_article_ids, path="content.json"):
    """Walk every string value in the JSON tree and apply the link patterns."""
    if isinstance(obj, str):
        for m in RE_SECTION.finditer(obj):
            slug = m.group(1)
            if slug not in valid_slugs:
                err(path, "?", f"string value contains section.html?s={slug!r} — unknown slug")
        for m in RE_ARTICLE.finditer(obj):
            article_id = m.group(1)
            if article_id not in valid_article_ids:
                err(path, "?", f"string value contains article.html?id={article_id!r} — no article with this id")
    elif isinstance(obj, dict):
        for v in obj.values():
            scan_json_strings(v, valid_slugs, valid_article_ids, path)
    elif isinstance(obj, list):
        for item in obj:
            scan_json_strings(item, valid_slugs, valid_article_ids, path)


def load_content(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"FAIL: could not load {path}: {e}")
        sys.exit(1)

    slugs = {s["slug"] for s in data.get("sections", []) if isinstance(s, dict) and "slug" in s}
    ids = {a["id"] for a in data.get("articles", []) if isinstance(a, dict) and "id" in a}
    return data, slugs, ids


def main(content_path, html_paths):
    data, valid_slugs, valid_article_ids = load_content(content_path)

    # Scan HTML files
    for path in sorted(html_paths):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError as e:
            err(path, 0, f"not valid UTF-8: {e}")
            continue
        scan_text(path, text, valid_slugs, valid_article_ids)

    # Scan string values inside content.json itself (e.g. breaking.link)
    scan_json_strings(data, valid_slugs, valid_article_ids, path=content_path)

    if ERRORS:
        print(f"FAIL: {len(ERRORS)} broken internal link(s):\n")
        for e in ERRORS:
            print(e)
        sys.exit(1)

    total = len(html_paths) + 1
    print(f"OK: all internal links valid across {total} file(s).")


if __name__ == "__main__":
    html_files = glob.glob("*.html")
    if not html_files:
        print("No .html files found.")
        sys.exit(0)
    main("content.json", html_files)
