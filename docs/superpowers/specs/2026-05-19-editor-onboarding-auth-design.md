# Editor Onboarding & Auth Refactor — Design Spec

**Date:** 2026-05-19
**Scope:** `editor.html` only — no other files affected

---

## Background

The Railsplitter editor is used by a rotating journalism class (~20–25 students/year) plus stable faculty advisors. Students are new to GitHub. Each year is an entirely new cohort; advisors are permanent.

Currently:
- Authorization uses a hardcoded `ALLOWED_EDITORS` username list — requires a code deploy to add/remove anyone
- No PAT → redirects to the Settings view, but the full sidebar remains visible
- Settings view doubles as both first-time setup and ongoing account management

---

## Goals

1. Replace the hardcoded `ALLOWED_EDITORS` list with GitHub repo write-permission checks — no code changes needed when the team changes
2. Hide the sidebar entirely when unauthenticated
3. Show a student-friendly first-time setup guide (not a bare form) when no PAT is stored
4. Keep Settings lean — just account management for already-authenticated users

---

## Auth Refactor

### Current flow
1. `validateToken(token)` → `GET /user` → returns username
2. Check `ALLOWED_EDITORS.includes(username)` — hardcoded array

### New flow
1. `validateToken(token)` → `GET /user` → returns username
2. `checkRepoAccess(token)` → `GET /repos/{REPO_OWNER}/{REPO_NAME}` → check `data.permissions.push === true`

The `permissions` object is included by GitHub in the repo response when the request is authenticated. `push: true` means the user has write access — either as a direct collaborator (personal repo) or as an org member with write access (after org transfer). No new PAT scopes required beyond the existing `repo`.

### Why this works across the transfer
`REPO_OWNER` and `REPO_NAME` are already configurable constants. After the repo transfers to a GitHub org, only those two constants need updating. The permission check logic is identical.

### Access denied path
If `permissions.push` is false or absent: clear the token from `localStorage`, display an "Access denied" notice — "Your GitHub account (@username) doesn't have access. Contact your faculty advisor." Do not navigate away from the setup/settings screen.

### Constants removed
`ALLOWED_EDITORS` array is deleted entirely.

---

## Sidebar Gating

Add a `data-unauthed` attribute to `.editor-wrap` on page load when no token is stored. Remove it on successful authentication.

CSS rules:
```css
[data-unauthed] .sidebar-nav { display: none; }
[data-unauthed] .sidebar-footer { display: none; }
```

The sidebar brand ("The Railsplitter / Editor") remains visible as a minimal anchor. Everything else disappears until auth succeeds.

On successful auth: remove `data-unauthed`, reveal full nav, navigate to articles view.

---

## Setup View (new)

Shown in `contentArea` when no PAT is stored on load. Replaces the current redirect-to-settings behavior.

### Structure

A single card centered in the content area, titled "Get Started". Three numbered steps followed by a token input:

**Step 1 — Create a GitHub account**
> Go to [github.com/signup](https://github.com/signup) and create a free account. Any email address works.

**Step 2 — Get access from your advisor**
> Tell your faculty advisor your GitHub username. They'll add you to the newspaper's repository. You'll receive a confirmation email from GitHub.

**Step 3 — Create your access token**
> In GitHub: click your profile picture (top-right) → **Settings** → **Developer settings** (bottom of left sidebar) → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**
>
> - Set expiration to **1 year**
> - Check the **`repo`** scope
> - Click **Generate token**
> - Copy the token — it starts with `ghp_` and won't be shown again

**Token input + Connect button**
- `<input type="password" placeholder="ghp_...">` 
- "Connect" button — on click: validates token, checks repo access, stores in `localStorage` if authorized
- Inline status feedback below the button ("Connecting…" / "✓ Connected as @username" / error)

### Navigation
`App.init()` checks `localStorage` for a saved token. If absent: `router.navigate('setup')`. If present: run the existing validate + check-repo-access flow, then navigate to `articles` on success.

The setup view is not reachable from the sidebar (no nav item). It is only shown automatically when unauthenticated.

---

## Settings View (simplified)

Shown via the Settings nav item for already-authenticated users. Contains:

1. **Account card** — "Signed in as @username" + "Sign out" button. Sign out: clears `localStorage`, sets `data-unauthed` on the wrapper, navigates to the `setup` view.
2. **Change token card** — password input pre-filled with masked current token, "Save & Reconnect" button (re-runs the validate + access check flow)
3. **Repository card** — existing owner/name fields (unchanged)

The three-step onboarding guide is removed from this view. It lives only in the setup view.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Token invalid / expired | "Token invalid or expired." inline error, stay on setup/settings |
| Token valid but no repo access | "Access denied — @username doesn't have access. Contact your advisor." clear token |
| Network error during validation | "Could not connect. Check your internet connection." |
| Token valid, repo accessible | Store token, remove `data-unauthed`, navigate to articles |

---

## Files Changed

- `editor.html` — only file modified. All changes are within the `<script>` block and inline CSS.

No new files. No changes to `content.json`, `styles.css`, or any other page.
