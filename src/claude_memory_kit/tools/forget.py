import logging

from ..store import Store

log = logging.getLogger("cmk")


async def do_forget(
    store: Store, memory_id: str, reason: str,
    user_id: str = "local",
) -> str:
    memory = store.db.delete_memory(memory_id, user_id=user_id)
    if memory is None:
        return f"No memory found with id: {memory_id}"

    # Archive with reason
    store.db.archive_memory(
        memory_id, memory.gate.value, memory.content, reason,
        user_id=user_id,
    )

    # Remove from vector store
    try:
        store.vectors.delete(memory_id, user_id=user_id)
    except Exception as e:
        log.warning("vector delete failed: %s", e)

    return (
        f"Forgotten: {memory_id} (reason: {reason}). "
        "Archived for accountability."
    )
