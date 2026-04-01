#!/usr/bin/env python3
"""
MCP Server for Manager AI - TODO System Management
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import Counter

import yaml
import re
from difflib import SequenceMatcher
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - use environment variable or current directory
BASE_DIR = Path(os.environ.get('MANAGER_AI_BASE_DIR', Path.cwd()))
TASKS_DIR = BASE_DIR / 'Tasks'

# Ensure directories exist
TASKS_DIR.mkdir(exist_ok=True, parents=True)

# Duplicate detection configuration
DEDUP_CONFIG = {
    "similarity_threshold": 0.6,  # How similar before flagging as potential duplicate
    "check_categories": True,     # Same category increases similarity score
}

# Granola integration configuration
GRANOLA_CREDS = Path.home() / "Library" / "Application Support" / "Granola" / "supabase.json"
GRANOLA_LAST_IMPORT = BASE_DIR / '.granola_last_import'
MEETINGS_DIR = BASE_DIR / 'Knowledge' / 'meetings'
GRANOLA_API_BASE = "https://api.granola.ai"


def get_granola_token() -> str:
    """Read the WorkOS access token from Granola's local credential file."""
    with open(GRANOLA_CREDS) as f:
        data = json.load(f)
    return json.loads(data['workos_tokens'])['access_token']


def granola_api_call(endpoint: str, payload: dict = None) -> Any:
    """Call a Granola API endpoint using curl --compressed.
    Returns parsed JSON response.
    """
    url = f"{GRANOLA_API_BASE}{endpoint}"
    token = get_granola_token()
    cmd = [
        "curl", "-s", "--compressed", "-X", "POST", url,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload or {}),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def prosemirror_to_text(node: dict) -> str:
    """Recursively extract plain text from a ProseMirror JSON document."""
    if not isinstance(node, dict):
        return ""
    parts = []
    if node.get("type") == "text":
        parts.append(node.get("text", ""))
    if node.get("type") == "heading":
        parts.append("\n### ")
    if node.get("type") == "bulletList":
        pass  # children handle it
    if node.get("type") == "listItem":
        parts.append("\n- ")
    for child in node.get("content", []):
        parts.append(prosemirror_to_text(child))
    if node.get("type") == "paragraph":
        parts.append("\n")
    return "".join(parts)


def get_existing_meeting_keys() -> set:
    """Scan Knowledge/meetings/ and BACKLOG.md for existing meeting date+title pairs.
    Returns a set of 'YYYY-MM-DD|lowered_title' keys.
    """
    keys = set()

    # Scan meeting files
    if MEETINGS_DIR.exists():
        for month_dir in MEETINGS_DIR.iterdir():
            if month_dir.is_dir():
                for f in month_dir.glob("*.md"):
                    # Filename pattern: YYYY-MM-DD-slug.md
                    name = f.stem
                    parts = name.split("-", 3)
                    if len(parts) >= 4:
                        date_str = "-".join(parts[:3])
                        title_slug = parts[3].replace("-", " ").lower()
                        keys.add(f"{date_str}|{title_slug}")
                    # Also check file content for Meeting Title
                    try:
                        content = f.read_text()
                        for line in content.split("\n")[:5]:
                            if line.startswith("# "):
                                keys.add(f"{date_str if len(parts) >= 4 else ''}|{line[2:].strip().lower()}")
                    except Exception:
                        pass

    # Scan BACKLOG.md for already-appended meetings
    backlog_file = BASE_DIR / "BACKLOG.md"
    if backlog_file.exists():
        try:
            content = backlog_file.read_text()
            for line in content.split("\n"):
                if line.startswith("Meeting Title: "):
                    title = line[len("Meeting Title: "):].strip().lower()
                    # Look for the Date line right after
                    keys.add(f"|{title}")
        except Exception:
            pass

    return keys


def meeting_matches_existing(date_str: str, title: str, existing_keys: set) -> bool:
    """Check if a meeting already exists by date+title or title alone."""
    title_lower = title.strip().lower()
    # Exact date+title match
    if f"{date_str}|{title_lower}" in existing_keys:
        return True
    # Title-only match (for BACKLOG entries without dates in key)
    if f"|{title_lower}" in existing_keys:
        return True
    # Fuzzy: check if title slug is substring of any existing key
    title_slug = re.sub(r'[^a-z0-9 ]', '', title_lower).strip()
    for key in existing_keys:
        existing_slug = key.split("|", 1)[1] if "|" in key else key
        if title_slug and title_slug in existing_slug:
            return True
        if existing_slug and existing_slug in title_slug:
            return True
    return False


def parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content"""
    if not content.startswith('---'):
        return {}, content
    
    try:
        parts = content.split('---', 2)[1:]
        if len(parts) >= 1:
            metadata = yaml.safe_load(parts[0])
            body = parts[1] if len(parts) > 1 else ''
            return metadata or {}, body
    except Exception as e:
        logger.error(f"Error parsing YAML: {e}")
        return {}, content

def get_all_tasks() -> List[Dict[str, Any]]:
    """Get all tasks from the Tasks directory"""
    tasks = []
    if not TASKS_DIR.exists():
        return tasks
    
    for task_file in TASKS_DIR.glob('*.md'):
        try:
            with open(task_file, 'r') as f:
                content = f.read()
                metadata, body = parse_yaml_frontmatter(content)
                if metadata:
                    metadata['filename'] = task_file.name
                    metadata['body_content'] = body[:500] if body else ''
                    tasks.append(metadata)
        except Exception as e:
            logger.error(f"Error reading {task_file}: {e}")
    
    return tasks

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two strings (0-1 score)"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text"""
    # Remove common words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'from', 'up', 'out'}
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in stop_words and len(w) > 2}

def find_similar_tasks(item: str, existing_tasks: List[Dict[str, Any]], config: dict = DEDUP_CONFIG) -> List[Dict[str, Any]]:
    """Find tasks similar to the given item"""
    similar = []
    item_keywords = extract_keywords(item)
    
    for task in existing_tasks:
        # Skip completed tasks
        if task.get('status') == 'd':
            continue
            
        # Calculate title similarity
        title = task.get('title', '')
        title_similarity = calculate_similarity(item, title)
        
        # Calculate keyword overlap
        task_keywords = extract_keywords(title)
        if item_keywords and task_keywords:
            keyword_overlap = len(item_keywords & task_keywords) / len(item_keywords | task_keywords)
        else:
            keyword_overlap = 0
        
        # Combined score
        similarity_score = (title_similarity * 0.7) + (keyword_overlap * 0.3)
        
        # Check if it's a potential duplicate
        if similarity_score >= config['similarity_threshold']:
            similar.append({
                'title': title,
                'filename': task.get('filename', ''),
                'category': task.get('category', ''),
                'status': task.get('status', ''),
                'similarity_score': round(similarity_score, 2)
            })
    
    # Sort by similarity score
    similar.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar[:3]  # Return top 3 matches

def is_ambiguous(item: str) -> bool:
    """Check if an item is too vague or ambiguous"""
    vague_patterns = [
        r'^(fix|update|improve|check|review|look at|work on)\s+(the|a|an)?\s*\w+$',  # "fix bug", "update docs"
        r'^\w+\s+(stuff|thing|issue|problem)$',  # "database stuff", "API thing"
        r'^(follow up|reach out|contact|email)$',  # Missing who/what
        r'^(investigate|research|explore)\s*\w{0,20}$',  # Too broad
    ]
    
    item_lower = item.lower().strip()
    
    # Check if too short
    if len(item_lower.split()) <= 2:
        return True
    
    # Check vague patterns
    for pattern in vague_patterns:
        if re.match(pattern, item_lower):
            return True
    
    return False

def generate_clarification_questions(item: str) -> List[str]:
    """Generate clarification questions for ambiguous items"""
    questions = []
    item_lower = item.lower()
    
    # Technical ambiguity
    if any(word in item_lower for word in ['fix', 'bug', 'error', 'issue']):
        questions.append("Which specific bug or error? Can you provide more details or error messages?")
        questions.append("What component or feature is affected?")
    
    # Scope ambiguity
    if any(word in item_lower for word in ['update', 'improve', 'refactor']):
        questions.append("What specific aspects need updating/improvement?")
        questions.append("What's the success criteria for this task?")
    
    # Missing target
    if any(word in item_lower for word in ['email', 'contact', 'reach out', 'follow up']):
        questions.append("Who should be contacted?")
        questions.append("What's the purpose or goal of this outreach?")
    
    # Missing context
    if any(word in item_lower for word in ['research', 'investigate', 'explore']):
        questions.append("What specific questions need to be answered?")
        questions.append("What decisions will this research inform?")
    
    # Generic catch-all
    if not questions:
        questions.append("Can you provide more specific details about what needs to be done?")
        questions.append("What's the expected outcome or deliverable?")
    
    return questions

def guess_category(item: str) -> str:
    """Guess the category based on item text"""
    item_lower = item.lower()
    
    # Check for category indicators
    if any(word in item_lower for word in ['email', 'contact', 'reach out', 'follow up', 'meeting', 'call']):
        return 'outreach'
    elif any(word in item_lower for word in ['code', 'api', 'database', 'deploy', 'fix', 'bug', 'implement']):
        return 'technical'
    elif any(word in item_lower for word in ['research', 'study', 'learn', 'understand', 'investigate']):
        return 'research'
    elif any(word in item_lower for word in ['write', 'draft', 'document', 'blog', 'article', 'proposal']):
        return 'writing'
    elif any(word in item_lower for word in ['expense', 'invoice', 'schedule', 'calendar', 'organize']):
        return 'admin'
    elif any(word in item_lower for word in ['tweet', 'post', 'linkedin', 'social', 'twitter', 'marketing', 'blog']):
        return 'marketing'
    else:
        return 'other'

