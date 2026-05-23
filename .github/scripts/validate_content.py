#!/usr/bin/env python3
"""
Validates the structure and internal consistency of content.json.

Catches missing required fields, wrong types, unknown section slugs,
broken cross-references, and duplicate IDs — the kinds of mistakes
that happen when someone hand-edits the file.
"""

import json
import sys

ERRORS = []
VALID_SLUGS = {"news", "features", "opinion", "sports", "reviews"}


# ---------------------------------------------------------------------------
# Error collection
# ---------------------------------------------------------------------------

def err(path, message):
    ERRORS.append(f"  {path}: {message}")


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

def require_str(obj, key, path, nonempty=True):
    if key not in obj:
        err(path, f"missing required field '{key}'")
        return False
    if not isinstance(obj[key], str):
        err(f"{path}.{key}", f"must be a string, got {type(obj[key]).__name__}")
        return False
    if nonempty and not obj[key].strip():
        err(f"{path}.{key}", "must not be empty")
        return False
    return True


def require_bool(obj, key, path):
    if key not in obj:
        err(path, f"missing required field '{key}'")
        return False
    if not isinstance(obj[key], bool):
        err(f"{path}.{key}", f"must be a boolean, got {type(obj[key]).__name__}")
        return False
    return True


def require_list(obj, key, path):
    if key not in obj:
        err(path, f"missing required field '{key}'")
        return False
    if not isinstance(obj[key], list):
        err(f"{path}.{key}", f"must be an array, got {type(obj[key]).__name__}")
        return False
    return True


def require_dict(obj, key, path):
    if key not in obj:
        err(path, f"missing required field '{key}'")
        return False
    if not isinstance(obj[key], dict):
        err(f"{path}.{key}", f"must be an object, got {type(obj[key]).__name__}")
        return False
    return True


# ---------------------------------------------------------------------------
# Section validators
# ---------------------------------------------------------------------------

def validate_sections(sections):
    if not isinstance(sections, list):
        err("sections", f"must be an array, got {type(sections).__name__}")
        return set()

    if len(sections) == 0:
        err("sections", "must not be empty")

    seen_slugs = set()
    for i, section in enumerate(sections):
        p = f"sections[{i}]"
        if not isinstance(section, dict):
            err(p, "must be an object")
            continue

        if require_str(section, "slug", p):
            slug = section["slug"]
            if slug not in VALID_SLUGS:
                err(f"{p}.slug", f"'{slug}' is not a known section slug {sorted(VALID_SLUGS)}")
            if slug in seen_slugs:
                err(f"{p}.slug", f"duplicate slug '{slug}'")
            seen_slugs.add(slug)

        require_str(section, "title", p)

        if require_str(section, "ph", p):
            expected_ph = f"img-ph--{section.get('slug', '')}"
            if section["ph"] != expected_ph:
                err(f"{p}.ph", f"expected '{expected_ph}', got '{section['ph']}'")

    missing = VALID_SLUGS - seen_slugs
    if missing:
        err("sections", f"missing entries for slugs: {sorted(missing)}")

    return seen_slugs


def validate_issues(issues):
    if not isinstance(issues, list):
        err("issues", f"must be an array, got {type(issues).__name__}")
        return set()

    seen_ids = set()
    for i, issue in enumerate(issues):
        p = f"issues[{i}]"
        if not isinstance(issue, dict):
            err(p, "must be an object")
            continue

        if require_str(issue, "id", p):
            if issue["id"] in seen_ids:
                err(f"{p}.id", f"duplicate issue id '{issue['id']}'")
            seen_ids.add(issue["id"])

        require_str(issue, "title", p)
        require_str(issue, "date", p)
        require_str(issue, "coverArticle", p)

    return seen_ids


def validate_articles(articles, valid_slugs, valid_issue_ids):
    if not isinstance(articles, list):
        err("articles", f"must be an array, got {type(articles).__name__}")
        return set()

    seen_ids = set()
    for i, article in enumerate(articles):
        p = f"articles[{i}]"
        if not isinstance(article, dict):
            err(p, "must be an object")
            continue

        if require_str(article, "id", p):
            aid = article["id"]
            if not aid.startswith("article-"):
                err(f"{p}.id", f"'{aid}' should start with 'article-'")
            if aid in seen_ids:
                err(f"{p}.id", f"duplicate article id '{aid}'")
            seen_ids.add(aid)

        require_str(article, "title", p)
        require_str(article, "author", p)

        if require_str(article, "section", p):
            slug = article["section"]
            if slug not in valid_slugs:
                err(f"{p}.section", f"'{slug}' is not a known section slug {sorted(valid_slugs)}")

        require_str(article, "issue", p)

        if require_str(article, "issueId", p):
            if article["issueId"] not in valid_issue_ids:
                err(f"{p}.issueId", f"'{article['issueId']}' does not match any issue id {sorted(valid_issue_ids)}")

        require_str(article, "dek", p)
        require_str(article, "body", p)

        if require_str(article, "ph", p):
            section_slug = article.get("section", "")
            expected_ph = f"img-ph--{section_slug}"
            if article["ph"] != expected_ph:
                err(f"{p}.ph", f"expected '{expected_ph}' to match section, got '{article['ph']}'")

        require_str(article, "credit", p)
        require_bool(article, "published", p)

        # 'photo' is optional — only validate type if present
        if "photo" in article and not isinstance(article["photo"], str):
            err(f"{p}.photo", f"must be a string, got {type(article['photo']).__name__}")

    return seen_ids


