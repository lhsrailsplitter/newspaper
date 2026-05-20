# Editor Onboarding & Auth Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `ALLOWED_EDITORS` check with GitHub repo-permission verification, add a student-friendly first-time setup guide, and hide the sidebar until authenticated.

**Architecture:** All changes are in `editor.html` only. A new `App.auth` namespace centralises the connect/sign-out flow so setup and settings views share identical logic. The sidebar is gated via a `data-unauthed` attribute on the shell element toggled by JS, hidden via CSS.

**Tech Stack:** Vanilla JS, inline CSS, GitHub REST API v3 (`/user`, `/repos/{owner}/{repo}`)

---

## File Map

| File | Change |
|---|---|
| `editor.html` line 186 | Add `id="editorShell"` to `.shell` div |
| `editor.html` lines 7–183 | Add `[data-unauthed]` CSS rules to `<style>` block |
| `editor.html` lines 251–265 | Remove `ALLOWED_EDITORS`; add `user: null` to `App.state` |
| `editor.html` lines 298–377 | Add `checkRepoAccess` to `App.github`; add `App.auth` namespace |
| `editor.html` lines 460–497 | Rewrite `App.init` |
| `editor.html` lines 500–579 | Replace `App.views.settings` |
| After `App.views.settings` | Add new `App.views.setup` |

> No other files are touched.

---

## Task 1: Add `id` to shell + CSS for unauthed state

**Files:**
- Modify: `editor.html:186` (shell div)
- Modify: `editor.html:183` (end of `<style>` block, before `</style>`)

- [ ] **Step 1: Add `id="editorShell"` to the shell div**

Find line 186:
```html
<div class="shell">
```
Change to:
```html
<div class="shell" id="editorShell">
```

- [ ] **Step 2: Add unauthed CSS rules before `</style>`**

Find the closing `</style>` tag (line 183). Insert these two rules immediately before it:
```css
[data-unauthed] .sidebar-nav{display:none;}
[data-unauthed] .sidebar-footer{display:none;}
```
So the end of the style block reads:
```css
.wf-detail-log{background:#1c1917;color:#e7e3de;padding:10px 14px;border-radius:5px;font-size:11px;line-height:1.65;margin-top:8px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-height:200px;overflow-y:auto;}
[data-unauthed] .sidebar-nav{display:none;}
[data-unauthed] .sidebar-footer{display:none;}
</style>
```

- [ ] **Step 3: Verify visually**

Open `editor.html` in a browser. In DevTools console run:
```js
document.getElementById('editorShell').setAttribute('data-unauthed', '')
```
Expected: the sidebar nav and footer disappear; the brand ("The Railsplitter / Editor") stays visible.

Run:
```js
document.getElementById('editorShell').removeAttribute('data-unauthed')
```
Expected: nav and footer reappear.

- [ ] **Step 4: Commit**
```bash
git add editor.html
git commit -m "feat: add editorShell id and unauthed CSS gating"
```

---

## Task 2: Add `checkRepoAccess` to `App.github`

**Files:**
- Modify: `editor.html` — `App.github` object (around line 367, after `validateToken`)

- [ ] **Step 1: Add `checkRepoAccess` after `validateToken`**

Find this block (ends around line 377):
```javascript
    validateToken: function(token) {
      return fetch(App.github.apiBase + '/user', {
        headers: {
          'Authorization': 'token ' + token,
          'Accept': 'application/vnd.github.v3+json'
        }
      }).then(function(r) {
        if (!r.ok) throw new Error('invalid');
        return r.json();
      });
    }
  },
```
Replace with:
```javascript
    validateToken: function(token) {
      return fetch(App.github.apiBase + '/user', {
        headers: {
          'Authorization': 'token ' + token,
          'Accept': 'application/vnd.github.v3+json'
        }
      }).then(function(r) {
        if (!r.ok) throw new Error('invalid');
        return r.json();
      });
    },

    checkRepoAccess: function(token) {
      var url = App.github.apiBase + '/repos/' + App.REPO_OWNER + '/' + App.REPO_NAME;
      return fetch(url, {
        headers: {
          'Authorization': 'token ' + token,
          'Accept': 'application/vnd.github.v3+json'
        }
      }).then(function(r) {
        if (!r.ok) throw new Error('repo_not_found');
        return r.json();
      }).then(function(data) {
        if (!data.permissions || !data.permissions.push) throw new Error('no_push_access');
      });
    }
  },
```

