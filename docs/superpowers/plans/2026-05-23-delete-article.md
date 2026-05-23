# Delete Article Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Delete Article action to the editor — available in the All Articles list and the Article Editor, with reference cleanup and an immediate GitHub commit.

**Architecture:** All changes live in the single `editor.html` file. A shared `App.deleteArticle(id)` function handles the confirm dialog, reference cleanup, and GitHub commit. Two entry points (articles list row, article editor view) call this shared function. No new files.

**Tech Stack:** Vanilla JS, browser `confirm()`, existing `App.github.saveContent()` / `App.handleApiError()` APIs.

---

### Task 1: Add `App.deleteArticle(id)` shared helper

**Files:**
- Modify: `editor.html` — insert after line 417 (after `App.articleById`)

- [ ] **Step 1: Insert the helper function**

  In `editor.html`, find this block (around line 415):

  ```js
  articleById: function(id) {
    return App.state.content.articles.find(function(a) { return a.id === id; });
  },
  ```

  Add the following immediately after it (before `sectionBySlug`):

  ```js
  deleteArticle: function(id) {
    var a = App.articleById(id);
    if (!a) return Promise.resolve();
    var title = a.title;
    var hp = App.state.content.homepage;

    var refs = [];
    if (hp.hero === id) refs.push('Homepage hero');
    if (hp.heroAside === id) refs.push('Homepage hero aside');
    Object.keys(hp.sections || {}).forEach(function(slug) {
      (hp.sections[slug] || []).forEach(function(slotId, idx) {
        if (slotId === id) refs.push('Homepage: ' + slug + ' slot ' + (idx + 1));
      });
    });
    (App.state.content.issues || []).forEach(function(issue) {
      if (issue.coverArticle === id) refs.push('Issue cover: ' + issue.title);
    });

    var msg = 'Delete "' + title + '"?';
    if (refs.length) {
      msg += '\n\nThis article is referenced in:\n' +
        refs.map(function(r) { return '- ' + r; }).join('\n') +
        '\n\nThose slots will be cleared. This cannot be undone.';
    } else {
      msg += '\n\nThis cannot be undone.';
    }

    if (!confirm(msg)) return Promise.resolve();

    App.state.content.articles = App.state.content.articles.filter(function(art) {
      return art.id !== id;
    });

    if (hp.hero === id) hp.hero = null;
    if (hp.heroAside === id) hp.heroAside = null;
    Object.keys(hp.sections || {}).forEach(function(slug) {
      if (hp.sections[slug]) {
        hp.sections[slug] = hp.sections[slug].map(function(slotId) {
          return slotId === id ? null : slotId;
        });
      }
    });
    (App.state.content.issues || []).forEach(function(issue) {
      if (issue.coverArticle === id) issue.coverArticle = null;
    });

    return App.github.saveContent('Delete: ' + title);
  },
  ```

- [ ] **Step 2: Verify the helper loads without errors**

  Open `editor.html` in a browser (or via `python3 -m http.server 8000` and visit `http://localhost:8000/editor.html`). Open the browser console. Log in with a GitHub token. Run:

  ```js
  typeof App.deleteArticle
  ```

  Expected: `"function"`

- [ ] **Step 3: Commit**

  ```bash
  git add editor.html
  git commit -m "feat: add App.deleteArticle shared helper"
  ```

---

### Task 2: Delete button in the All Articles list

**Files:**
- Modify: `editor.html` — inside `App.views.articles.render()` (~line 690)

- [ ] **Step 1: Add the Delete button to each row**

  In `editor.html`, find the last `<td>` in the articles row builder (around line 703):

  ```js
  '<td style="padding:10px 12px;">' +
    '<a href="#" class="art-link btn btn-secondary" data-id="' + App.esc(a.id) + '" style="font-size:12px;">Edit</a>' +
  '</td>' +
  ```

  Replace it with:

  ```js
  '<td style="padding:10px 12px;white-space:nowrap;">' +
    '<a href="#" class="art-link btn btn-secondary" data-id="' + App.esc(a.id) + '" style="font-size:12px;">Edit</a>' +
    ' <button class="art-delete btn btn-danger" data-id="' + App.esc(a.id) + '" style="font-size:12px;">Delete</button>' +
  '</td>' +
  ```

- [ ] **Step 2: Add the click handler**

  In the same `render()` function, find the event-listener block that follows the table HTML (around line 723):

  ```js
  document.querySelectorAll('.art-link').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault();
      App.router.navigate('articleEditor', { articleId: link.dataset.id });
    });
  });
  ```

  Add the following immediately after it:

  ```js
  document.querySelectorAll('.art-delete').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var id = btn.dataset.id;
      App.deleteArticle(id).then(function() {
        App.showSuccess('Article deleted.');
        App.views.articles.render();
      }).catch(function(err) {
        App.handleApiError(err);
      });
    });
  });
  ```

- [ ] **Step 3: Verify in browser**

  Navigate to the All Articles view. Each row should now have a red Delete button next to Edit.

  - Click Delete on an article with no references — confirm dialog should say: `Delete "Headline"?\n\nThis cannot be undone.`
  - Click Cancel — article should remain in the list.
  - Click Delete again and confirm — the row disappears, a green "Article deleted." notice appears. (This commits to GitHub, so only do this on a test/draft article.)

- [ ] **Step 4: Commit**

  ```bash
  git add editor.html
  git commit -m "feat: add delete button to articles list"
  ```

---

### Task 3: Delete button in the Article Editor view

**Files:**
- Modify: `editor.html` — inside `App.views.articleEditor.render()` (~line 867 and ~line 1029)

- [ ] **Step 1: Add the Danger Zone HTML to the content area**

  In `editor.html`, find the end of the `contentArea` innerHTML assignment in `App.views.articleEditor.render()`. It currently ends with (around line 866):

  ```js
      '</div></div>' +
    '</div>';
  ```

  That closing `'</div>';` ends the `editor-grid` div. Replace just that final line with:

  ```js
      '</div></div>' +
    '</div>' +
    '<div style="margin-top:24px;padding-top:16px;border-top:1px solid #e8e5e0;">' +
      '<button class="btn btn-danger" id="deleteArticleBtn" style="font-size:13px;">Delete Article</button>' +
    '</div>';
  ```

- [ ] **Step 2: Wire the Delete Article button**

  In the same `render()` function, find the last event-listener lines (around line 1028):

  ```js
  document.getElementById('saveDraftBtn').addEventListener('click', function() { collectAndSave(false); });
  document.getElementById('publishBtn').addEventListener('click', function() { collectAndSave(true); });
  ```

  Add the following immediately after:

  ```js
  document.getElementById('deleteArticleBtn').addEventListener('click', function() {
    var id = App.state.articleId;
    App.deleteArticle(id).then(function() {
      App.showSuccess('Article deleted.');
      App.router.navigate('articles');
    }).catch(function(err) {
      App.handleApiError(err);
    });
  });
  ```

- [ ] **Step 3: Verify in browser**

  Open any article in the editor. At the bottom of the content area, below the editor grid, a red "Delete Article" button should appear.

  - Click it — confirm dialog should appear with the article title.
  - Click Cancel — nothing changes, you stay on the editor page.
  - Click Delete and confirm — editor navigates back to All Articles, success notice appears, the deleted article is gone from the list.

  To test the references warning: in the browser console run:
  ```js
  App.state.content.homepage.hero = App.state.articleId;
  ```
  Then click Delete — the dialog should list "Homepage hero" in the references.

- [ ] **Step 4: Commit**

  ```bash
  git add editor.html
  git commit -m "feat: add delete button to article editor view"
  ```
