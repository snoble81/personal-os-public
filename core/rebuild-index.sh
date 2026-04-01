#!/bin/bash
# Rebuilds INDEX.md with all markdown files, sorted by creation date descending
# Run manually or hook into your workflow (e.g., git pre-commit, fswatch, etc.)

cd "$(dirname "$0")/.." || exit 1

OUTPUT="INDEX.md"

cat > "$OUTPUT" << 'HEADER'
# Index

All documents ordered by date created (newest first).

> **Auto-generated** by `core/rebuild-index.sh`. Do not edit manually.

---

HEADER

CURRENT_DATE=""

find Documents Knowledge Tasks sensitive GOALS.md TASKS.md BACKLOG.md Untitled.md -name "*.md" \
  -not -path "*/node_modules/*" \
  -not -name "README.md" \
  2>/dev/null | while read -r f; do
  birthtime=$(stat -f "%SB" -t "%Y-%m-%d" "$f" 2>/dev/null)
  modtime=$(stat -f "%Sm" -t "%Y-%m-%d" "$f" 2>/dev/null)
  echo "$birthtime|$modtime|$f"
done | sort -r | while IFS='|' read -r created updated filepath; do
  # Derive display name from filename: strip .md, replace hyphens with spaces
  basename=$(basename "$filepath" .md)
  displayname=$(echo "$basename" | tr '-' ' ')

  # Derive category from directory
  dirpath=$(dirname "$filepath")
  if [ "$dirpath" = "." ]; then
    category="Root"
  else
    category="$dirpath"
  fi

  # URL-encode spaces for links
  linkpath=$(echo "$filepath" | sed 's/ /%20/g')

  # Print date header if new date
  if [ "$created" != "$CURRENT_DATE" ]; then
    CURRENT_DATE="$created"
    echo "" >> "$OUTPUT"
    echo "## $created" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "| Category | Document | Last Updated |" >> "$OUTPUT"
    echo "|----------|----------|--------------|" >> "$OUTPUT"
  fi

  echo "| $category | [$displayname]($linkpath) | $updated |" >> "$OUTPUT"
done

echo "" >> "$OUTPUT"
echo "---" >> "$OUTPUT"
echo "*Last rebuilt: $(date '+%Y-%m-%d %H:%M')*" >> "$OUTPUT"
