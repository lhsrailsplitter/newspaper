#!/usr/bin/env python3
"""
Checks content.json for signs of character encoding corruption (mojibake).

Mojibake happens when UTF-8 bytes are misread as Latin-1/CP1252 and then
re-encoded, producing garbled sequences like â€œ instead of " or ÃÂ¢ instead of â.
"""

import json
import re
import sys

MOJIBAKE_PATTERNS = [
    # Double-encoded UTF-8 smart quotes and punctuation (the "â€" family).
    # These appear when curly quotes, dashes, bullets etc. get UTF-8 encoded twice.
    (r"â€[œ\x9c]",              'double-encoded left double quote (U+201C)'),
    (r"â€[ž\x9d]",              'double-encoded right double quote (U+201D)'),
    (r"â€™",                    'double-encoded right single quote / apostrophe (U+2019)'),
    (r"â€˜",                    'double-encoded left single quote (U+2018)'),
    (r"â€[\x93\x94]",           'double-encoded em/en dash (U+2013/2014)'),
    (r"â€¢",                    'double-encoded bullet (U+2022)'),
    (r"â€¦",                    'double-encoded ellipsis (U+2026)'),
    # Any â followed by two UTF-8 continuation bytes is a double-encoding artifact.
    (r"â[\x80-\xBF][\x80-\xBF]", 'double-encoded 3-byte UTF-8 sequence'),
    # Triple-encoding artifacts — the exact pattern from the bug report.
    (r"ÃÂ",                     'triple-encoded UTF-8 (severe corruption)'),
    # Latin-1 misread of common UTF-8 accented characters.
    (r"Ã©",                     'double-encoded e-acute (é)'),
    (r"Ã¨",                     'double-encoded e-grave (è)'),
    (r"Ã ",                     'double-encoded a-grave (à)'),
    (r"Ã¼",                     'double-encoded u-umlaut (ü)'),
    (r"Ã¶",                     'double-encoded o-umlaut (ö)'),
    (r"Ã¤",                     'double-encoded a-umlaut (ä)'),
    (r"Ã±",                     'double-encoded n-tilde (ñ)'),
    # Replacement character — data was already undecodable upstream.
    ("�",                   'Unicode replacement character (U+FFFD)'),
    # Null bytes are never valid inside JSON string values.
    (r"\x00",                   'null byte'),
]

CONTEXT_CHARS = 60


def excerpt(text, match):
    start = max(0, match.start() - CONTEXT_CHARS)
    end = min(len(text), match.end() + CONTEXT_CHARS)
    snippet = text[start:end].replace("\n", " ")
    return f"...{snippet}..."


def check(path):
    with open(path, "rb") as f:
        raw = f.read()

    # 1. Must be valid UTF-8
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"FAIL: {path} is not valid UTF-8: {e}")
        sys.exit(1)

    # 2. Must be valid JSON
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        print(f"FAIL: {path} is not valid JSON: {e}")
        sys.exit(1)

    # 3. Scan for mojibake signatures
    errors = []
    for pattern, description in MOJIBAKE_PATTERNS:
        for m in re.finditer(pattern, text):
            errors.append(
                f"  Line ~{text[:m.start()].count(chr(10)) + 1}: "
                f"found {description!r} pattern\n"
                f"  Context: {excerpt(text, m)}"
            )

    if errors:
        print(f"FAIL: {path} contains {len(errors)} corruption signature(s):\n")
        for e in errors:
            print(e)
        sys.exit(1)

    print(f"OK: {path} passed all integrity checks.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-content.json>")
        sys.exit(2)
    check(sys.argv[1])
