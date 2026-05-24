# GitHub Org Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `editor.html` to point at `lhsrailsplitter/newspaper` and rewrite the Setup view's Step 2 copy to match the GitHub org invitation flow.

**Architecture:** Three targeted edits to `editor.html` — two constant updates and two copy changes. No auth logic changes; `checkRepoAccess` (`permissions.push`) works identically for org repos.

**Tech Stack:** Vanilla JS, static HTML. No build step — open `editor.html` directly in a browser to verify.

---

### Task 1: Update repo constants

**Files:**
- Modify: `editor.html:254-255`

- [ ] **Step 1: Update `REPO_OWNER` and `REPO_NAME`**

In `editor.html`, find lines 254–255:
```js
  REPO_OWNER: 'luryann',
  REPO_NAME:  'lincolnNewsletter',
```

Replace with:
```js
  REPO_OWNER: 'lhsrailsplitter',
  REPO_NAME:  'newspaper',
```

- [ ] **Step 2: Verify no other hardcoded references remain**

Run:
```bash
grep -n "luryann\|lincolnNewsletter" editor.html
```
Expected: no output (zero matches).

- [ ] **Step 3: Commit**

```bash
git add editor.html
git commit -m "feat: update repo constants to lhsrailsplitter/newspaper"
```

---

### Task 2: Update Setup view Step 2 copy

**Files:**
- Modify: `editor.html:694`

- [ ] **Step 1: Rewrite Step 2 paragraph**

In `editor.html`, find line 694:
```js
              'Tell your Mr. Skramstad your GitHub username. They\'ll add you to the newspaper\'s repository. You\'ll get a confirmation email from GitHub.' +
```

Replace with:
```js
              'Tell Mr. Skramstad your GitHub username. They\'ll add you to The Railsplitter\'s GitHub organization. You\'ll get an invitation email from GitHub — open it and click <strong>Accept invitation</strong> before you continue here.' +
```

- [ ] **Step 2: Commit**

```bash
git add editor.html
git commit -m "feat: update setup view step 2 copy for org invitation flow"
```

---

### Task 3: Update Settings Repository card label

**Files:**
- Modify: `editor.html:635`

- [ ] **Step 1: Change "Owner" label**

In `editor.html`, find line 635:
```js
          '<div class="field"><label>Owner</label><input type="text" id="repoOwner" value="' + App.esc(App.REPO_OWNER) + '"></div>' +
```

Replace with:
```js
          '<div class="field"><label>Organization or username</label><input type="text" id="repoOwner" value="' + App.esc(App.REPO_OWNER) + '"></div>' +
```

- [ ] **Step 2: Commit**

```bash
git add editor.html
git commit -m "feat: clarify settings repo owner label as organization or username"
```

---

### Task 4: Manual verification

These checks confirm the editor works correctly after the constants are updated. Do this **after** the GitHub org and repo transfer are complete (see Migration Steps in the spec), otherwise the access check will fail.

- [ ] **Step 1: Open the editor**

Open `editor.html` directly in a browser (or via `python3 -m http.server` and navigate to `http://localhost:8000/editor.html`).

- [ ] **Step 2: Verify Setup view copy**

With no token in `localStorage`, the Setup view should appear. Confirm:
- Step 2 reads "Tell Mr. Skramstad your GitHub username. They'll add you to The Railsplitter's GitHub organization. You'll get an invitation email from GitHub — open it and click **Accept invitation** before you continue here."

- [ ] **Step 3: Verify Settings Repository card**

Navigate to Settings (if already authenticated). Confirm:
- The first field under the Repository card is labelled "Organization or username" (not "Owner")
- The field value shows `lhsrailsplitter`
- The Repository name field shows `newspaper`

- [ ] **Step 4: Verify access check points at the right repo**

Open browser DevTools → Network tab. In the Setup view, paste a valid PAT and click Connect. Confirm the request goes to:
```
GET https://api.github.com/repos/lhsrailsplitter/newspaper
```
(Not `luryann/lincolnNewsletter`.)
