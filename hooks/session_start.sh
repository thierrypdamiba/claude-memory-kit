#!/bin/bash
# Claude Code SessionStart hook
# Loads identity card + recent journal context on session start

STORE="${MEMORY_STORE_PATH:-$HOME/.claude-memory/store}"
IDENTITY="$STORE/identity.md"
JOURNAL_DIR="$STORE/journal"

context=""

# Load identity card
if [ -f "$IDENTITY" ]; then
    context="$(cat "$IDENTITY")"
fi

# Load last 2 journal entries
if [ -d "$JOURNAL_DIR" ]; then
    recent=$(ls -1 "$JOURNAL_DIR"/*.md 2>/dev/null | sort | tail -2)
    for f in $recent; do
        context="$context

---
$(cat "$f")"
    done
fi

if [ -n "$context" ]; then
    echo "{\"hookSpecificOutput\":{\"additionalContext\":$(echo "$context" | jq -Rs .)}}"
fi
