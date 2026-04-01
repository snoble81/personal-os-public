---
name: sync-offsite-tracker
description: "Sync a project tracker with tasks and reference docs. Use on Monday mornings to import meeting transcripts, update tracker reference doc, and keep task files in sync."
user-invocable: true
argument-hint: "[optional: 'skip-granola' to skip meeting import, or specific date range]"
---

# Sync Project Tracker

Weekly Monday morning workflow that imports meetings, syncs tracker status, updates task files, and refreshes the master to-do list.

## Overview

This skill orchestrates the weekly sync by running these steps in sequence:
1. Import recent meetings from Granola
2. Read the project tracker (CSV export from Google Sheets or similar)
3. Cross-reference meetings against tracker items
4. Update the reference doc with changes
5. Sync individual task files (Progress Logs, statuses)
6. Refresh Tasks/TODO.md (the master to-do list)

## Workflow

### Step 1: Import meetings

Unless `$ARGUMENTS` contains `skip-granola`:
1. Determine the date range: last Friday through today (Monday)
2. Run the `/granola-sync` skill for that date range
3. Note which meetings were imported for Step 3

### Step 2: Read tracker

1. Look for the tracker reference doc in `Documents/` (the user should have a file tracking their action items from a recurring project or team meeting)
2. If a CSV export exists in the task subfolder, read it for the latest status

### Step 3: Cross-reference meetings with tracker

For each meeting imported in Step 1:
1. Scan for mentions of tracker items (by title, keyword, or project name)
2. Identify status changes: items discussed as "done", "blocked", "in progress", etc.
3. Identify new action items assigned to the user
4. Flag items that appear stale (in tracker but not mentioned in any recent meeting)

### Step 4: Update reference doc

Update the tracker reference doc with:
- Status changes detected from meetings
- New items added
- Date of last update
- Source meeting references for each change

### Step 5: Sync task files

For each active task in `Tasks/`:
1. Check if any imported meetings reference this task
2. If so, add a Progress Log entry with the date and what was discussed
3. Update task status if the meeting indicates a change
4. Add meeting file to `resource_refs` if not already there
5. If the task has a subfolder with META.md, update the Relevant Meetings list and Changelog

### Step 6: Refresh TODO.md

Rebuild `Tasks/TODO.md` by:
1. Scanning last week's meetings for new action items assigned to the user
2. Checking off items that meetings confirm are done
3. Adding new items with source references
4. Flagging stale P0/P1 items (untouched 14+ days)
5. Running a relevance check against user's initiatives/goals from GOALS.md
6. Removing items that don't belong on the user's plate
7. Organizing by priority tier (P0 today, P1 this week, P1 this month, P2 scheduled, tracking items)

### Step 7: Report

Summarize:
- Meetings imported: X
- Tracker items updated: X
- New action items found: X
- Tasks synced: X
- Stale items flagged: X
- TODO.md changes: items added/removed/checked off
