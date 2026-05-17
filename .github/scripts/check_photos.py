#!/usr/bin/env python3
"""
Checks photo file integrity for content.json.

Two checks:
  1. Every 'photo' field in articles points to a file that actually exists.
  2. Every file in the photos/ directory is referenced by at least one article
     (flags orphans so stale files don't accumulate silently).
"""

import json
import os
import sys

PHOTOS_DIR = "photos"


def check(content_path):
    errors = []
    warnings = []

    # Load content.json
    try:
        with open(content_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"FAIL: could not parse {content_path}: {e}")
        sys.exit(1)

    articles = data.get("articles", [])

    # Build the set of referenced photo paths
    referenced = set()
    for i, article in enumerate(articles):
        photo = article.get("photo")
        if photo is None:
            continue  # photo is optional
        if not isinstance(photo, str):
            errors.append(f"  articles[{i}].photo: must be a string, got {type(photo).__name__}")
            continue

        referenced.add(photo)

        # Check the file actually exists on disk
        if not os.path.isfile(photo):
            errors.append(
                f"  articles[{i}] ({article.get('id', '?')}): "
                f"photo '{photo}' does not exist"
            )

    # Check for orphaned files in photos/
    if os.path.isdir(PHOTOS_DIR):
        for filename in sorted(os.listdir(PHOTOS_DIR)):
            filepath = os.path.join(PHOTOS_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            if filepath not in referenced and filename not in referenced:
                warnings.append(f"  {filepath}: not referenced by any article")
    else:
        warnings.append(f"  '{PHOTOS_DIR}/' directory does not exist")

    # Report
    if errors:
        print(f"FAIL: {len(errors)} photo reference error(s):\n")
        for e in errors:
            print(e)

    if warnings:
        print(f"\nWARN: {len(warnings)} orphaned photo(s) (referenced by nothing):\n")
        for w in warnings:
            print(w)

    if errors:
        sys.exit(1)

    if not errors and not warnings:
        print(f"OK: all photo references are valid, no orphaned files.")
    elif not errors:
        print(f"\nOK: no broken references (orphan warnings above are non-fatal).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-content.json>")
        sys.exit(2)
    check(sys.argv[1])
