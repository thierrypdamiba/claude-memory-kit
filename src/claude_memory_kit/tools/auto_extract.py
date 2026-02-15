import logging

from ..config import get_api_key
from ..extract import extract_memories
from ..store import Store
from .remember import do_remember

log = logging.getLogger("cmk")


async def do_auto_extract(
    store: Store, transcript: str, user_id: str = "local"
) -> str:
    api_key = get_api_key()
    if not api_key:
        return "No API key configured. Cannot extract memories."

    memories = await extract_memories(transcript, api_key)
    if not memories:
        return "No memories worth keeping from this transcript."

    saved = []
    for mem in memories:
        try:
            msg = await do_remember(
                store,
                mem.get("content", ""),
                mem.get("gate", "epistemic"),
                mem.get("person"),
                mem.get("project"),
                user_id=user_id,
            )
            saved.append(msg)
        except Exception as e:
            log.warning("auto-extract save failed: %s", e)

    return (
        f"Auto-extracted {len(saved)} memories from transcript:\n"
        + "\n".join(saved)
    )
