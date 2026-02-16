import asyncio
import logging

from ..store import Store

log = logging.getLogger("cmk")


async def do_recall(
    store: Store, query: str, user_id: str = "local"
) -> str:
    results = []
    seen_ids: set[str] = set()

    # 1. Hybrid search (dense + sparse with RRF fusion) via Qdrant
    try:
        vec_results = await asyncio.to_thread(
            store.qdrant.search, query, 10, user_id
        )
        for mem_id, score in vec_results:
            if mem_id not in seen_ids:
                seen_ids.add(mem_id)
                full = store.qdrant.get_memory(mem_id, user_id=user_id)
                if full:
                    store.qdrant.touch_memory(mem_id, user_id=user_id)
                    person = full.person or "?"
                    results.append(
                        f"[{full.gate.value}, score={score:.2f}] "
                        f"({full.created:%Y-%m-%d}, {person}) "
                        f"{full.content}\n  id: {full.id}"
                    )
    except Exception as e:
        log.warning("hybrid search failed: %s", e)

    # 2. Text search fallback when hybrid returned nothing
    if not results and not store.qdrant._disabled:
        try:
            text_results = await asyncio.to_thread(
                store.qdrant.search_text, query, 5, user_id
            )
            for mem_id, score in text_results:
                if mem_id not in seen_ids:
                    seen_ids.add(mem_id)
                    full = store.qdrant.get_memory(mem_id, user_id=user_id)
                    if full:
                        store.qdrant.touch_memory(mem_id, user_id=user_id)
                        person = full.person or "?"
                        results.append(
                            f"[{full.gate.value}, text] "
                            f"({full.created:%Y-%m-%d}, {person}) "
                            f"{full.content}\n  id: {full.id}"
                        )
        except Exception as e:
            log.warning("text search failed: %s", e)

    # 3. Graph traversal for sparse results
    if len(results) < 3:
        for mid in list(seen_ids)[:2]:
            related = store.qdrant.find_related(
                mid, depth=2, user_id=user_id
            )
            for rel in related:
                rid = rel["id"]
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    preview = rel.get("content", "")[:80]
                    results.append(
                        f"[graph: {rel['relation']}] "
                        f"{preview} (id: {rid})"
                    )

    if not results:
        return "No memories found matching that query."

    return f"Found {len(results)} memories:\n\n" + "\n\n".join(results)
