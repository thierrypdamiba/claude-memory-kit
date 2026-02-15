import asyncio
import logging

from ..store import Store

log = logging.getLogger("cmk")


async def do_recall(
    store: Store, query: str, user_id: str = "local"
) -> str:
    results = []
    seen_ids: set[str] = set()

    # 1. FTS search (sync, run in thread)
    fts_results = await asyncio.to_thread(
        store.db.search_fts, query, 5, user_id
    )
    for mem in fts_results:
        if mem.id not in seen_ids:
            seen_ids.add(mem.id)
            store.db.touch_memory(mem.id, user_id=user_id)
            person = mem.person or "?"
            results.append(
                f"[{mem.gate.value}] ({mem.created:%Y-%m-%d}, {person}) "
                f"{mem.content}\n  id: {mem.id}"
            )

    # 2. Vector search (sync, run in thread)
    try:
        vec_results = await asyncio.to_thread(
            store.vectors.search, query, 5, user_id
        )
        for mem_id, score in vec_results:
            if mem_id not in seen_ids:
                seen_ids.add(mem_id)
                full = store.db.get_memory(mem_id, user_id=user_id)
                if full:
                    store.db.touch_memory(mem_id, user_id=user_id)
                    person = full.person or "?"
                    results.append(
                        f"[{full.gate.value}, vector={score:.2f}] "
                        f"({full.created:%Y-%m-%d}, {person}) "
                        f"{full.content}\n  id: {full.id}"
                    )
                else:
                    results.append(
                        f"[vector match, score={score:.2f}] id: {mem_id}"
                    )
    except Exception as e:
        log.warning("vector search failed: %s", e)

    # 3. Graph traversal for sparse results
    if len(results) < 3:
        for mid in list(seen_ids)[:2]:
            related = store.db.find_related(
                mid, depth=2, user_id=user_id
            )
            for rel in related:
                rid = rel["id"]
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    results.append(
                        f"[graph: {rel['relation']}] "
                        f"{rel['preview']} (id: {rid})"
                    )

    if not results:
        return "No memories found matching that query."

    return f"Found {len(results)} memories:\n\n" + "\n\n".join(results)
