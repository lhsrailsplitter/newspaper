# The Railsplitter

Student newspaper of Abraham Lincoln High School — Los Angeles, CA.

## Overview

Static HTML/CSS/JS site. No build system, no framework. Open any `.html` file directly in a browser, or serve the directory with any static file server. All content lives in [`content.json`](content.json).

## Pages

| File | URL pattern | Purpose |
|---|---|---|
| `index.html` | `/` | Homepage — hero, section previews |
| `section.html` | `?s=<slug>` | All articles for a section |
| `article.html` | `?id=<article-id>` | Single article view |
| `archive.html` | — | Issue archive |
| `about.html` | — | Staff and masthead |
| `search.html` | — | Article search |
| `print.html` | — | Print-formatted view |
| `404.html` | — | Not found |
| `editor.html` | — | CMS editor (see below) |

### Section slugs

`news` · `features` · `opinion` · `sports` · `reviews`

## Content

All content is stored in `content.json`. The top-level keys are:

| Key | Description |
|---|---|
| `sections` | Section metadata (slug, title, placeholder class) |
| `issues` | Issue list with cover article reference |
| `articles` | Every article — body, author, section, photo, etc. |
| `homepage` | Hero article + per-section featured article slots |
| `staff` | Leadership, photo/copy editors, and writers |
| `breaking` | Optional breaking news banner (active flag + text + link) |

### Adding an article

1. Open the editor (`editor.html`) — sign in with a GitHub personal access token (`repo` scope).
2. Click **All Articles → New Article**, fill in the fields, upload a photo, and save.
3. The editor commits `content.json` and the photo directly to GitHub via the API.

To add an article manually, append an entry to `articles[]` with these required fields:

```json
{
  "id": "article-<timestamp>",
  "title": "...",
  "author": "...",
  "section": "news",
  "issue": "Issue 7, May 2026",
  "issueId": "issue-7",
  "dek": "...",
  "body": "<p>...</p>",
  "ph": "img-ph--news",
  "credit": "...",
  "published": true
}
```

`photo` (path like `photos/article-<id>.jpg`) is optional.

## Editor

`editor.html` is a browser-based CMS that writes directly to GitHub. It requires a GitHub personal access token with `repo` (or `contents: write`) scope.

**Views:** All Articles · Article Editor · Homepage · Breaking News · Sections · Issues · Staff · **CI Status** · Settings

The **CI Status** view shows the live pass/fail state of every GitHub Actions workflow. Failed workflows expand to show which job and step failed, along with a log excerpt when available.

### Photos

Upload photos through the article editor. They are stored in `photos/` and referenced by the article's `photo` field as `photos/<filename>`. The filename is automatically set to `article-<id>.<ext>`.

## Theming

All design tokens are CSS custom properties on `:root` in `styles.css`:

```
--f-display / --f-body / --f-sans   fonts
--c-ink / --c-orange / --c-bg       colors
--c-surface / --c-rule / --c-muted
--max-w / --x-pad / --gap           layout
```

The tweaks panel (FAB, bottom-right on the homepage) lets you toggle accent color, font pairing, background mood, and density live.

## GitHub Actions

Seven automated workflows run on every relevant push or pull request.

### Content checks (run on `content.json` changes)

| Workflow | File | What it checks |
|---|---|---|
| Content Integrity | `content-integrity.yml` | Mojibake, double-encoded UTF-8, null bytes, invalid JSON |
| Content Auto-Repair | `content-autorepair.yml` | Detects encoding corruption and auto-repairs with `ftfy`, commits the fix |
| Content Schema | `content-schema.yml` | Required fields, correct types, valid section slugs, cross-references between articles/issues/homepage |
| Photo Integrity | `photo-integrity.yml` | Referenced photos exist on disk; orphaned files in `photos/` are flagged |
| Internal Links | `content-schema.yml` | `section.html?s=` and `article.html?id=` values match known slugs and article IDs |

### HTML checks (run on `*.html` changes)

| Workflow | File | What it checks |
|---|---|---|
| HTML Validation | `html-validation.yml` | Unclosed tags, mismatched tags, missing `<html>`/`<head>`/`<body>`/`<title>` |

### Maintenance (scheduled / manual)

| Workflow | Trigger | What it does |
|---|---|---|
| Photo Purge | 1st of every month + manual | Deletes orphaned photos older than 6 months using git history for age; manual runs default to dry-run |
| Archive Release | Manual (`workflow_dispatch`) | Creates a GitHub Release tagged with the current issue, attaches `content.json` and an article changelog |

### CI scripts

All check logic lives in `.github/scripts/` as standalone Python files (no third-party dependencies except `ftfy` for the auto-repair):

```
check_content.py    — encoding / mojibake detection
repair_content.py   — ftfy-based repair + JSON formatting
validate_content.py — schema and cross-reference validation
check_photos.py     — photo file existence + orphan detection (with git age)
check_links.py      — internal query-param link validation
validate_html.py    — HTML structure validation
purge_photos.py     — orphan photo deletion with --dry-run support
```

Each script can be run locally:

```bash
python3 .github/scripts/validate_content.py content.json
python3 .github/scripts/check_links.py
python3 .github/scripts/validate_html.py *.html
python3 .github/scripts/purge_photos.py content.json --dry-run
```

## Repository structure

```
/
├── index.html          Homepage
├── section.html        Section listing
├── article.html        Article view
├── archive.html        Issue archive
├── about.html          Staff page
├── search.html         Search
├── print.html          Print view
├── 404.html            Not found
├── editor.html         CMS editor
├── styles.css          Single shared stylesheet
├── content.json        All site content
├── photos/             Article photos
└── .github/
    ├── workflows/      GitHub Actions workflow files
    └── scripts/        Python validation and repair scripts
```
