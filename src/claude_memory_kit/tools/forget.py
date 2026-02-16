import logging

from ..store import Store

log = logging.getLogger("cmk")


async def do_forget(
    store: Store, memory_id: str, reason: str,
    user_id: str = "local",
) -> str:
    memory = store.qdrant.delete_memory(memory_id, user_id=user_id)
    if memory is None:
        return f"No memory found with id: {memory_id}"

    return f"Forgotten: {memory_id} (reason: {reason})."
