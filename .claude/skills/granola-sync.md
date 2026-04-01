---
name: granola-sync
description: "Import meetings from Granola into Knowledge/meetings/. Use when the user asks to import, sync, or update meetings from a specific date or date range."
user-invocable: true
argument-hint: "[date or date range, e.g. 'today', 'yesterday', 'March 17-21']"
---

# Granola Meeting Sync

Import meeting transcripts from Granola (via MCP) into the local Knowledge/meetings/ folder structure.

## Prerequisites

This skill requires the Granola MCP server to be configured. If not set up, tell the user to add the following to their MCP configuration:

```json
{
  "granola": {
    "type": "http",
    "url": "https://mcp.granola.ai/mcp"
  }
}
```

## Workflow

### Step 1: Determine date range

Parse `$ARGUMENTS` to determine which meetings to import:
- `today` or no argument: today's date
- `yesterday`: yesterday's date
- `March 17` or `2026-03-17`: specific date
- `March 17-21` or `last week`: date range
- `since Monday`: from the specified day to today

### Step 2: Fetch meetings from Granola

1. Use `mcp__granola__list_meetings` to get meetings in the date range.
2. For each meeting, use `mcp__granola__get_meeting_transcript` to get the full content.

### Step 3: Check for duplicates

1. For each fetched meeting, check if a file already exists in `Knowledge/meetings/YYYY-MM/` with a matching date and similar title.
2. Use fuzzy title matching (normalize to lowercase, strip punctuation) to detect duplicates.
3. Skip duplicates. Report them to the user.

### Step 4: Write meeting files

For each new (non-duplicate) meeting, create a file at:
```
Knowledge/meetings/YYYY-MM/YYYY-MM-DD-meeting-title-slugified.md
```

File format:
```markdown
---
title: [Meeting Title]
date: YYYY-MM-DD
time: HH:MM
participants: [list of attendees]
source: granola
---

## Summary
[Granola's summary or first section]

## Notes
[Full transcript/notes content]

## Action Items
[Extract any action items mentioned in the transcript]
```

### Step 5: Handle recurring meetings

1. Check if the meeting title matches any series in `Knowledge/meetings/recurring/`.
2. If it does, also save a copy (or symlink reference) in the recurring series folder.
3. If the meeting appears to be part of a recurring series but no folder exists yet, note this but don't create the folder automatically.

### Step 6: Update last import marker

Write the current date to `.granola_last_import` so future imports know where to start.

### Step 7: Report

Summarize:
- Meetings imported: X
- Duplicates skipped: X
- List each imported meeting with its file path
- Any meetings that matched recurring series
