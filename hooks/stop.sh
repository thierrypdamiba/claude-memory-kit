#!/bin/bash
# Claude Code Stop hook
# Auto-extracts memories from the session transcript via Haiku

BINARY="${CLAUDE_MEMORY_BIN:-/Users/thierrydamiba/claude-memory/target/release/claude-memory}"
STORE="${MEMORY_STORE_PATH:-$HOME/.claude-memory/store}"

export MEMORY_STORE_PATH="$STORE"

# Read hook input from stdin, extract transcript
if [ -t 0 ]; then
    exit 0
fi

# Pass transcript to the binary in --extract mode
# Timeout after 30 seconds (Haiku is fast)
timeout 30 "$BINARY" --extract < /dev/stdin 2>/dev/null

exit 0