def generate_task_content(item: str, category: str) -> str:
    """Generate rich task content based on item and category"""
    
    # Base structure that all tasks get
    base_content = f"""## Overview
{get_task_overview(item, category)}

## Next Actions
{get_next_actions(item, category)}

## Notes & Details
- Task created from backlog processing
- Category: {category}
"""
    
    # Add category-specific sections
    if category == 'outreach':
        base_content += """
## Draft Message
[Draft outreach message here based on context]

## Contact Details
- LinkedIn profile: [to be added]
- Email: [to be added]
"""
    elif category == 'writing':
        base_content += """
## Key Points
- [Main argument or thesis]
- [Supporting points]
- [Call to action]

## Target Audience
[Define who this is for]

## Resources
- [Related documents or references]
"""
    elif category == 'technical':
        base_content += """
## Technical Requirements
- [Specific technical details]
- [Dependencies or prerequisites]
- [Expected outcome]

## Implementation Notes
- [Technical approach]
- [Testing considerations]
"""
    elif category == 'research':
        base_content += """
## Research Questions
- [What are we trying to learn?]
- [Key hypotheses to test]

## Sources to Explore
- [Relevant resources]
- [People to consult]
"""
    elif category == 'marketing':
        base_content += """
## Content Strategy
- Platform: [Twitter/LinkedIn/Blog/etc]
- Key message: [Core point]
- Engagement goal: [What response do we want?]

## Draft Post
[Initial draft of marketing content]
"""
        
    return base_content

def get_task_overview(item: str, category: str) -> str:
    """Generate a contextual overview based on the task"""
    item_lower = item.lower()
    
    # Provide smarter overviews based on keywords
    if 'proposal' in item_lower:
        return f"Create and submit a comprehensive proposal for {item}. Research requirements, draft content, and prepare supporting materials."
    elif 'review' in item_lower:
        return f"Conduct thorough review of {item}. Provide feedback, suggestions, and actionable improvements."
    elif 'follow up' in item_lower or 'reach out' in item_lower:
        return f"Establish or continue communication regarding {item}. Ensure clear next steps and maintain relationship momentum."
    elif 'post' in item_lower or 'write' in item_lower:
        return f"Create compelling content for {item}. Focus on value delivery and audience engagement."
    elif 'implement' in item_lower or 'build' in item_lower:
        return f"Design and implement solution for {item}. Ensure functionality, testing, and documentation."
    else:
        return f"Complete {item} with focus on quality and timeliness."

def get_next_actions(item: str, category: str) -> str:
    """Generate smart next actions based on task type"""
    actions = []
    
    # Universal first steps
    actions.append("- [ ] Review related context and existing work")
    
    # Category-specific actions
    if category == 'outreach':
        actions.extend([
            "- [ ] Research contact's recent activity/interests",
            "- [ ] Draft personalized message",
            "- [ ] Schedule follow-up reminder"
        ])
    elif category == 'writing':
        actions.extend([
            "- [ ] Create outline with key points",
            "- [ ] Write first draft",
            "- [ ] Review and edit for clarity",
            "- [ ] Prepare for publication/submission"
        ])
    elif category == 'technical':
        actions.extend([
            "- [ ] Define technical requirements",
            "- [ ] Set up development environment",
            "- [ ] Implement core functionality",
            "- [ ] Test and validate solution"
        ])
    elif category == 'research':
        actions.extend([
            "- [ ] Define research questions",
            "- [ ] Gather relevant sources",
            "- [ ] Analyze and synthesize findings",
            "- [ ] Document insights and recommendations"
        ])
    elif category == 'marketing':
        actions.extend([
            "- [ ] Research trending topics/hashtags",
            "- [ ] Draft engaging content",
            "- [ ] Add relevant visuals/links",
            "- [ ] Schedule optimal posting time"
        ])
    else:
        actions.extend([
            "- [ ] Define specific requirements",
            "- [ ] Create action plan",
            "- [ ] Execute plan",
            "- [ ] Verify completion"
        ])
    
    return '\n'.join(actions)

