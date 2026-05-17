#!/usr/bin/env python3
"""
Repairs character-encoding corruption (mojibake) in content.json.

Strategy: walk every string value in the JSON tree and run ftfy.fix_text(),
which reverses double- and triple-encoded UTF-8 sequences. Then write the
file back with consistent 2-space indentation and real Unicode characters
(ensure_ascii=False keeps curly quotes, dashes, etc. as-is rather than
escaping them as \\uXXXX).
"""

import json
import sys

try:
    import ftfy
except ImportError:
    print("ERROR: ftfy is not installed. Run: pip install ftfy")
    sys.exit(2)


def fix_value(value):
    if isinstance(value, str):
        return ftfy.fix_text(value)
    if isinstance(value, dict):
        return {k: fix_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [fix_value(item) for item in value]
    return value


def repair(path):
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    data = json.loads(original)
    fixed_data = fix_value(data)
    fixed_text = json.dumps(fixed_data, ensure_ascii=False, indent=2) + "\n"

    if fixed_text == original:
        print(f"No changes needed: {path} already clean.")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(fixed_text)

    # Show a diff-style summary of what changed.
    original_lines = original.splitlines()
    fixed_lines = fixed_text.splitlines()
    changed = sum(1 for a, b in zip(original_lines, fixed_lines) if a != b)
    print(f"Repaired {path}: {changed} line(s) changed.")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-content.json>")
        sys.exit(2)
    repair(sys.argv[1])
