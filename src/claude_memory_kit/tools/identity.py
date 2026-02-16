import logging
from datetime import datetime, timezone

from ..config import get_api_key
from ..extract import regenerate_identity
from ..store import Store
from ..types import IdentityCard

log = logging.getLogger("cmk")


async def do_identity(
    store: Store, onboard_response: str | None = None,
    user_id: str = "local",
) -> str:
    # If identity exists, return it
    identity = store.qdrant.get_identity(user_id=user_id)
    if identity:
        output = identity.content
        # Append recent journal context
        recent = store.qdrant.recent_journal(days=2, user_id=user_id)
        if recent:
            output += "\n\n---\nRecent context:\n"
            for e in recent[:10]:
                output += f"[{e['gate']}] {e['content']}\n"
        return output

    # No identity yet. Create a basic one from the onboard response or
    # return a prompt asking for info.
    if not onboard_response:
        return (
            "No identity card yet. Tell me your name and what you're "
            "working on, and I'll create one."
        )

    api_key = get_api_key()
    if api_key:
        try:
            content = await regenerate_identity(onboard_response, api_key)
        except Exception as e:
            log.warning("identity synthesis failed: %s", e)
            content = onboard_response
    else:
        content = onboard_response

    card = IdentityCard(
        person=None,
        project=None,
        content=content,
        last_updated=datetime.now(timezone.utc),
    )
    store.qdrant.set_identity(card, user_id=user_id)
    return f"Identity card created.\n\n{content}"
