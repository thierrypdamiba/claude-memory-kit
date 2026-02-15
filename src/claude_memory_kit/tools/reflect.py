import logging
from datetime import datetime, timezone

from ..config import get_api_key
from ..consolidation.decay import is_fading
from ..consolidation.digest import consolidate_journals
from ..extract import regenerate_identity
from ..store import Store
from ..types import IdentityCard

log = logging.getLogger("cmk")


async def do_reflect(store: Store, user_id: str = "local") -> str:
    api_key = get_api_key()
    report = []

    # 1. Consolidate old journals into weekly digests
    if api_key:
        result = await consolidate_journals(
            store.db, api_key, user_id=user_id
        )
        if result:
            report.append(result)
        else:
            report.append("No journals old enough to consolidate.")
    else:
        report.append("No API key. Skipping journal consolidation.")

    # 2. Apply decay: archive fading memories
    fading_count = 0
    all_memories = store.db.list_memories(limit=500, user_id=user_id)
    for mem in all_memories:
        if is_fading(mem):
            store.db.archive_memory(
                mem.id, mem.gate.value, mem.content,
                "auto-archived: decay score below threshold",
                user_id=user_id,
            )
            store.db.delete_memory(mem.id, user_id=user_id)
            try:
                store.vectors.delete(mem.id, user_id=user_id)
            except Exception:
                pass
            fading_count += 1
    if fading_count:
        report.append(f"Archived {fading_count} fading memories.")

    # 3. Regenerate identity card from recent memories
    if api_key:
        recent = store.db.recent_journal(days=5, user_id=user_id)
        if recent:
            entries_text = "\n".join(
                f"[{e['gate']}] {e['content']}" for e in recent
            )
            try:
                new_content = await regenerate_identity(
                    entries_text, api_key
                )
                old_identity = store.db.get_identity(user_id=user_id)
                card = IdentityCard(
                    person=(
                        old_identity.person if old_identity else None
                    ),
                    project=(
                        old_identity.project if old_identity else None
                    ),
                    content=new_content,
                    last_updated=datetime.now(timezone.utc),
                )
                store.db.set_identity(card, user_id=user_id)
                report.append("Identity card regenerated.")
            except Exception as e:
                report.append(f"Identity regeneration failed: {e}")

    if not report:  # pragma: no cover - consolidation block always appends
        return "Reflection complete. Nothing to consolidate."
    return "Reflection complete:\n- " + "\n- ".join(report)
