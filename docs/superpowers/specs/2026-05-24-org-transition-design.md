# GitHub Org Transition — Design Spec

**Date:** 2026-05-24
**Scope:** `editor.html` only — two constant updates + one copy rewrite

---

## Background

The Railsplitter editor currently lives under the personal GitHub account `luryann/lincolnNewsletter`. Access is managed by adding individual students as repository collaborators. The goal is to move to a GitHub Organization (`lhsrailsplitter/newspaper`) so advisors manage access via org membership — cleaner roster management, immediate revocation, and per-commit attribution in `git log`.

PATs are retained: each student uses their own GitHub account's PAT, so every push to `content.json` is attributed to that student's username.

---

## What Does Not Change

- Auth logic: `validateToken` + `checkRepoAccess` (`permissions.push`) works identically for org repos — no changes
- PAT flow, sidebar gating, error handling, Settings view — unchanged
- All other files (`content.json`, `styles.css`, etc.) — unchanged

---

## Code Changes (`editor.html`)

### 1. Constants

```js
// Before
REPO_OWNER: 'luryann',
REPO_NAME:  'lincolnNewsletter',

// After
REPO_OWNER: 'lhsrailsplitter',
REPO_NAME:  'newspaper',
```

### 2. Setup view — Step 2 copy

**Before:**
> "Tell your faculty advisor your GitHub username. They'll add you to the newspaper's repository. You'll receive a confirmation email from GitHub."

**After:**
> "Tell your faculty advisor your GitHub username. They'll add you to The Railsplitter's GitHub organization. You'll get an invitation email from GitHub — open it and click **Accept invitation** before you continue here."

The distinction is important: an org invitation email looks different from a repo collaborator invite. Students who skip the accept step will get an access-denied error without this warning.

### 3. Settings view — Repository card label

Change the "Owner" field label to "Organization or username" to reflect that this field now holds an org name.

---

## Migration Steps (one-time, performed by advisor)

These are GitHub-side steps, not code changes. Do them before deploying the editor update.

1. **Create the org** — github.com → "+" → New organization → Free plan → name: `lhsrailsplitter`
2. **Transfer the repo** — `lincolnNewsletter` repo Settings → Danger Zone → Transfer → enter `lhsrailsplitter` → new repo name: `newspaper`
3. **Retain admin access** — add yourself as org owner during or after transfer
4. **Update local git remote** — `git remote set-url origin https://github.com/lhsrailsplitter/newspaper`
5. **Deploy editor update** — update constants and copy in `editor.html`, push

Existing students will need to be re-invited via the org. After transfer, GitHub redirects old repo URLs automatically, but the `editor.html` constants must be updated before students can use the editor.

---

## Onboarding flow after migration

1. Student gets org invitation email from GitHub → clicks **Accept invitation**
2. Student opens the editor, sees the Setup view
3. Follows Step 1 (create GitHub account if needed) and Step 3 (generate PAT)
4. Pastes PAT → editor validates token + checks `permissions.push` on `lhsrailsplitter/newspaper`
5. On success: sidebar unlocks, navigates to articles view
6. All subsequent commits attributed to student's GitHub account

---

## Files Changed

- `editor.html` — only file modified
  - `REPO_OWNER`: `'luryann'` → `'lhsrailsplitter'`
  - `REPO_NAME`: `'lincolnNewsletter'` → `'newspaper'`
  - Setup view Step 2 copy: updated for org invitation flow
  - Settings Repository card label: "Owner" → "Organization or username"