- [ ] **Step 2: Commit**
```bash
git add editor.html
git commit -m "feat: add checkRepoAccess to App.github"
```

---

## Task 3: Add `App.auth` namespace + `user` to state

**Files:**
- Modify: `editor.html` — `App.state` object (line ~258) and the `App` object (add `auth` key before `init`)

- [ ] **Step 1: Add `user: null` to `App.state`**

Find:
```javascript
  state: {
    token:        null,
    sha:          null,
    content:      null,
    lastSavedJson: null,
    view:         'articles',
    articleId:    null,
    pendingChanges: []
  },
```
Replace with:
```javascript
  state: {
    token:        null,
    user:         null,
    sha:          null,
    content:      null,
    lastSavedJson: null,
    view:         'articles',
    articleId:    null,
    pendingChanges: []
  },
```

- [ ] **Step 2: Add `App.auth` before `App.init`**

Find the line:
```javascript
  // ── Init ──────────────────────────────────────────────────────────────
```
Insert the following block immediately before it:
```javascript
  // ── Auth ──────────────────────────────────────────────────────────────
  auth: {
    connect: function(token, onStatus) {
      onStatus('connecting');
      return App.github.validateToken(token).then(function(user) {
        return App.github.checkRepoAccess(token).then(function() { return user; });
      }).then(function(user) {
        localStorage.setItem('rs_token', token);
        App.state.token = token;
        App.state.user  = user.login;
        document.getElementById('editorShell').removeAttribute('data-unauthed');
        document.getElementById('sidebarFooter').innerHTML =
          'Signed in as <strong>@' + App.esc(user.login) + '</strong>';
        document.getElementById('navCiStatus').style.display = '';
        onStatus('success', user.login);
        return App.github.getContent().then(function() {
          App.router.navigate('articles');
        });
      }).catch(function(err) {
        onStatus('error', err.message);
      });
    },

    signOut: function() {
      localStorage.removeItem('rs_token');
      App.state.token = null;
      App.state.user  = null;
      document.getElementById('editorShell').setAttribute('data-unauthed', '');
      document.getElementById('sidebarFooter').textContent = 'Not signed in';
      document.getElementById('navCiStatus').style.display = 'none';
      App.router.navigate('setup');
    }
  },

```

- [ ] **Step 3: Commit**
```bash
git add editor.html
git commit -m "feat: add App.auth connect/signOut and App.state.user"
```

---

## Task 4: Rewrite `App.init`

**Files:**
- Modify: `editor.html` — `App.init` (lines ~460–497)

- [ ] **Step 1: Replace the full `init` function**

