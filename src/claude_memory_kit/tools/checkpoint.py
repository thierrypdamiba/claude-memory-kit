"""Session checkpoint: structured snapshot of working context.

Checkpoints are stored as journal entries with gate='checkpoint'.
They capture what matters between sessions: task context, decisions,
failed approaches, and next steps. Loaded automatically at session start.
"""

import logging
from datetime import datetime, timezone

from ..store import Store
from ..types import JournalEntry, Gate

log = logging.getLogger("cmk")

# Structured prompt that forces useful checkpoint content.
# This is included in the tool description so Claude knows what to write.
CHECKPOINT_GUIDANCE = (
    "Include: (1) current task/goal, (2) key decisions made and WHY, "
    "(3) what was tried that didn't work, (4) open questions or blockers, "
    "(5) concrete next steps. Be specific. Skip pleasantries."
)

# Auto-checkpoint interval (separate from reflect interval)
CHECKPOINT_EVERY = 8


async def do_checkpoint(
    store: Store,
    summary: str,
    user_id: str = "local",
) -> str:
    """Save a session checkpoint to the journal."""
    entry = JournalEntry(
        timestamp=datetime.now(timezone.utc),
        gate=Gate.checkpoint,
        content=summary,
    )
    store.qdrant.insert_journal(entry, user_id=user_id)
    return "Checkpoint saved. This will be loaded at the start of your next session."
