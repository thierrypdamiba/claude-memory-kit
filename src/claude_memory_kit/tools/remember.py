import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from ..store import Store
from ..types import DecayClass, Gate, JournalEntry, Memory

log = logging.getLogger("cmk")

# Patterns that suggest sensitive data
_PII_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "API key (sk-...)"),
    (re.compile(r"sk_(?:live|test)_[a-zA-Z0-9]{20,}"), "Stripe key"),
    (re.compile(r"pk_(?:live|test)_[a-zA-Z0-9]{20,}"), "Stripe publishable key"),
    (re.compile(r"cmk-sk-[a-zA-Z0-9]+"), "CMK secret key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub personal access token"),
    (re.compile(r"gho_[a-zA-Z0-9]{36}"), "GitHub OAuth token"),
    (re.compile(r"xox[baprs]-[a-zA-Z0-9\-]+"), "Slack token"),
    (re.compile(r"eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}"), "JWT token"),
    (re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE), "password"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "credit card number"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN"),
]


def _check_pii(content: str) -> str | None:
    """Check content for common PII patterns. Returns warning string or None."""
    for pattern, label in _PII_PATTERNS:
        if pattern.search(content):
            return f"This memory appears to contain a {label}. Consider removing sensitive data."
    return None


async def do_remember(
    store: Store,
    content: str,
    gate_str: str,
    person: str | None = None,
    project: str | None = None,
    user_id: str = "local",
) -> str:
    gate = Gate.from_str(gate_str)
    if gate is None:
        return (
            f"invalid gate '{gate_str}'. "
            "use: behavioral, relational, epistemic, promissory, correction"
        )

    now = datetime.now(timezone.utc)
    mem_id = f"mem_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    memory = Memory(
        id=mem_id,
        created=now,
        gate=gate,
        person=person,
        project=project,
        confidence=0.9,
        last_accessed=now,
        access_count=1,
        decay_class=DecayClass.from_gate(gate),
        content=content,
    )

    # 1. Journal entry
    entry = JournalEntry(
        timestamp=now,
        gate=gate,
        content=content,
        person=person,
        project=project,
    )
    store.db.insert_journal(entry, user_id=user_id)

    # 2. Insert into SQLite
    store.db.insert_memory(memory, user_id=user_id)

    # 3. Vector store
    try:
        store.vectors.upsert(mem_id, content, person, project, user_id=user_id)
    except Exception as e:
        log.warning("vector upsert failed: %s", e)

    # 4. Auto-link graph edges
    store.db.auto_link(mem_id, person, project, user_id=user_id)

    # 5. Contradiction check via vectors
    warning = ""
    try:
        similar = store.vectors.search(content, limit=3, user_id=user_id)
        for sid, score in similar:
            if sid != mem_id and score > 0.85:
                existing = store.db.get_memory(sid, user_id=user_id)
                if existing and existing.content != content:
                    warning = (
                        f"\n\nwarning: high similarity (score={score:.2f}) "
                        f"with existing memory [{sid}]. "
                        "possible contradiction or duplicate."
                    )
                    break
    except Exception as e:
        log.warning("contradiction check failed: %s", e)

    # 6. Correction gate: create CONTRADICTS edge, downgrade old
    if gate == Gate.correction:
        try:
            similar = store.vectors.search(content, limit=1, user_id=user_id)
            for sid, score in similar:
                if sid != mem_id and score > 0.5:
                    store.db.add_edge(
                        mem_id, sid, "CONTRADICTS", user_id=user_id
                    )
                    old = store.db.get_memory(sid, user_id=user_id)
                    if old:
                        store.db.update_confidence(
                            sid, old.confidence * 0.5, user_id=user_id
                        )
        except Exception as e:
            log.warning("correction handling failed: %s", e)

    # 7. Memory chains: FOLLOWS edge for same person+project within 24h
    if person or project:
        try:
            cutoff = (now - timedelta(hours=24)).isoformat()
            recent = store.db.conn.execute(
                "SELECT id FROM memories "
                "WHERE id != ? AND created > ? AND user_id = ? "
                "AND (person = ? OR project = ?) "
                "ORDER BY created DESC LIMIT 1",
                (mem_id, cutoff, user_id, person or "", project or ""),
            ).fetchone()
            if recent:
                store.db.add_edge(
                    mem_id, recent[0], "FOLLOWS", user_id=user_id
                )
        except Exception as e:
            log.warning("memory chain failed: %s", e)

    # 8. PII detection
    pii_warning = _check_pii(content)
    if pii_warning:
        warning += f"\n\nWARNING: {pii_warning}"

    # 9. Opus sensitivity classification
    try:
        from ..config import get_api_key
        api_key = get_api_key()
        if api_key:
            from .classify import classify_single
            classification = await classify_single(store, mem_id, user_id)
            level = classification.get("level", "unknown")
            if level not in ("safe", "unknown"):
                warning += (
                    f"\n\nSENSITIVITY: {level} "
                    f"({classification.get('reason', '')})"
                )
    except Exception as e:
        log.warning("sensitivity classification failed: %s", e)

    preview = content[:80] if len(content) > 80 else content
    return f"Remembered [{gate.value}]: {preview} (id: {mem_id}){warning}"
