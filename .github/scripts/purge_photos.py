#!/usr/bin/env python3
"""
Deletes orphaned photos (not referenced by any article) that were added
to the repo more than --months ago.

Usage:
  python3 purge_photos.py content.json           # real run (default 6 months)
  python3 purge_photos.py content.json --dry-run # print what would be deleted
  python3 purge_photos.py content.json --months 3

Exit codes:
  0 — completed (whether or not anything was deleted)
  1 — error loading content.json or git unavailable
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

PHOTOS_DIR = "photos"


def git_added_date(path):
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%ai", "--", path],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        if not lines:
            return None
        return datetime.fromisoformat(lines[-1]).astimezone(timezone.utc)
    except Exception:
        return None


def referenced_photos(content_path):
    with open(content_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    refs = set()
    for article in data.get("articles", []):
        photo = article.get("photo")
        if isinstance(photo, str):
            refs.add(photo)
            refs.add(os.path.basename(photo))
    return refs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("content", help="Path to content.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be deleted without deleting")
    parser.add_argument("--months", type=int, default=6,
                        help="Age threshold in months (default: 6)")
    args = parser.parse_args()

    try:
        refs = referenced_photos(args.content)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: could not load {args.content}: {e}")
        sys.exit(1)

    if not os.path.isdir(PHOTOS_DIR):
        print(f"No '{PHOTOS_DIR}/' directory found — nothing to purge.")
        sys.exit(0)

    threshold_days = args.months * 30
    now = datetime.now(timezone.utc)

    candidates = []
    skipped_young = []
    skipped_referenced = []

    for filename in sorted(os.listdir(PHOTOS_DIR)):
        filepath = os.path.join(PHOTOS_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        if filepath in refs or filename in refs:
            skipped_referenced.append(filepath)
            continue

        added = git_added_date(filepath)
        if added is None:
            print(f"  SKIP {filepath}: not tracked in git, skipping to be safe")
            continue

        age_days = (now - added).days
        if age_days < threshold_days:
            skipped_young.append((filepath, age_days, threshold_days - age_days))
            continue

        candidates.append((filepath, age_days))

    # Report
    if skipped_young:
        print(f"Skipping {len(skipped_young)} orphan(s) under {args.months} months old:")
        for path, age, remaining in skipped_young:
            print(f"  {path}  ({age}d old, {remaining}d until eligible)")

    if not candidates:
        print(f"\nNothing to purge — no orphaned photos older than {args.months} months.")
        return

    verb = "Would delete" if args.dry_run else "Deleting"
    print(f"\n{verb} {len(candidates)} orphaned photo(s) older than {args.months} months:")
    for path, age in candidates:
        size_kb = os.path.getsize(path) // 1024
        print(f"  {path}  ({age}d old, {size_kb} KB)")

    if args.dry_run:
        print("\nDry run — nothing deleted. Remove --dry-run to apply.")
        return

    deleted = []
    for path, _ in candidates:
        try:
            os.remove(path)
            deleted.append(path)
        except OSError as e:
            print(f"  ERROR deleting {path}: {e}")

    print(f"\nDeleted {len(deleted)} file(s).")


if __name__ == "__main__":
    main()
