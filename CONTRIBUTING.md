# Contributing to OpenScience-Reflections

All contributions are welcome — short essays, commentaries, or links to relevant discussions.

---

## Add a Reflection

Create a Markdown file at:

reflections/YYYY/MM/YYYY-MM-DDTHH-MM-SSZ-title.md

Front matter (YAML):

```yaml
id: provisional
author: <your-name-or-handle>
tags: [open-science, reproducibility]
summary: <≤160-character summary>
status: note   # draft | note | decision | takeaway | erratum
```

The CI workflow will replace `id: provisional` with a hash-based ID and update `index.json`.

---

## Writing Style

- Concise and reflective (≤400 words).
- Plain language — avoid jargon.
- Provide links or citations for context.

---

## Commit Message

```
reflection: first note on openness as method
```