def validate_homepage(homepage, valid_article_ids, valid_slugs):
    p = "homepage"
    if not isinstance(homepage, dict):
        err(p, f"must be an object, got {type(homepage).__name__}")
        return

    if require_str(homepage, "hero", p):
        if homepage["hero"] not in valid_article_ids:
            err(f"{p}.hero", f"'{homepage['hero']}' does not match any article id")

    if require_list(homepage, "heroAside", p):
        for j, ref in enumerate(homepage["heroAside"]):
            if not isinstance(ref, str):
                err(f"{p}.heroAside[{j}]", f"must be a string article id, got {type(ref).__name__}")
            elif ref not in valid_article_ids:
                err(f"{p}.heroAside[{j}]", f"'{ref}' does not match any article id")

    if require_dict(homepage, "sections", p):
        hsections = homepage["sections"]
        for slug in valid_slugs:
            if slug not in hsections:
                err(f"{p}.sections", f"missing key '{slug}'")
            elif not isinstance(hsections[slug], list):
                err(f"{p}.sections.{slug}", f"must be an array, got {type(hsections[slug]).__name__}")
            else:
                for j, ref in enumerate(hsections[slug]):
                    if not isinstance(ref, str):
                        err(f"{p}.sections.{slug}[{j}]", f"must be a string article id")
                    elif ref not in valid_article_ids:
                        err(f"{p}.sections.{slug}[{j}]", f"'{ref}' does not match any article id")

        extra = set(hsections.keys()) - valid_slugs
        if extra:
            err(f"{p}.sections", f"unknown section keys: {sorted(extra)}")


def validate_staff(staff):
    p = "staff"
    if not isinstance(staff, dict):
        err(p, f"must be an object, got {type(staff).__name__}")
        return

    for group in ("leadership", "photoCopy", "writers"):
        if not require_list(staff, group, p):
            continue
        members = staff[group]
        for i, member in enumerate(members):
            mp = f"{p}.{group}[{i}]"
            if not isinstance(member, dict):
                err(mp, "must be an object")
                continue
            require_str(member, "name", mp)
            if group in ("leadership", "photoCopy"):
                require_str(member, "role", mp)
                require_str(member, "beat", mp)
            else:
                require_str(member, "section", mp)


def validate_breaking(breaking):
    p = "breaking"
    if not isinstance(breaking, dict):
        err(p, f"must be an object, got {type(breaking).__name__}")
        return
    require_bool(breaking, "active", p)
    require_str(breaking, "text", p)
    require_str(breaking, "link", p, nonempty=breaking.get("active", False))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def validate(path):
    # 1. Valid UTF-8
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError as e:
        print(f"FAIL: {path} is not valid UTF-8: {e}")
        sys.exit(1)

    # 2. Valid JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"FAIL: {path} is not valid JSON: {e}")
        sys.exit(1)

    if not isinstance(data, dict):
        print(f"FAIL: {path} root must be a JSON object")
        sys.exit(1)

    # 3. Required top-level keys
    required_top = {"sections", "issues", "articles", "homepage", "staff"}
    missing_top = required_top - set(data.keys())
    if missing_top:
        for key in sorted(missing_top):
            err("(root)", f"missing required top-level key '{key}'")

    unknown_top = set(data.keys()) - required_top - {"breaking"}
    if unknown_top:
        for key in sorted(unknown_top):
            err("(root)", f"unknown top-level key '{key}' (did you mean to add this?)")

    # 4. Validate each section, collecting IDs for cross-reference checks
    valid_slugs = validate_sections(data.get("sections", []))
    valid_issue_ids = validate_issues(data.get("issues", []))
    valid_article_ids = validate_articles(
        data.get("articles", []), valid_slugs, valid_issue_ids
    )

    # Cross-check: coverArticle references in issues
    for i, issue in enumerate(data.get("issues", [])):
        if isinstance(issue, dict) and "coverArticle" in issue:
            if issue["coverArticle"] not in valid_article_ids:
                err(f"issues[{i}].coverArticle",
                    f"'{issue['coverArticle']}' does not match any article id")

    if "homepage" in data:
        validate_homepage(data["homepage"], valid_article_ids, valid_slugs)

    if "staff" in data:
        validate_staff(data["staff"])

    if "breaking" in data:
        validate_breaking(data["breaking"])

    # 5. Report
    if ERRORS:
        print(f"FAIL: {path} has {len(ERRORS)} schema error(s):\n")
        for e in ERRORS:
            print(e)
        sys.exit(1)

    print(f"OK: {path} passed schema validation.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-content.json>")
        sys.exit(2)
    validate(sys.argv[1])