Find the entire block:
```javascript
  init: function() {
    document.querySelectorAll('.nav-item[data-view]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        App.router.navigate(btn.dataset.view);
      });
    });

    App.state.token = localStorage.getItem('rs_token');

    if (!App.state.token) {
      App.router.navigate('settings');
      return;
    }

    document.getElementById('topbarTitle').textContent = 'Loading…';
    document.getElementById('contentArea').innerHTML = '<div class="spinner"></div>';

    App.github.validateToken(App.state.token).then(function(user) {
      if (!App.ALLOWED_EDITORS.includes(user.login.toLowerCase())) {
        localStorage.removeItem('rs_token');
        App.state.token = null;
        document.getElementById('topbarTitle').textContent = 'Access Denied';
        document.getElementById('contentArea').innerHTML =
          '<div class="notice notice-error" style="max-width:480px;margin:40px auto;">' +
            '<strong>Access denied.</strong> Your GitHub account (@' + App.esc(user.login) + ') is not authorized to use this editor. ' +
            'Contact the editor-in-chief to request access.' +
          '</div>';
        return;
      }
      document.getElementById('sidebarFooter').innerHTML = 'Signed in as <strong>@' + App.esc(user.login) + '</strong>';
      document.getElementById('navCiStatus').style.display = '';
      return App.github.getContent().then(function() {
        App.router.navigate('articles');
      });
    }).catch(function(err) {
      App.handleApiError(err);
    });
  }
```
Replace with:
```javascript
  init: function() {
    document.querySelectorAll('.nav-item[data-view]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        App.router.navigate(btn.dataset.view);
      });
    });

    App.state.token = localStorage.getItem('rs_token');

    if (!App.state.token) {
      document.getElementById('editorShell').setAttribute('data-unauthed', '');
      App.router.navigate('setup');
      return;
    }

    document.getElementById('topbarTitle').textContent = 'Loading…';
    document.getElementById('contentArea').innerHTML = '<div class="spinner"></div>';

    App.auth.connect(App.state.token, function(state, detail) {
      if (state === 'error') {
        if (detail === 'no_push_access') {
          document.getElementById('topbarTitle').textContent = 'Access Denied';
          document.getElementById('contentArea').innerHTML =
            '<div class="notice notice-error" style="max-width:480px;margin:40px auto;">' +
              '<strong>Access denied.</strong> Your GitHub account doesn\'t have write access to this repository. ' +
              'Contact your faculty advisor to be added.' +
            '</div>';
        } else {
          App.handleApiError(new Error(detail));
        }
      }
    });
  }
```

- [ ] **Step 2: Remove `ALLOWED_EDITORS` constant**

Find:
```javascript
  ALLOWED_EDITORS: ['luryann'], // GitHub usernames permitted to use this editor
```
Delete that entire line.

- [ ] **Step 3: Verify no-token path in browser**

Clear localStorage:
```js
localStorage.removeItem('rs_token')
```
Reload the page. Expected:
- Sidebar nav and footer hidden, only brand visible
- Content area shows the setup view title (after Task 5 — skip this check until then)

- [ ] **Step 4: Commit**
```bash
git add editor.html
git commit -m "feat: rewrite App.init to use App.auth, remove ALLOWED_EDITORS"
```

---

## Task 5: Add `App.views.setup`

**Files:**
- Modify: `editor.html` — add new view after `App.views.settings` closing brace

- [ ] **Step 1: Insert `App.views.setup` after `App.views.settings`**

Find the closing of `App.views.settings` (look for the final `};` after the `saveRepoBtn` listener, around line 579). Insert the following block immediately after it:

