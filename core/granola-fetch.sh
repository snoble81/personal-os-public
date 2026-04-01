#!/bin/bash
# Fetch recent Granola meetings and output as readable text
# Usage:
#   ./core/granola-fetch.sh              # Today's meetings
#   ./core/granola-fetch.sh 2026-03-04   # Specific date
#   ./core/granola-fetch.sh all          # Last 10 meetings
#   ./core/granola-fetch.sh ID           # Specific meeting by ID

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

ARG="${1:-}"
python3 - "$ARG" << 'PYEOF'
import json, os, subprocess, sys

DATE_FILTER = sys.argv[1] if len(sys.argv) > 1 else None

token_path = os.path.expanduser("~/Library/Application Support/Granola/supabase.json")
with open(token_path) as f:
    data = json.load(f)
token = json.loads(data["workos_tokens"])["access_token"]

API = "https://api.granola.ai"

def api_call(endpoint, payload=None):
    result = subprocess.run([
        "curl", "-s", "--compressed", "-X", "POST", API + endpoint,
        "-H", "Authorization: Bearer " + token,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload or {})
    ], capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)

def prosemirror_to_text(node, indent=0):
    if not isinstance(node, dict):
        return ""
    parts = []
    ntype = node.get("type", "")
    if ntype == "text":
        parts.append(node.get("text", ""))
    elif ntype == "heading":
        level = node.get("attrs", {}).get("level", 1)
        parts.append("\n" + "#" * level + " ")
    elif ntype == "listItem":
        parts.append("\n" + "  " * indent + "- ")
    elif ntype == "paragraph":
        parts.append("\n")
    for child in node.get("content", []):
        child_indent = indent + 1 if ntype == "bulletList" else indent
        parts.append(prosemirror_to_text(child, child_indent))
    return "".join(parts)

# Check if argument is a document ID (UUID format)
if DATE_FILTER and len(DATE_FILTER) == 36 and DATE_FILTER.count("-") == 4:
    doc_ids = [DATE_FILTER]
else:
    # Get all documents
    doc_set = api_call("/v1/get-document-set")
    docs = doc_set.get("documents", {})

    if DATE_FILTER == "all":
        # Sort by updated_at desc, take 10
        sorted_docs = sorted(docs.items(), key=lambda x: x[1].get("updated_at", ""), reverse=True)
        doc_ids = [did for did, _ in sorted_docs[:10]]
    elif DATE_FILTER:
        doc_ids = [did for did, meta in docs.items()
                   if meta.get("updated_at", "").startswith(DATE_FILTER)]
    else:
        # Today
        from datetime import date
        today = date.today().isoformat()
        doc_ids = [did for did, meta in docs.items()
                   if meta.get("updated_at", "").startswith(today)]

if not doc_ids:
    print("No meetings found.")
    sys.exit(0)

# Get batch details
batch = api_call("/v1/get-documents-batch", {"document_ids": doc_ids})

for doc in batch.get("docs", []):
    title = doc.get("title") or "untitled"
    created = (doc.get("created_at") or "")[:16]
    did = doc.get("id", "")

    # Get attendees
    people = doc.get("people", {})
    attendees = people.get("attendees", [])
    attendee_names = []
    for a in attendees:
        details = a.get("details", {})
        person = details.get("person", {})
        name_info = person.get("name", {})
        full_name = name_info.get("fullName") or a.get("email", "unknown")
        attendee_names.append(full_name)

    print(f"{'=' * 60}")
    print(f"Meeting: {title}")
    print(f"Date: {created}")
    print(f"ID: {did}")
    if attendee_names:
        print(f"Attendees: {', '.join(attendee_names)}")
    print(f"{'=' * 60}")

    # Get panels (AI summary)
    panels = api_call("/v1/get-document-panels", {"document_id": did})
    if isinstance(panels, list):
        for panel in panels:
            ptitle = panel.get("title", "")
            content = panel.get("content", "")
            if isinstance(content, dict):
                text = prosemirror_to_text(content).strip()
            else:
                text = str(content).strip()
            if text:
                print(f"\n--- {ptitle} ---")
                print(text)

    print()
PYEOF
