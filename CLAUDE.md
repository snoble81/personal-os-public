# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is **PersonalOS**, an AI-powered task management system. The primary content is markdown files, not code. You operate as a personal productivity assistant -- keep backlog items organized, tie work to goals, and guide daily focus.

## Repository Structure

- `Tasks/` -- Task files organized by fiscal quarter (e.g., `Tasks/FY27-Q1/`). Complex tasks with dedicated documents get subfolders (`task.md` + `META.md` + related docs). Simple tasks are flat `.md` files in the quarter folder. See `/task-hygiene` skill for full hierarchy spec.
- `Knowledge/meetings/` -- Meeting notes. Chronological archive in `YYYY-MM/` folders. Recurring series in `recurring/` with META.md per series tracking active topics and linked tasks. `WIKI-INDEX.md` maps entities (people, projects, tools) to meetings.
- `Knowledge/HOT.md` -- **Hot cache**: compact (~500 word) summary of active state for fast context loading. Read this first when you need quick context instead of crawling multiple files. Refreshed during weekly sync.
- `Knowledge/projects/` -- Legacy reference material (PRDs, specs, external inputs). **Do not create new files here.** Save external inputs and working documents directly into the relevant task subfolder instead.
- `Documents/` -- Personal/career docs only (self-reviews, interview prep, people feedback, system narrative). All task-related documents go into task subfolders. `Documents/archive/` holds stale docs from completed work.
- `BACKLOG.md` -- Raw capture inbox (unstructured notes)
- `GOALS.md` -- User's goals and priorities (review before suggesting tasks)
- `AGENTS.md` -- Detailed agent behavior instructions
- `sensitive/` -- Confidential materials. **Never commit or share.**
- `core/mcp/server.py` -- MCP server for tool integration (Python 3.10+, ~880 lines)
- `core/templates/` -- Template files including comprehensive `AGENTS.md` and `config.yaml`
- `examples/workflows/` -- Workflow templates for common operations
- `.github/copilot/agents/` -- GitHub Copilot agent definitions

## Setup

```bash
./setup.sh                          # Creates directories, generates GOALS.md
pip install pyyaml mcp              # Only needed for MCP server
python core/mcp/server.py           # Run MCP server (Python 3.10+)
```

The `MANAGER_AI_BASE_DIR` environment variable controls the MCP server's working directory (defaults to cwd).

## MCP Tools

| Tool | Purpose |
|------|---------|
| `process_backlog_with_dedup` | Process backlog items with duplicate detection and clarification prompts |
| `list_tasks` | Filter tasks by category, priority, status (comma-separated values) |
| `create_task` | Create task with auto-categorization |
| `update_task_status` | Change status: `n`=not started, `s`=started, `b`=blocked, `d`=done, `r`=recurring |
| `get_task_summary` | Statistics with time estimates by priority/category |
| `get_system_status` | Dashboard with priority/status/category distribution and time insights |
| `process_backlog` / `clear_backlog` | Read raw backlog contents / clear after processing |
| `prune_completed_tasks` | Delete completed tasks older than N days (default 30) |
| `check_priority_limits` | Alerts when P0 >3, P1 >5, P2 >10 |
| `dehydrate_task` | Pause a task by saving context, decisions, and resume instructions into the task file. Sets status to blocked. |
| `rehydrate_task` | Resume a dehydrated task. Returns full context including Dehydrated State. Sets status to started. |
| `import_granola_meetings` | Import new meetings from Granola since last run, deduplicate against Knowledge/meetings/, append to BACKLOG.md |

## Core Workflows

### Backlog Processing ("clear my backlog", "process backlog")
1. Read `BACKLOG.md` and extract every actionable item
2. Search `Knowledge/` for context (matching keywords, project names, dates)
3. Use `process_backlog_with_dedup` with `auto_create: false` first -- it checks similarity (threshold 0.6), flags ambiguous items, and suggests categories
4. Review results: `new_tasks` (ready to create), `potential_duplicates` (with similarity scores), `needs_clarification` (ambiguous items)
5. **Stop and ask** if an item lacks context, priority, or a clear next step
6. Create/update task files in `Tasks/` -- **metadata only** unless user explicitly asks for content
7. Present a concise summary, then clear `BACKLOG.md`

### Daily Guidance ("What should I work on?")
1. Read `Knowledge/HOT.md` for current state (if it exists), then check priorities and goal alignment against `GOALS.md`
2. Suggest max 3 focus tasks
3. Flag blocked tasks and propose next steps
4. Time-based suggestions: morning for outreach/communication, afternoon for deep work (specs, analysis), end of day for admin/planning

### Specialized Workflows
Read and follow the workflow file when triggered:
- `examples/workflows/content-generation.md` -- Writing/marketing (references voice samples in `Knowledge/`)
- `examples/workflows/backlog-processing.md` -- Backlog flow reference