```javascript
// ── Setup view (first-time onboarding) ────────────────────────────────────
App.views.setup = {
  render: function() {
    document.getElementById('topbarTitle').textContent = 'Get Started';
    document.getElementById('topbarActions').innerHTML = '';
    document.getElementById('contentArea').innerHTML =
      '<div style="max-width:560px;margin:40px auto;padding:0 16px;">' +
        '<div class="card">' +
          '<div class="card-title">Welcome to The Railsplitter Editor</div>' +
          '<p style="font-size:13px;color:#888;margin-bottom:24px;">Follow these three steps to connect your GitHub account.</p>' +

          '<div style="margin-bottom:20px;">' +
            '<div style="font-size:11px;font-weight:700;color:#C85500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Step 1 — Create a GitHub account</div>' +
            '<p style="font-size:13px;color:#555;margin:0;">' +
              'Go to <a href="https://github.com/signup" target="_blank" style="color:#C85500;text-decoration:underline;">github.com/signup</a> and create a free account. Any email address works.' +
            '</p>' +
          '</div>' +

          '<div style="margin-bottom:20px;">' +
            '<div style="font-size:11px;font-weight:700;color:#C85500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Step 2 — Get access from your advisor</div>' +
            '<p style="font-size:13px;color:#555;margin:0;">' +
              'Tell your faculty advisor your GitHub username. They\'ll add you to the newspaper\'s repository. You\'ll get a confirmation email from GitHub.' +
            '</p>' +
          '</div>' +

          '<div style="margin-bottom:24px;">' +
            '<div style="font-size:11px;font-weight:700;color:#C85500;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">Step 3 — Create your access token</div>' +
            '<p style="font-size:13px;color:#555;margin-bottom:8px;">' +
              'In GitHub: click your <strong>profile picture</strong> (top-right) &rarr; <strong>Settings</strong> &rarr; <strong>Developer settings</strong> (bottom of left sidebar) &rarr; <strong>Personal access tokens</strong> &rarr; <strong>Tokens (classic)</strong> &rarr; <strong>Generate new token (classic)</strong>' +
            '</p>' +
            '<ul style="font-size:13px;color:#555;margin:0;padding-left:18px;line-height:1.8;">' +
              '<li>Set expiration to <strong>1 year</strong></li>' +
              '<li>Check the <strong><code style="background:#f0ede8;padding:1px 4px;border-radius:3px;">repo</code></strong> scope</li>' +
              '<li>Click <strong>Generate token</strong></li>' +
              '<li>Copy the token — it starts with <code style="background:#f0ede8;padding:1px 4px;border-radius:3px;">ghp_</code> and won\'t be shown again</li>' +
            '</ul>' +
          '</div>' +

          '<div style="border-top:1px solid #e8e5e0;padding-top:20px;">' +
            '<div class="field"><label>Paste your token here</label>' +
              '<input type="password" id="setupTokenInput" placeholder="ghp_...">' +
            '</div>' +
            '<button class="btn btn-primary" id="setupConnectBtn">Connect</button>' +
            '<div id="setupStatus" style="margin-top:10px;font-size:12px;min-height:18px;"></div>' +
          '</div>' +
        '</div>' +
      '</div>';

    document.getElementById('setupConnectBtn').addEventListener('click', function() {
      var token = document.getElementById('setupTokenInput').value.trim();
      if (!token) return;
      var btn = document.getElementById('setupConnectBtn');
      btn.disabled = true;
      App.auth.connect(token, function(state, detail) {
        var statusEl = document.getElementById('setupStatus');
        if (state === 'connecting') {
          statusEl.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px;"></span> Connecting…';
        } else if (state === 'error') {
          btn.disabled = false;
          if (detail === 'no_push_access') {
            statusEl.innerHTML = '<span style="color:#b91c1c;">✗ Access denied — your account doesn\'t have access yet. Contact your faculty advisor (Step 2).</span>';
          } else {
            statusEl.innerHTML = '<span style="color:#b91c1c;">✗ Token not recognised. Double-check you copied the full token starting with <code>ghp_</code>.</span>';
          }
        }
        // On success App.auth.connect navigates to articles — no status update needed
      });
    });
  }
};
```

- [ ] **Step 2: Verify setup view in browser**

Clear localStorage and reload:
```js
localStorage.removeItem('rs_token'); location.reload();
```
Expected:
- Sidebar shows only brand; nav and footer hidden
- Content area shows the three-step card with "Get Started" in the topbar
- Pasting a bad token shows the red error message
- Pasting a valid token with repo access signs in, reveals sidebar nav, navigates to All Articles

- [ ] **Step 3: Commit**
```bash
git add editor.html
git commit -m "feat: add first-time setup view with three-step onboarding guide"
```

---

## Task 6: Simplify `App.views.settings`

**Files:**
- Modify: `editor.html` — `App.views.settings.render` (lines ~501–579)

- [ ] **Step 1: Replace `App.views.settings` render function**

Find the entire `App.views.settings` block (from `App.views.settings = {` to its closing `};`) and replace it with:

