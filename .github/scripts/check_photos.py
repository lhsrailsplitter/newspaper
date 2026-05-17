#!/usr/bin/env python3
"""
Checks photo file integrity for content.json.

  1. Every 'photo' field in articles points to a file that actually exists.
  2. Every file in photos/ is referenced by at least one article.
     Orphans are non-fatal warnings that include how long ago the file
     was added to the repo (useful context for the purge workflow).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

PHOTOS_DIR = "photos"


def git_added_date(path):
    """Return the date a file was first committed, or None if not in git."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%ai", "--", path],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        if not lines:
            return None
        oldest = lines[-1]
        return datetime.fromisoformat(oldest).astimezone(timezone.utc)
    except Exception:
        return None


def days_old(dt):
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).days


def check(content_path):
    errors = []
    warnings = []

    try:
        with open(content_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"FAIL: could not parse {content_path}: {e}")
        sys.exit(1)

    articles = data.get("articles", [])

    referenced = set()
    for i, article in enumerate(articles):
        photo = article.get("photo")
        if photo is None:
            continue
        if not isinstance(photo, str):
            errors.append(f"  articles[{i}].photo: must be a string, got {type(photo).__name__}")
            continue
        referenced.add(photo)
        if not os.path.isfile(photo):
            errors.append(
                f"  articles[{i}] ({article.get('id', '?')}): "
                f"photo '{photo}' does not exist"
            )

    if os.path.isdir(PHOTOS_DIR):
        for filename in sorted(os.listdir(PHOTOS_DIR)):
            filepath = os.path.join(PHOTOS_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            if filepath not in referenced and filename not in referenced:
                added = git_added_date(filepath)
                age = days_old(added)
                age_str = f"{age}d old" if age is not None else "age unknown"
                warnings.append(f"  {filepath}: not referenced by any article ({age_str})")
    else:
        warnings.append(f"  '{PHOTOS_DIR}/' directory does not exist")

    if errors:
        print(f"FAIL: {len(errors)} photo reference error(s):\n")
        for e in errors:
            print(e)

    if warnings:
        print(f"\nWARN: {len(warnings)} orphaned photo(s):\n")
        for w in warnings:
            print(w)

    if errors:
        sys.exit(1)

    if not errors and not warnings:
        print("OK: all photo references are valid, no orphaned files.")
    elif not errors:
        print("\nOK: no broken references (orphan warnings above are non-fatal).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-content.json>")
        sys.exit(2)
    check(sys.argv[1])