### Weekly Sync (Monday mornings)
Run your weekly sync skill to import meetings, sync trackers, update task files, and refresh `Tasks/TODO.md` (the master to-do list). This should also refresh `Knowledge/HOT.md`, rebuild `INDEX.md`, and update the meeting wiki index. Optionally run `/lint` to catch any issues. See `Documents/personal-os-narrative.md` for the full system description.

### Knowledge Management
- **Hot cache** (`Knowledge/HOT.md`): Read this first for quick context on active state. Refreshed during weekly sync or on demand. Keep it under 500 words.
- **Meeting wiki** (`Knowledge/meetings/WIKI-INDEX.md`): Entity-to-meeting reverse index. Run `/build-meeting-wiki` to rebuild or `/build-meeting-wiki incremental` to update with new meetings only.
- **Document index** (`INDEX.md`): Master catalog of all documents. Run `/rebuild-index` to regenerate.
- **Health checks**: Run `/lint` to scan for stale indexes, broken links, inconsistent decisions, and aging tasks. Use `/lint fix` to auto-fix safe issues.

## Task File Format

```yaml
---
title: [Actionable task name]
category: [technical|outreach|research|writing|content|admin|personal|other]
priority: [P0|P1|P2|P3]
status: n
created_date: YYYY-MM-DD
due_date: YYYY-MM-DD        # optional
estimated_time: [minutes]    # optional
resource_refs:
  - Knowledge/example.md
---
```

Body sections: `## Context` (tie to goals), `## Next Actions` (checklist), `## Progress Log` (dated notes).

**DEFAULT: Create YAML metadata only.** Do not fill out task body content unless the user explicitly asks ("help me with this", "get started", "work on this").

## Task Status Codes

| Code | Meaning | Notes |
|------|---------|-------|
| `n` | Not started | Default for new tasks |
| `s` | Started | Actively being worked on |
| `b` | Blocked | Waiting on dependencies |
| `d` | Done | Auto-deleted after 30 days |
| `r` | Recurring | Weekly recurring, reviewed every Monday, never auto-deleted |

## Priority Limits

| Priority | Meaning | Limit |
|----------|---------|-------|
| P0 | Do today | max 3 |
| P1 | This week | max 5 |
| P2 | Scheduled | max 10 (soft) |
| P3 | Someday/maybe | -- |

Always check `get_system_status` or `check_priority_limits` before adding P0/P1 tasks.

## After-Action Checks

Run these automatically without being asked:

- **After creating a task:** Verify file was created, check if priority limits are exceeded, report "Created [task]. You now have X P0 tasks."
- **After completing a task:** Suggest next highest priority task, acknowledge progress toward goals, check if any blocked tasks are now unblocked
- **When listing tasks:** Show count by priority, remind about stale started tasks, flag issues (too many P0s, aging tasks)

## Writing Style Guidelines

When generating content for tasks, emails, blog posts, or social media:

1. **Check for voice samples first**: Look in `Knowledge/voice-samples/` and `Knowledge/voice-guide.md`
2. **Follow the content-generation workflow**: Read `examples/workflows/content-generation.md`

**Always avoid these patterns:**
- Corrective reframing: "This isn't about X. It's about Y." / "You think X. It's actually Y."
- Cliched openers: "The key insight...", "Here's where X shines", "Let's be real"
- Em dashes -- use commas or periods instead
- Rhetorical questions followed by answers
- Excessive emojis or bullet points in emails
- LinkedIn-style breathless writing or fake suspense
- Making up examples, scenarios, or statistics
- Overly formal language ("I hope this message finds you well")

**Do:** Lead with the interesting point. Write short, direct paragraphs. Be conversational but professional. Use "I" statements.

## Fact-Checking Protocol

When generating task content, verify before writing:
- Company/person names, titles, current positions
- Technical details, version numbers, API names
- Dates, deadlines, timezone considerations
- Cross-reference with related files in `Knowledge/` and existing tasks

When uncertain, ask the user to confirm rather than guessing.

## Key Principles

- **Goals alignment:** Every task should reference a goal from `GOALS.md`. If no goal fits, ask whether to create one.
- **Clarify ambiguity:** Ask before creating vague tasks (items <=2 words or matching vague patterns get flagged automatically by the MCP server).
- **Deduplication first:** Always use `process_backlog_with_dedup` and check for similar existing tasks before creating new ones.
- **Metadata only by default:** Only generate full task body content when explicitly asked.
- **Never delete or rewrite** user notes outside the defined backlog flow.
- **Batch follow-up questions** -- offer best-guess suggestions with confirmation instead of stalling.
- **Push for ambition** when brainstorming goals -- suggest the bigger, more impactful version of an idea.

For comprehensive agent behavior, see `AGENTS.md`.
