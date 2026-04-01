---
name: ai-pm-weekly
description: "Generate a weekly PM speed round update. Use on Monday mornings to compile 4-5 bullet points from the past week's meetings for a recurring weekly team meeting."
user-invocable: true
argument-hint: "[optional: date range like 'last week' or 'March 17-21']"
---

# Weekly PM Speed Round Update

Generate a concise weekly update for a recurring team meeting. Pulls from meeting notes to create 4-5 bullet points covering key developments.

## Workflow

### Step 1: Gather meeting notes from the past week

1. Determine the date range: default is the previous Monday through Friday. If `$ARGUMENTS` specifies a range, use that.
2. Find all meeting files in `Knowledge/meetings/` for the date range.
3. Also check `Knowledge/meetings/recurring/` for series meetings that fell within the range.

### Step 2: Extract key developments

For each meeting, extract:
- Decisions made
- Status changes on active initiatives
- New commitments or action items assigned to the user
- Key updates from partners, stakeholders, or cross-functional teams
- Blockers raised or resolved

### Step 3: Synthesize into bullets

Create 4-5 bullet points that:
- Lead with the most important development
- Are concise (1-2 sentences each)
- Focus on "what changed" not "what was discussed"
- Group related updates into single bullets where possible
- Include specific names, dates, and deliverables (not vague summaries)

### Step 4: Format output

```markdown
## Weekly Update - [Date Range]

- **[Topic 1]:** [Concise update on what changed/happened]
- **[Topic 2]:** [Concise update]
- **[Topic 3]:** [Concise update]
- **[Topic 4]:** [Concise update]
- **[Topic 5]:** [Concise update] (optional)
```

### Style guidelines
- No filler words or throat-clearing
- Use specific facts, not "good progress was made"
- If a bullet references a deliverable, include the timeline
- If a bullet references a blocker, include who owns it