def update_file_frontmatter(filepath: Path, updates: dict) -> bool:
    """Update YAML frontmatter in a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        metadata, body = parse_yaml_frontmatter(content)
        metadata.update(updates)
        
        # Reconstruct file
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{yaml_str}---\n{body}"
        
        with open(filepath, 'w') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        logger.error(f"Error updating {filepath}: {e}")
        return False

DASHBOARD_FILE = TASKS_DIR / 'DASHBOARD.md'

PRIORITY_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
STATUS_ORDER = {'s': 0, 'n': 1, 'b': 2, 'r': 3}

def parse_dashboard_notes() -> Dict[str, str]:
    """Parse existing DASHBOARD.md and return {task_title: note} for non-empty notes."""
    notes = {}
    if not DASHBOARD_FILE.exists():
        return notes
    with open(DASHBOARD_FILE, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line.startswith('|') or line.startswith('| Priority') or line.startswith('|---'):
            continue
        cells = [c.strip() for c in line.split('|')]
        # cells: ['', priority, status, task, category, notes, '']
        if len(cells) >= 7:
            title = cells[3]
            note = cells[5]
            if note:
                notes[title] = note
    return notes

def generate_dashboard_content(tasks: List[Dict[str, Any]], existing_notes: Dict[str, str] = None) -> str:
    """Generate markdown table content for the dashboard."""
    if existing_notes is None:
        existing_notes = {}

    # Sort: priority first, then status (started before not-started)
    tasks.sort(key=lambda t: (
        PRIORITY_ORDER.get(t.get('priority', 'P2'), 9),
        STATUS_ORDER.get(t.get('status', 'n'), 9),
        t.get('title', '')
    ))

    today = datetime.now().strftime('%Y-%m-%d')
    lines = [
        f"# Daily Dashboard",
        f"*Generated: {today}*",
        "",
        "| Priority | Status | Task | Category | Notes |",
        "|----------|--------|------|----------|-------|",
    ]

    status_labels = {'n': 'not started', 's': 'started', 'b': 'blocked', 'r': 'recurring'}

    for task in tasks:
        title = task.get('title', '')
        note = existing_notes.get(title, '')
        priority = task.get('priority', 'P2')
        status = status_labels.get(task.get('status', 'n'), task.get('status', 'n'))
        category = task.get('category', 'other')
        lines.append(f"| {priority} | {status} | {title} | {category} | {note} |")

    lines.append("")
    return '\n'.join(lines)

def append_progress_log(filepath: Path, note: str, date_str: str) -> bool:
    """Append a timestamped note to the Progress Log section of a task file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        entry = f"- {date_str}: {note}"

        if '## Progress Log' in content:
            # Append after the Progress Log heading
            parts = content.split('## Progress Log', 1)
            after = parts[1]
            # Find end of existing entries (next ## heading or end of file)
            next_heading = re.search(r'\n## ', after)
            if next_heading:
                insert_pos = next_heading.start()
                new_after = after[:insert_pos].rstrip() + '\n' + entry + '\n' + after[insert_pos:]
            else:
                new_after = after.rstrip() + '\n' + entry + '\n'
            content = parts[0] + '## Progress Log' + new_after
        else:
            # Add Progress Log section at the end
            content = content.rstrip() + '\n\n## Progress Log\n' + entry + '\n'

        with open(filepath, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error appending progress log to {filepath}: {e}")
        return False

# Create the MCP server
app = Server("manager-ai-mcp")

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools"""
    return [
        types.Tool(
            name="list_tasks",
            description="List tasks with optional filters (category, priority, status)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category (comma-separated)"},
                    "priority": {"type": "string", "description": "Filter by priority (comma-separated, e.g., P0,P1)"},
                    "status": {"type": "string", "description": "Filter by status (n,s,b,d)"},
                    "include_done": {"type": "boolean", "description": "Include completed tasks", "default": False}
                }
            }
        ),
        types.Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "category": {"type": "string", "description": "Task category", "default": "other"},
                    "priority": {"type": "string", "description": "Priority (P0-P3)", "default": "P2"},
                    "estimated_time": {"type": "integer", "description": "Estimated time in minutes", "default": 30},
                    "content": {"type": "string", "description": "Task content/description"}
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="update_task_status",
            description="Update task status (n=not started, s=started, b=blocked, d=done)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_file": {"type": "string", "description": "Task filename"},
                    "status": {"type": "string", "description": "New status (n,s,b,d)"}
                },
                "required": ["task_file", "status"]
            }
        ),
        types.Tool(
            name="get_task_summary",
            description="Get summary statistics for all tasks",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="check_priority_limits",
            description="Check if priority limits are exceeded",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_system_status",
            description="Get comprehensive system status",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="process_backlog",
            description="Read and return backlog contents",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="clear_backlog",
            description="Clear the backlog after processing",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="prune_completed_tasks",
            description="Delete completed tasks older than specified days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days old", "default": 30}
                }
            }
        ),
        types.Tool(
            name="process_backlog_with_dedup",
            description="Process backlog items with duplicate detection and clarification",
            inputSchema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of backlog items to process"
                    },
                    "auto_create": {
                        "type": "boolean",
                        "description": "Automatically create non-duplicate tasks",
                        "default": False
                    }
                },
                "required": ["items"]
            }
        ),
        types.Tool(
            name="generate_dashboard",
            description="Generate Tasks/DASHBOARD.md with a table of all active tasks and a Notes column for daily updates",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="process_dashboard_notes",
            description="Process notes from DASHBOARD.md into timestamped Progress Log entries on each task file, then clear the Notes column",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="dehydrate_task",
            description="Pause a task by saving current context, decisions, and next steps into a Dehydrated State section. Sets status to blocked. Use when switching away from an in-progress task to preserve resumption context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_file": {"type": "string", "description": "Task filename"},
                    "where_left_off": {"type": "string", "description": "What was being worked on when paused"},
                    "decisions_made": {"type": "string", "description": "Decisions or options explored so far"},
                    "to_resume": {"type": "string", "description": "Instructions for resuming this task"}
                },
                "required": ["task_file", "where_left_off", "to_resume"]
            }
        ),
        types.Tool(
            name="rehydrate_task",
            description="Resume a dehydrated task. Returns the full task file including Dehydrated State context so work can continue where it left off. Sets status to started.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_file": {"type": "string", "description": "Task filename"}
                },
                "required": ["task_file"]
            }
        ),
        types.Tool(
            name="import_granola_meetings",
            description="Import new meetings from Granola. Fetches meetings since last import, deduplicates against existing Knowledge/meetings/ files, and appends formatted entries to BACKLOG.md for processing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_back": {
                        "type": "integer",
                        "description": "How many days back to look on first run (default 7). Ignored on subsequent runs which use the stored timestamp.",
                        "default": 7
                    }
                }
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    
    if name == "list_tasks":
        tasks = get_all_tasks()
        
        # Apply filters
        if arguments:
            if not arguments.get('include_done', False):
                tasks = [t for t in tasks if t.get('status') != 'd']
            
            if arguments.get('category'):
                categories = [c.strip() for c in arguments['category'].split(',')]
                tasks = [t for t in tasks if t.get('category') in categories]
            
            if arguments.get('priority'):
                priorities = [p.strip() for p in arguments['priority'].split(',')]
                tasks = [t for t in tasks if t.get('priority') in priorities]
            
            if arguments.get('status'):
                statuses = [s.strip() for s in arguments['status'].split(',')]
                tasks = [t for t in tasks if t.get('status') in statuses]
        else:
            # Default: exclude done tasks
            tasks = [t for t in tasks if t.get('status') != 'd']
        
        result = {
            "tasks": tasks,
            "count": len(tasks),
            "filters_applied": arguments or {}
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_task":
        title = arguments['title']
        category = arguments.get('category', 'other')
        priority = arguments.get('priority', 'P2')
        estimated_time = arguments.get('estimated_time', 30)
        content = arguments.get('content', '')
        
        # Create filename
        filename = title.replace('/', '_').replace('\\', '_') + '.md'
        filepath = TASKS_DIR / filename
        
        # Create task metadata
        metadata = {
            'title': title,
            'category': category,
            'priority': priority,
            'status': 'n',
            'estimated_time': estimated_time
        }
        
        # Create file content
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        file_content = f"---\n{yaml_str}---\n\n# {title}\n\n{content}"
        
        try:
            with open(filepath, 'w') as f:
                f.write(file_content)
            
            result = {
                "success": True,
                "filename": filename,
                "message": f"Task '{title}' created successfully"
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "update_task_status":
        task_file = arguments['task_file']
        status = arguments['status']
        
        if not task_file.endswith('.md'):
            task_file += '.md'
        
        filepath = TASKS_DIR / task_file
        if not filepath.exists():
            result = {
                "success": False,
                "error": f"Task file not found: {task_file}"
            }
        else:
            success = update_file_frontmatter(filepath, {'status': status})
            status_names = {'n': 'not started', 's': 'started', 'b': 'blocked', 'd': 'done'}
            result = {
                "success": success,
                "task_file": task_file,
                "new_status": status_names.get(status, status)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_task_summary":
        tasks = get_all_tasks()
        active_tasks = [t for t in tasks if t.get('status') != 'd']
        
        by_priority = Counter(t.get('priority', 'P2') for t in active_tasks)
        by_category = Counter(t.get('category', 'other') for t in active_tasks)
        by_status = Counter(t.get('status', 'n') for t in tasks)
        
        # Calculate time estimates
        time_by_priority = {}
        for priority in ['P0', 'P1', 'P2', 'P3']:
            priority_tasks = [t for t in active_tasks if t.get('priority') == priority]
            total_time = sum(t.get('estimated_time', 30) for t in priority_tasks)
            time_by_priority[priority] = {
                'total_minutes': total_time,
                'total_hours': round(total_time / 60, 1)
            }
        
        result = {
            "total_tasks": len(tasks),
            "active_tasks": len(active_tasks),
            "by_priority": dict(by_priority),
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "time_by_priority": time_by_priority
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "check_priority_limits":
        tasks = [t for t in get_all_tasks() if t.get('status') != 'd']
        by_priority = Counter(t.get('priority', 'P2') for t in tasks)
        
        thresholds = {'P0': 3, 'P1': 5, 'P2': 10}
        alerts = []
        
        for priority, threshold in thresholds.items():
            count = by_priority.get(priority, 0)
            if count > threshold:
                alerts.append(f"{priority} has {count} tasks (limit: {threshold})")
        
        result = {
            "priority_counts": dict(by_priority),
            "alerts": alerts,
            "balanced": len(alerts) == 0
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_system_status":
        all_tasks = get_all_tasks()
        active_tasks = [t for t in all_tasks if t.get('status') != 'd']

        priority_counts = Counter(task['priority'] for task in active_tasks)
        status_counts = Counter(task['status'] for task in active_tasks)
        category_counts = Counter(task['category'] for task in active_tasks)

        # Check backlog
        backlog_items = 0
        backlog_file = BASE_DIR / 'BACKLOG.md'
        if backlog_file.exists():
            with open(backlog_file, 'r') as f:
                content = f.read().strip()
                if content and content != 'all done!':
                    backlog_items = len([l for l in content.split('\n') if l.strip().startswith('-')])

        # Time insights
        now = datetime.now()
        hour = now.hour
        day_name = now.strftime('%A')

        time_insights = []
        if 9 <= hour < 12:
            time_insights.append("Morning - ideal for outreach tasks")
        elif 14 <= hour < 17:
            time_insights.append("Afternoon - good for deep work")
        elif hour >= 17:
            time_insights.append("End of day - quick admin tasks")

        result = {
            "total_active_tasks": len(active_tasks),
            "priority_distribution": dict(priority_counts),
            "status_distribution": dict(status_counts),
            "category_distribution": dict(category_counts),
            "backlog_items": backlog_items,
            "time_insights": time_insights,
            "timestamp": now.isoformat()
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "process_backlog":
        backlog_file = BASE_DIR / 'BACKLOG.md'
        
        if not backlog_file.exists():
            result = {
                "success": False,
                "error": "BACKLOG.md not found"
            }
        else:
            with open(backlog_file, 'r') as f:
                content = f.read().strip()
            
            if not content or content == 'all done!':
                result = {
                    "success": True,
                    "content": None,
                    "message": "Backlog is already clear"
                }
            else:
                # Parse items
                lines = content.split('\n')
                items = []
                current_item = None
                
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('- '):
                        if current_item:
                            items.append(current_item)
                        current_item = {
                            'text': stripped[2:],
                            'subitems': []
                        }
                    elif stripped.startswith('  - ') and current_item:
                        current_item['subitems'].append(stripped[4:])
                
                if current_item:
                    items.append(current_item)
                
                result = {
                    "success": True,
                    "content": content,
                    "parsed_items": items,
                    "count": len(items)
                }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "clear_backlog":
        backlog_file = BASE_DIR / 'BACKLOG.md'
        
        try:
            with open(backlog_file, 'w') as f:
                f.write("all done!")
            
            result = {
                "success": True,
                "message": "Backlog cleared successfully"
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e)
            }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "prune_completed_tasks":
        days = arguments.get('days', 30) if arguments else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted = []
        
        for task_file in TASKS_DIR.glob('*.md'):
            try:
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime)
                if mtime < cutoff_date:
                    with open(task_file, 'r') as f:
                        content = f.read()
                        metadata, _ = parse_yaml_frontmatter(content)
                        if metadata.get('status') == 'd':
                            task_file.unlink()
                            deleted.append(task_file.name)
            except Exception as e:
                logger.error(f"Error processing {task_file}: {e}")
        
        result = {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_files": deleted,
            "message": f"Deleted {len(deleted)} tasks older than {days} days"
        }
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "dehydrate_task":
        task_file = arguments['task_file']
        if not task_file.endswith('.md'):
            task_file += '.md'
        filepath = TASKS_DIR / task_file

        if not filepath.exists():
            return [types.TextContent(type="text", text=json.dumps({
                "success": False, "error": f"Task file not found: {task_file}"
            }, indent=2))]

        where_left_off = arguments['where_left_off']
        decisions_made = arguments.get('decisions_made', '')
        to_resume = arguments['to_resume']
        today = datetime.now().strftime('%Y-%m-%d')

        with open(filepath, 'r') as f:
            content = f.read()

        # Build dehydrated state section
        dehydrated = f"\n\n## Dehydrated State\n*Paused: {today}*\n\n"
        dehydrated += f"**Where I left off:** {where_left_off}\n\n"
        if decisions_made:
            dehydrated += f"**Decisions/options explored:** {decisions_made}\n\n"
        dehydrated += f"**To resume:** {to_resume}\n"

        # Remove existing dehydrated state if present
        if '## Dehydrated State' in content:
            content = re.sub(r'\n*## Dehydrated State.*?(?=\n## |\Z)', '', content, flags=re.DOTALL)

        content = content.rstrip() + dehydrated

        # Update status to blocked
        metadata, body = parse_yaml_frontmatter(content)
        metadata['status'] = 'b'
        yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        content = f"---\n{yaml_str}---{body}"

        # Re-append dehydrated state if it got lost in the rebuild
        if '## Dehydrated State' not in content:
            content = content.rstrip() + dehydrated

        with open(filepath, 'w') as f:
            f.write(content)

        result = {
            "success": True,
            "task_file": task_file,
            "message": f"Task dehydrated and set to blocked. Resume with rehydrate_task."
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "rehydrate_task":
        task_file = arguments['task_file']
        if not task_file.endswith('.md'):
            task_file += '.md'
        filepath = TASKS_DIR / task_file

        if not filepath.exists():
            return [types.TextContent(type="text", text=json.dumps({
                "success": False, "error": f"Task file not found: {task_file}"
            }, indent=2))]

        with open(filepath, 'r') as f:
            content = f.read()

        # Update status to started
        update_file_frontmatter(filepath, {'status': 's'})

        # Re-read after update
        with open(filepath, 'r') as f:
            content = f.read()

        has_state = '## Dehydrated State' in content
        result = {
            "success": True,
            "task_file": task_file,
            "has_dehydrated_state": has_state,
            "content": content,
            "message": "Task rehydrated and set to started. Read the Dehydrated State section for context." if has_state else "Task set to started. No dehydrated state found."
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "process_backlog_with_dedup":
        items = arguments.get('items', [])
        auto_create = arguments.get('auto_create', False)
        
        if not items:
            return [types.TextContent(type="text", text=json.dumps({
                "error": "No items provided to process"
            }, indent=2))]

        existing_tasks = get_all_tasks()

        result = {
            "new_tasks": [],
            "potential_duplicates": [],
            "needs_clarification": [],
            "auto_created": [],
            "summary": {}
        }
        
        for item in items:
            # Check for duplicates
            similar_tasks = find_similar_tasks(item, existing_tasks)
            
            if similar_tasks:
                result["potential_duplicates"].append({
                    "item": item,
                    "similar_tasks": similar_tasks,
                    "recommended_action": "merge" if similar_tasks[0]['similarity_score'] > 0.8 else "review"
                })
            elif is_ambiguous(item):
                result["needs_clarification"].append({
                    "item": item,
                    "questions": generate_clarification_questions(item),
                    "suggestions": [
                        "Add more specific details",
                        "Include success criteria",
                        "Specify scope or boundaries"
                    ]
                })
            else:
                # This is a new, clear task
                result["new_tasks"].append({
                    "item": item,
                    "suggested_category": guess_category(item),
                    "suggested_priority": "P2",  # Default priority
                    "ready_to_create": True
                })
                
                # Auto-create if requested
                if auto_create:
                    # Create the task file
                    safe_filename = re.sub(r'[^\w\s-]', '', item).strip()
                    safe_filename = re.sub(r'[-\s]+', ' ', safe_filename)
                    task_file = TASKS_DIR / f"{safe_filename}.md"
                    
                    metadata = {
                        "title": item,
                        "category": guess_category(item),
                        "priority": "P2",
                        "status": "n",
                        "estimated_time": 60
                    }
                    
                    yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
                    
                    # Generate richer task content based on category
                    task_content = generate_task_content(item, metadata['category'])
                    content = f"---\n{yaml_str}---\n\n# {item}\n\n{task_content}"
                    
                    with open(task_file, 'w') as f:
                        f.write(content)
                    
                    result["auto_created"].append(safe_filename + ".md")
        
        # Add summary
        result["summary"] = {
            "total_items": len(items),
            "new_tasks": len(result["new_tasks"]),
            "duplicates_found": len(result["potential_duplicates"]),
            "needs_clarification": len(result["needs_clarification"]),
            "auto_created": len(result["auto_created"]),
            "recommendations": []
        }
        
        # Add recommendations
        if result["potential_duplicates"]:
            result["summary"]["recommendations"].append(
                f"Review {len(result['potential_duplicates'])} potential duplicates before creating tasks"
            )
        
        if result["needs_clarification"]:
            result["summary"]["recommendations"].append(
                f"Clarify {len(result['needs_clarification'])} ambiguous items for better task definition"
            )
        
        if result["new_tasks"] and not auto_create:
            result["summary"]["recommendations"].append(
                f"Ready to create {len(result['new_tasks'])} new tasks - use auto_create=true or create manually"
            )
        
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "generate_dashboard":
        tasks = [t for t in get_all_tasks() if t.get('status') not in ('d',)]
        # Preserve any existing notes the user has written
        existing_notes = parse_dashboard_notes()
        content = generate_dashboard_content(tasks, existing_notes)

        with open(DASHBOARD_FILE, 'w') as f:
            f.write(content)

        preserved = sum(1 for n in existing_notes.values() if n)
        result = {
            "success": True,
            "task_count": len(tasks),
            "notes_preserved": preserved,
            "message": f"Dashboard generated with {len(tasks)} active tasks"
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "process_dashboard_notes":
        if not DASHBOARD_FILE.exists():
            return [types.TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "DASHBOARD.md not found. Run generate_dashboard first."
            }, indent=2))]

        notes = parse_dashboard_notes()
        if not notes:
            return [types.TextContent(type="text", text=json.dumps({
                "success": True,
                "processed": [],
                "message": "No notes to process"
            }, indent=2))]

        today = datetime.now().strftime('%Y-%m-%d')
        all_tasks = get_all_tasks()
        processed = []
        skipped = []

        for title, note in notes.items():
            # Find matching task file
            matched_file = None
            for task in all_tasks:
                if task.get('title', '') == title:
                    matched_file = TASKS_DIR / task['filename']
                    break

            # Fallback: fuzzy match
            if not matched_file:
                best_score = 0
                for task in all_tasks:
                    score = calculate_similarity(title, task.get('title', ''))
                    if score > best_score and score >= 0.7:
                        best_score = score
                        matched_file = TASKS_DIR / task['filename']

            if matched_file and matched_file.exists():
                success = append_progress_log(matched_file, note, today)
                if success:
                    processed.append({"task": title, "note": note, "date": today, "file": matched_file.name})
                else:
                    skipped.append({"task": title, "note": note, "reason": "write error"})
            else:
                skipped.append({"task": title, "note": note, "reason": "task file not found"})

        # Regenerate dashboard with notes cleared
        active_tasks = [t for t in all_tasks if t.get('status') not in ('d',)]
        content = generate_dashboard_content(active_tasks)
        with open(DASHBOARD_FILE, 'w') as f:
            f.write(content)

        result = {
            "success": True,
            "processed": processed,
            "skipped": skipped,
            "summary": f"Processed {len(processed)} notes across {len(processed)} tasks"
        }
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "import_granola_meetings":
        try:
            days_back = (arguments or {}).get("days_back", 7)

            # Determine cutoff time
            if GRANOLA_LAST_IMPORT.exists():
                cutoff = datetime.fromisoformat(GRANOLA_LAST_IMPORT.read_text().strip())
            else:
                cutoff = datetime.utcnow() - timedelta(days=days_back)

            # Step 1: Get document index
            doc_set = granola_api_call("/v1/get-document-set")
            all_docs = doc_set.get("documents", {})

            # Filter to docs updated after cutoff
            recent_ids = []
            for doc_id, meta in all_docs.items():
                updated = meta.get("updated_at", "")
                if updated:
                    doc_time = datetime.fromisoformat(updated.replace("Z", "+00:00")).replace(tzinfo=None)
                    if doc_time > cutoff:
                        recent_ids.append(doc_id)

            if not recent_ids:
                # Update timestamp even if nothing new
                GRANOLA_LAST_IMPORT.write_text(datetime.utcnow().isoformat())
                return [types.TextContent(type="text", text=json.dumps({
                    "success": True,
                    "imported": [],
                    "skipped_duplicates": [],
                    "summary": f"No new meetings since {cutoff.isoformat()}"
                }, indent=2))]

            # Step 2: Batch fetch document details (200 at a time)
            all_doc_details = []
            for i in range(0, len(recent_ids), 200):
                batch = recent_ids[i:i+200]
                batch_result = granola_api_call("/v1/get-documents-batch", {"document_ids": batch})
                all_doc_details.extend(batch_result.get("docs", []))

            # Filter to valid meetings only
            meetings = [d for d in all_doc_details if d.get("type") == "meeting" and d.get("valid_meeting") and not d.get("deleted_at")]

            # Step 3: Deduplicate
            existing_keys = get_existing_meeting_keys()
            imported = []
            skipped_duplicates = []
            backlog_entries = []

            for meeting in meetings:
                title = (meeting.get("title") or "Untitled Meeting").strip()
                created = meeting.get("created_at", "")
                date_str = created[:10] if created else datetime.utcnow().strftime("%Y-%m-%d")

                if meeting_matches_existing(date_str, title, existing_keys):
                    skipped_duplicates.append({"title": title, "date": date_str})
                    continue

                doc_id = meeting["id"]

                # Fetch AI notes (panels)
                panels_text = ""
                try:
                    panels = granola_api_call("/v1/get-document-panels", {"document_id": doc_id})
                    if isinstance(panels, list) and panels:
                        content = panels[0].get("content", {})
                        panels_text = prosemirror_to_text(content).strip()
                except Exception as e:
                    logger.warning(f"Failed to fetch panels for {doc_id}: {e}")

                # Fetch transcript
                transcript_text = ""
                try:
                    transcript = granola_api_call("/v1/get-document-transcript", {"document_id": doc_id})
                    if isinstance(transcript, list):
                        segments = [seg.get("text", "") for seg in transcript if seg.get("is_final")]
                        transcript_text = " ".join(segments)[:5000]
                except Exception as e:
                    logger.warning(f"Failed to fetch transcript for {doc_id}: {e}")

                # Extract attendees
                people = meeting.get("people", {})
                attendee_names = []
                if isinstance(people, dict):
                    for att in people.get("attendees", []):
                        name = att.get("name", att.get("email", "Unknown"))
                        attendee_names.append(name)

                # Format backlog entry
                entry = f"""---
Meeting Title: {title}
Date: {date_str}
Participants: {', '.join(attendee_names) if attendee_names else 'Unknown'}

AI Summary:
{panels_text if panels_text else '(No AI summary available)'}

Transcript:
{transcript_text if transcript_text else '(No transcript available)'}
"""
                backlog_entries.append(entry)
                imported.append({"title": title, "date": date_str})

                # Add to existing keys to prevent intra-batch duplicates
                existing_keys.add(f"{date_str}|{title.strip().lower()}")

            # Step 4: Append to BACKLOG.md
            if backlog_entries:
                backlog_file = BASE_DIR / "BACKLOG.md"
                with open(backlog_file, "a") as f:
                    f.write("\n" + "\n".join(backlog_entries))

            # Step 5: Update timestamp
            GRANOLA_LAST_IMPORT.write_text(datetime.utcnow().isoformat())

            result = {
                "success": True,
                "imported": imported,
                "skipped_duplicates": skipped_duplicates,
                "summary": f"Imported {len(imported)} meetings, skipped {len(skipped_duplicates)} duplicates"
            }
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except FileNotFoundError:
            return [types.TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Granola credentials not found at {GRANOLA_CREDS}. Is Granola installed?"
            }, indent=2))]
        except Exception as e:
            logger.error(f"Granola import error: {e}")
            return [types.TextContent(type="text", text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2))]

    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Main entry point for the MCP server"""
    logger.info(f"Starting Manager AI MCP Server")
    logger.info(f"Working directory: {BASE_DIR}")
    logger.info(f"Tasks directory: {TASKS_DIR}")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="manager-ai-mcp",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())