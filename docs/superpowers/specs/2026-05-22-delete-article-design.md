# Delete Article Feature — Design Spec

**Date:** 2026-05-22
**Project:** The Railsplitter — editor.html

## Summary

Add a Delete Article action to the browser-based CMS editor. Delete is available in two places: the All Articles table and the Article Editor view. Deletion is hard (removes the article from `content.json`), commits immediately to GitHub, and automatically clears any references to the deleted article.

---

## 1. Entry Points

### All Articles list
Each row in the articles table gains a Delete button alongside the existing Edit button. Styled with `btn-danger` (red, consistent with section and issue Delete buttons).

### Article Editor view
A "Delete Article" danger button appears at the bottom of the editing form, below the Save Draft / Publish buttons, in its own row.

Both entry points call the same shared `deleteArticle(id)` function.

---

## 2. Confirmation Dialog

Before deleting, the editor scans for active references and shows a `confirm()` dialog:

**No references:**
```
Delete "Headline"? This cannot be undone.
```

**With references:**
```
Delete "Headline"?

This article is referenced in:
- Homepage hero
- Homepage: sports slot
- Issue 7 cover

Those slots will be cleared. This cannot be undone.
```

The reference scan runs before the dialog so the warning text is accurate.

---

## 3. Reference Cleanup

`deleteArticle(id)` performs these steps in order before committing:

1. Remove the article from `content.articles[]`
2. Null `homepage.hero` if it equals the deleted id
3. Null `homepage.heroAside` if it equals the deleted id
4. Walk `homepage.sections` — for each section's slot array, set any element matching the deleted id to `null`
5. Walk `content.issues` — set `coverArticle` to `null` on any issue that references the deleted id

After cleanup, calls `App.github.saveContent('Delete: ' + title)`.

---

## 4. Post-Delete Navigation

- **From the articles list:** re-render the list in place (the deleted row disappears).
- **From the article editor:** navigate back to the All Articles list (`App.router.navigate('articles')`).

In both cases, `App.showSuccess('Article deleted.')` displays a confirmation notice.

---

## 5. Commit Strategy

Uses `App.github.saveContent('Delete: ' + title)` — same immediate-commit pattern as article save/publish. No `markDirty` / Push All involvement. The GitHub commit serves as the undo record.

---

## 6. Error Handling

On GitHub API failure, `App.handleApiError(err)` is called (existing pattern). The article remains in the in-memory state so the user can retry.

---

## Out of Scope

- Soft delete / trash / recovery flow
- Bulk delete
- Undo after commit
