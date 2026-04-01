---
name: gather-todos
description: "Scan all sources for open to-do items, deduplicate, flag stale items, and build a consolidated index. Use on demand to get a complete view of outstanding work."
user-invocable: true
argument-hint: "[optional: keyword filter like 'MCP', or 'stale', 'past-due']"
---

# Gather To-Dos

On-demand consolidated view of all open to-do items across the entire repo. Scans task files, meeting notes, backlog, and documents to find every outstanding action item.

## Workflow

### Step 1: Check cache

1. Look for `Tasks/TODO-INDEX.md` and check its last-modified date
2. If it exists and was modified within the last 24 hours, use it as the base (skip to Step 4 for filtering)
3. If stale or missing, proceed with full scan

### Step 2: Scan all sources

Scan these locations for open to-do items:

**Task files** (`Tasks/`):
- Read all `.md` files with `status: n`, `status: s`, or `status: b`
- Extract title, priority, status, and next actions

**Meeting notes** (`Knowledge/meetings/`):
- Scan recent meetings (last 30 days) for `## Action Items` sections
- Look for unchecked items (`- [ ]`) assigned to the user
- Cross-reference against existing tasks to avoid double-counting

**Backlog** (`BACKLOG.md`):
- Read any unprocessed items
- Flag them as "unprocessed backlog" in the index

**Documents** (`Documents/`):
- Scan for unchecked to-do items in active documents
- Only include items that look like action items (not spec checklists or templates)

### Step 3: Deduplicate

1. Compare items by title similarity (fuzzy match, threshold 0.6)
2. If an action item from a meeting matches an existing task, link them (don't duplicate)
3. If multiple sources mention the same item, keep the task file version as canonical

### Step 4: Apply filters

If `$ARGUMENTS` contains a keyword:
- `stale`: show only items untouched for 14+ days
- `past-due`: show only items past their due_date
- `[keyword]`: filter items matching the keyword in title or content (e.g., "MCP", "legal")

### Step 5: Build index

Write `Tasks/TODO-INDEX.md`:

```markdown
# To-Do Index

*Generated: YYYY-MM-DD HH:MM*
*Filter: [filter if applied]*

## Summary
- Total open items: X
- P0: X | P1: X | P2: X | P3: X
- Stale (14+ days): X
- Unprocessed backlog items: X

## By Priority

### P0 - Do Today
- [ ] [Task title](Tasks/path.md) - status: [s/n/b] - last updated: [date]

### P1 - This Week
- [ ] [Task title](Tasks/path.md) - status: [s/n/b] - last updated: [date]

### P2 - Scheduled
...

### Unprocessed
- [ ] [Item from BACKLOG.md] (source: BACKLOG.md)
- [ ] [Action item from meeting] (source: Knowledge/meetings/YYYY-MM/file.md)
```

### Step 6: Report

Display the index to the user. Highlight:
- Any P0/P1 items that are stale
- Unprocessed backlog items
- Action items from meetings that don't have corresponding tasks yet
