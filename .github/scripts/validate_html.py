#!/usr/bin/env python3
"""
Validates HTML files for structural correctness.

Catches the kinds of mistakes that happen during manual editing:
  - Malformed tag syntax (missing quotes, stray characters)
  - Unclosed block-level tags (div, script, style, nav, etc.)
  - Mismatched tags (opened as <div>, closed as </section>)
  - Missing required page elements (html, head, body, title)
  - <script> or <style> tags with no matching close (page-breaking)

Uses only the Python standard library (html.parser).
"""

import glob
import html.parser
import os
import sys

# Tags that must be explicitly closed (non-void block elements we care about).
# Void elements (br, img, input, meta, link, hr, etc.) are intentionally excluded.
TRACKED_TAGS = {
    "html", "head", "body",
    "div", "main", "header", "footer", "nav", "section", "article", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "ul", "ol", "li",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "form", "fieldset", "select", "textarea",
    "script", "style", "template",
    "a", "button",
    "figure", "figcaption",
}

# Every page should have these.
REQUIRED_TAGS = {"html", "head", "body", "title"}


class HTMLValidator(html.parser.HTMLParser):
    def __init__(self, filename):
        super().__init__(convert_charrefs=False)
        self.filename = filename
        self.errors = []
        self.stack = []       # (tag, line) tuples for open tracked tags
        self.seen = set()     # tags we've encountered at all

    def _pos(self):
        line, _ = self.getpos()
        return line

    def handle_starttag(self, tag, attrs):
        self.seen.add(tag)
        if tag in TRACKED_TAGS:
            self.stack.append((tag, self._pos()))

    def handle_endtag(self, tag):
        if tag not in TRACKED_TAGS:
            return
        # Find the most recent matching open tag
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                # Check for anything left open between here and the match
                unclosed = self.stack[i + 1:]
                for open_tag, open_line in unclosed:
                    self.errors.append(
                        f"  line {self._pos()}: </{tag}> closed before "
                        f"<{open_tag}> (opened at line {open_line}) was closed"
                    )
                self.stack = self.stack[:i]
                return
        # No matching open tag found
        self.errors.append(
            f"  line {self._pos()}: </{tag}> has no matching opening tag"
        )

    def handle_error(self, message):
        line, _ = self.getpos()
        self.errors.append(f"  line {line}: {message}")

    def finish(self):
        # Anything still on the stack was never closed
        for tag, line in self.stack:
            self.errors.append(f"  line {line}: <{tag}> was never closed")

        # Check required structural elements
        for req in sorted(REQUIRED_TAGS):
            if req not in self.seen:
                self.errors.append(f"  missing required element <{req}>")

        return self.errors


def validate_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except UnicodeDecodeError as e:
        return [f"  not valid UTF-8: {e}"]

    validator = HTMLValidator(path)
    try:
        validator.feed(source)
    except html.parser.HTMLParseError as e:
        return [f"  parse error: {e}"]

    return validator.finish()


def main(paths):
    total_errors = 0

    for path in sorted(paths):
        errors = validate_file(path)
        if errors:
            total_errors += len(errors)
            print(f"FAIL {path} — {len(errors)} error(s):")
            for e in errors:
                print(e)
            print()
        else:
            print(f"OK   {path}")

    if total_errors:
        print(f"\n{total_errors} total error(s) across {len(paths)} file(s).")
        sys.exit(1)
    else:
        print(f"\nAll {len(paths)} HTML file(s) passed.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    else:
        # Default: all .html files in the repo root
        paths = glob.glob("*.html")
        if not paths:
            print("No .html files found.")
            sys.exit(0)

    main(paths)
