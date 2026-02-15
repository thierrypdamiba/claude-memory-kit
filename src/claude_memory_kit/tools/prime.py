import logging

from ..store import Store

log = logging.getLogger("cmk")


async def do_prime(
    store: Store, message: str, user_id: str = "local"
) -> str:
    """Proactive recall. Hybrid search (dense + sparse, RRF) top 3."""
    try:
        results = store.vectors.search(message, limit=3, user_id=user_id)
    except Exception as e:
        log.warning("prime hybrid search failed: %s", e)
        return "No relevant memories found."

    if not results:
        return "No relevant memories found."

    lines = []
    for mem_id, score in results:
        if score < 0.3:
            continue
        full = store.db.get_memory(mem_id, user_id=user_id)
        if full:
            store.db.touch_memory(mem_id, user_id=user_id)
            lines.append(
                f"[{full.gate.value}, relevance={score:.2f}] {full.content}"
            )

    if not lines:
        return "No relevant memories found."

    return "Relevant context from memory:\n" + "\n".join(lines)