```javascript
// ── Settings view ──────────────────────────────────────────────────────────
App.views.settings = {
  render: function() {
    document.getElementById('topbarTitle').textContent = 'Settings';
    document.getElementById('topbarActions').innerHTML = '';

    document.getElementById('contentArea').innerHTML =
      '<div class="settings-wrap">' +
        '<div class="card">' +
          '<div class="card-title">Account</div>' +
          '<p style="font-size:13px;color:#555;margin-bottom:14px;">Signed in as <strong>@' + App.esc(App.state.user || '') + '</strong></p>' +
          '<button class="btn btn-danger" id="signOutBtn">Sign out</button>' +
        '</div>' +
        '<div class="card">' +
          '<div class="card-title">Change Token</div>' +
          '<div class="field"><label>Personal Access Token</label>' +
            '<input type="password" id="tokenInput" value="' + App.esc(localStorage.getItem('rs_token') || '') + '" placeholder="ghp_...">' +
          '</div>' +
          '<button class="btn btn-primary" id="saveTokenBtn">Save &amp; Reconnect</button>' +
          '<div id="settingsTokenStatus" style="margin-top:12px;font-size:12px;min-height:18px;"></div>' +
        '</div>' +
        '<div class="card">' +
          '<div class="card-title">Repository</div>' +
          '<div class="field"><label>Owner</label><input type="text" id="repoOwner" value="' + App.esc(App.REPO_OWNER) + '"></div>' +
          '<div class="field"><label>Repository name</label><input type="text" id="repoName" value="' + App.esc(App.REPO_NAME) + '"></div>' +
          '<button class="btn btn-secondary" id="saveRepoBtn">Update Repository</button>' +
        '</div>' +
      '</div>';

    document.getElementById('signOutBtn').addEventListener('click', function() {
      App.auth.signOut();
    });

    document.getElementById('saveTokenBtn').addEventListener('click', function() {
      var token = document.getElementById('tokenInput').value.trim();
      if (!token) return;
      var btn = document.getElementById('saveTokenBtn');
      btn.disabled = true;
      App.auth.connect(token, function(state, detail) {
        var statusEl = document.getElementById('settingsTokenStatus');
        if (state === 'connecting') {
          statusEl.innerHTML = '<span class="spinner" style="width:12px;height:12px;border-width:2px;"></span> Connecting…';
        } else if (state === 'error') {
          btn.disabled = false;
          if (detail === 'no_push_access') {
            statusEl.innerHTML = '<span style="color:#b91c1c;">✗ Access denied.</span>';
          } else {
            statusEl.innerHTML = '<span style="color:#b91c1c;">✗ Token invalid or expired.</span>';
          }
        }
      });
    });

    document.getElementById('saveRepoBtn').addEventListener('click', function() {
      App.REPO_OWNER = document.getElementById('repoOwner').value.trim();
      App.REPO_NAME  = document.getElementById('repoName').value.trim();
      App.showSuccess('Repository updated.');
    });
  }
};
```

- [ ] **Step 2: Verify settings view in browser**

Sign in with a valid token, then click Settings in the sidebar. Expected:
- Shows "Signed in as @username" with a Sign out button
- No onboarding steps
- "Change Token" card and "Repository" card present
- Clicking "Sign out" clears session, hides nav, shows the setup view

- [ ] **Step 3: Commit**
```bash
git add editor.html
git commit -m "feat: simplify Settings to account management, move onboarding to setup view"
```

---

## Task 7: Full end-to-end verification

No code changes — verification only.

- [ ] **Scenario A: First-time visitor (no token)**
  1. `localStorage.removeItem('rs_token'); location.reload()`
  2. Expected: brand-only sidebar, three-step setup card, topbar says "Get Started"

- [ ] **Scenario B: Invalid token**
  1. On setup view, paste a garbage string, click Connect
  2. Expected: red error "Token not recognised…"

- [ ] **Scenario C: Valid token, no repo access**
  1. Paste a valid GitHub token from an account that is NOT a collaborator on the repo
  2. Expected: red error "Access denied — your account doesn't have access yet…"

- [ ] **Scenario D: Valid token with repo access**
  1. Paste a valid token from an authorised account
  2. Expected: sidebar nav appears, topbar shows "All Articles", footer shows "@username"

- [ ] **Scenario E: Return visit (token in localStorage)**
  1. Reload page with token saved
  2. Expected: spinner briefly, then navigates straight to All Articles — no setup screen

- [ ] **Scenario F: Sign out**
  1. From any view, click Settings → Sign out
  2. Expected: nav hidden, setup view shown, localStorage has no `rs_token`

- [ ] **Scenario G: Change token in Settings**
  1. Sign in, go to Settings, paste a new valid token, click Save & Reconnect
  2. Expected: reconnects, navigates to All Articles

- [ ] **Final commit**
```bash
git add editor.html
git commit -m "chore: verified onboarding and auth refactor end-to-end"
```
