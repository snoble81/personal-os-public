---
name: lint
description: "Run a health check across PersonalOS: stale indexes, broken links, inconsistent decisions, aging tasks, and missing metadata. Use weekly or when things feel out of sync."
user-invocable: true
argument-hint: "[optional: 'fix' to auto-fix safe issues, or section name like 'tasks' or 'meetings']"
---

# Lint / Health Check

Periodic health scan of the PersonalOS repository. Finds inconsistencies, staleness, broken references, and structural issues.

## Checks to Run

### 1. Index Freshness

- Read the footer of `INDEX.md` for its "Last rebuilt" timestamp
- If older than 7 days, flag as **stale** and suggest running `/rebuild-index`
- Check if `Tasks/TODO-INDEX.md` exists and its age

**Output:** "INDEX.md: rebuilt X days ago [OK/STALE]"

### 2. Task Health

For each task file in active quarter folders under `Tasks/`:

- **Missing frontmatter fields:** flag tasks missing `title`, `priority`, `status`, or `category`
- **Stale started tasks:** flag `status: s` tasks with file modification date older than 14 days
- **Priority limit violations:** count P0 tasks (limit 3), P1 (limit 5), P2 (limit 10)
- **Orphaned subfolders:** task subfolders missing `task.md` or `META.md`
- **Broken resource_refs:** for each `resource_refs` path, verify the file exists. Flag broken links.
- **Done but not archived:** `status: d` tasks older than 30 days still in the active quarter folder

**Output:** Table of issues found, grouped by severity (error/warning/info)

### 3. Meeting Hygiene

- **Recurring series META.md freshness:** for each `Knowledge/meetings/recurring/*/META.md`, check if it's been updated in the last 14 days. Flag stale ones.
- **Active topics without linked tasks:** scan META.md active topics tables for empty "Linked Task" cells. Flag topics that should probably have a task.
- **Orphaned meeting files:** meetings in the root of `Knowledge/meetings/` not inside a YYYY-MM folder

**Output:** List of stale series and unlinked topics

### 4. Decision Log Consistency (if `Knowledge/decision-log.md` exists)

- **Staleness:** flag if "Last updated" is older than 14 days
- **Contradictions:** scan for entries in the same section that appear to conflict (e.g., different dates for the same milestone) without one being marked superseded
- **References to deleted files:** verify source file references still exist

**Output:** List of potential contradictions and stale entries

### 5. TODO.md Alignment

- Read `Tasks/TODO.md` (if it exists)
- **Ghost tasks:** TODO.md references task files that no longer exist
- **Missing from TODO:** P0/P1 tasks that exist in task folders but aren't mentioned in TODO.md
- **Stale items:** TODO.md items not updated in 14+ days (check linked task file modification dates)
- **Checked items still listed:** items marked `[x]` that have been done for 7+ days (should be removed or archived)

**Output:** List of alignment issues

### 6. GOALS.md Currency

- Check "Last updated" date in GOALS.md
- Flag if older than 30 days
- Check if top 3 priorities still match the P0 tasks in the system

**Output:** Freshness status and alignment check

### 7. Hot Cache Freshness

- If `Knowledge/HOT.md` exists, check its "Last refreshed" timestamp
- Flag if older than 7 days

**Output:** Freshness status

### 8. Meeting Wiki Index Freshness

- If `Knowledge/meetings/WIKI-INDEX.md` exists, check its timestamp
- Flag if older than 14 days

**Output:** Freshness status

## Steps

### Step 1: Run all checks in parallel

Launch parallel Grep/Glob/Read calls for each independent check section. Minimize sequential reads.

### Step 2: Compile results

Organize findings into a report:

```markdown
## PersonalOS Health Check -- YYYY-MM-DD

### Summary
| Check | Status | Issues |
|-------|--------|--------|
| Index freshness | OK/STALE | ... |
| Task health | X errors, Y warnings | ... |
| Meeting hygiene | ... | ... |
| Decision log | ... | ... |
| TODO alignment | ... | ... |
| GOALS currency | ... | ... |
| Hot cache | ... | ... |
| Wiki index | ... | ... |

### Errors (must fix)
...

### Warnings (should fix)
...

### Info (nice to know)
...

### Suggested Actions
1. Run `/rebuild-index` (index is X days stale)
2. Archive 3 done tasks older than 30 days
3. ...
```

### Step 3: Auto-fix (if `$ARGUMENTS` contains "fix")

Safe auto-fixes only:
- Run `/rebuild-index` if index is stale
- Archive `status: d` tasks older than 30 days
- Remove checked-off items from TODO.md that are 7+ days old
- Update "Last updated" dates where the content was actually refreshed

Do NOT auto-fix:
- Broken resource_refs (might be intentional or renamed)
- Decision log contradictions (need user judgment)
- Missing frontmatter (need user input on values)

### Step 4: Section filter

If `$ARGUMENTS` contains a section name (e.g., "tasks", "meetings", "decisions"), only run that section's checks.

## Rules

- Never modify files unless "fix" mode is explicitly requested
- Keep the report concise. Don't list every file checked, only issues found.
- For large repos, use Glob counts and spot-checks rather than reading every file
