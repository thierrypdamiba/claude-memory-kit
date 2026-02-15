import logging
from datetime import datetime, timezone

from ..config import get_api_key
from ..extract import regenerate_identity
from ..store import Store
from ..types import IdentityCard, OnboardingState

log = logging.getLogger("cmk")

COLD_START = (
    "First session. I don't know you yet. "
    "What should I call you?"
)

STEP_2_TEMPLATE = (
    "Nice to meet you, {person}. "
    "What are you working on right now?"
)

STEP_3_TEMPLATE = (
    "Got it. How do you like to work with me? "
    "Fast and direct, or more deliberate and exploratory?"
)


async def do_identity(
    store: Store, onboard_response: str | None = None,
    user_id: str = "local",
) -> str:
    # If identity exists, return it
    identity = store.db.get_identity(user_id=user_id)
    if identity:
        output = identity.content
        # Append recent journal context
        recent = store.db.recent_journal(days=2, user_id=user_id)
        if recent:
            output += "\n\n---\nRecent context:\n"
            for e in recent[:10]:
                output += f"[{e['gate']}] {e['content']}\n"
        return output

    # Onboarding flow
    state = store.db.get_onboarding(user_id=user_id)

    if state is None and onboard_response is None:
        store.db.set_onboarding(OnboardingState(step=0), user_id=user_id)
        return COLD_START

    if state is None:
        state = OnboardingState(step=0)

    if onboard_response is None:
        if state.step == 0:
            return COLD_START
        if state.step == 1:
            return STEP_2_TEMPLATE.format(person=state.person or "friend")
        if state.step == 2:
            return STEP_3_TEMPLATE
        return COLD_START

    # Process onboarding response
    if state.step == 0:
        state.person = onboard_response.strip()
        state.step = 1
        store.db.set_onboarding(state, user_id=user_id)
        return STEP_2_TEMPLATE.format(person=state.person)

    if state.step == 1:
        state.project = onboard_response.strip()
        state.step = 2
        store.db.set_onboarding(state, user_id=user_id)
        return STEP_3_TEMPLATE

    if state.step == 2:
        state.style = onboard_response.strip()
        state.step = 3

        api_key = get_api_key()
        raw = (
            f"Name: {state.person}\n"
            f"Working on: {state.project}\n"
            f"Communication style: {state.style}\n"
        )
        if api_key:
            try:
                content = await regenerate_identity(raw, api_key)
            except Exception as e:
                log.warning("identity synthesis failed: %s", e)
                content = (
                    f"I work with {state.person}. "
                    f"They're building {state.project}. "
                    f"They prefer: {state.style}."
                )
        else:
            content = (
                f"I work with {state.person}. "
                f"They're building {state.project}. "
                f"They prefer: {state.style}."
            )

        card = IdentityCard(
            person=state.person,
            project=state.project,
            content=content,
            last_updated=datetime.now(timezone.utc),
        )
        store.db.set_identity(card, user_id=user_id)
        store.db.delete_onboarding(user_id=user_id)
        return f"Got it. Identity card created. I'll remember you.\n\n{content}"

    return COLD_START
