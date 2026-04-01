---
name: task-hygiene
description: "Organize tasks into fiscal quarter folders, file documents, archive completed tasks, and keep the task hierarchy clean. Run periodically (e.g. Monday mornings) or when asked to clean up tasks."
user-invocable: true
argument-hint: "[optional: quarter to organize, e.g. FY27-Q1]"
---

# Task Hygiene & Organization

Periodic cleanup of the Tasks/ folder hierarchy. Ensures tasks are filed by fiscal quarter, documents are grouped with their tasks, and completed work is archived.

## Task Folder Hierarchy

```
Tasks/
  FY27-Q1/                          # Fiscal quarter
    simple-task.md                   # Simple task (no dedicated docs)
    complex-task/                    # Task with dedicated documents
      META.md                        # Metadata index: summary, timeline, contents, meetings, changelog
      task.md                        # The task file (always named task.md)
      related-doc.md                 # Documents produced for this task
      data/                          # Supporting data files
  FY27-Q2/                          # Next quarter
  archive/                          # Completed/stale tasks
  TODO.md                           # Master to-do list (stays at root)
  DASHBOARD.md                      # Dashboard (stays at root)
  README.md                         # README (stays at root)
```

### Fiscal Quarter Mapping (customize for your org)
- **Q1:** Feb 1 - Apr 30
- **Q2:** May 1 - Jul 31
- **Q3:** Aug 1 - Oct 31
- **Q4:** Nov 1 - Jan 31

### Rules
- Tasks with `status: d` (done) older than 30 days go to `archive/`
- Tasks with `status: r` (recurring) stay in the current quarter folder
- When a task has dedicated document outputs (specs, one-pagers, scripts, data files), create a named subfolder and rename the task file to `task.md`
- When a task only references shared Knowledge/ files, keep it as a flat .md file in the quarter folder
- Documents in `Documents/` that are clearly outputs of a single task should be moved into that task's folder
- Documents referenced by multiple tasks stay in `Documents/`
- Knowledge/ files never move (they are shared reference material)
- `TODO.md`, `DASHBOARD.md`, `README.md`, and `TODO-archive.md` stay at `Tasks/` root

## Workflow

### Step 1: Scan for tasks needing organization

1. List all .md files directly in `Tasks/` (not in subfolders). These are unfiled tasks.
2. Read each task's frontmatter to get status, priority, and created_date.
3. Categorize:
   - `status: d` and older than 30 days -> archive
   - Active tasks (n, s, b, r) -> file into the appropriate quarter folder based on created_date
   - If unsure which quarter, use current quarter

### Step 2: Identify tasks that need subfolders

1. For each active task, check its `resource_refs` for Documents/ paths.
2. If a task has 2+ dedicated documents in Documents/, create a named subfolder.
3. Move the task file as `task.md` and move its dedicated documents alongside it.
4. Create a `META.md` file in the subfolder (see META.md format below).
5. Update `resource_refs` paths in the task file to reflect new locations.

### Step 3: Archive completed tasks

1. Move `status: d` tasks older than 30 days to `archive/`.
2. If the task had a subfolder, move the entire subfolder to `archive/`.

### Step 4: Report

Summarize what was moved:
- Tasks filed: X
- Tasks archived: X
- Documents filed with tasks: X
- Any tasks that need attention (missing status, stale started tasks, etc.)

## META.md Format

Every task subfolder must have a `META.md` at its root with:

```markdown
# Task Title

**Started:** YYYY-MM-DD
**Target:** YYYY-MM-DD or TBD or description (e.g., "H2 FY27")
**Status:** Current status description
**Priority:** P0/P1/P2/P3

## Summary
1-3 sentence description of the task and its current state.

## Folder Contents
| File | Description |
|------|-------------|
| `task.md` | ... |
| `doc.md` | ... |

## Relevant Meetings
- `Knowledge/meetings/YYYY-MM/file.md` -- brief description

## Changelog
| Date | Change |
|------|--------|
| YYYY-MM-DD | What happened |
```

**Changelog rules:**
- Add an entry when files are added/removed from the folder
- Add an entry when meeting context updates the task details
- Add an entry when status, priority, or target changes
- Keep entries concise (one line each)
- The granola-sync skill will automatically append meeting references and changelog entries when it detects relevant meetings

## For Other Skills

Other skills that create or reference tasks should be aware of this hierarchy:

- **Creating a new task:** File it in `Tasks/{current-quarter}/`. If it will have dedicated documents, create a subfolder with a `META.md` immediately.
- **Referencing a task:** Look in the appropriate quarter folder first, then check `Tasks/` root for unfiled tasks.
- **Finding documents for a task:** Check the task's subfolder first, then `Documents/`, then `Knowledge/`.
- **Saving external inputs** (someone else's PRD, use case doc, raw data): Save directly into the relevant task subfolder, not `Knowledge/projects/`. The projects folder is legacy reference material.
- **Path convention:** Task subfolders use kebab-case names derived from the task title. The task file inside is always `task.md`.
- **Updating a task:** When adding files or meeting context to a task subfolder, always update `META.md` (Folder Contents table, Relevant Meetings list, and Changelog).
