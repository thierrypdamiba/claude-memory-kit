"""Opus-powered sensitivity classification for memories."""

import json
import logging

from ..config import get_api_key
from ..extract import _call_anthropic
from ..store import Store

log = logging.getLogger("cmk")

CLASSIFY_PROMPT = """You are a privacy classifier for a personal memory system.
Analyze each memory and classify its sensitivity level.

Levels:
- safe: general knowledge, preferences, project details, technical notes,
  coding patterns, tool usage, workflow preferences
- sensitive: personal health, finances, salary, relationships, private opinions,
  emotional states, family details, anything embarrassing or harmful if leaked
- critical: passwords, API keys, tokens, SSNs, credit cards, legal matters,
  content that could cause direct harm if exposed

For each memory, return:
- id: the memory id exactly as given
- level: safe|sensitive|critical
- reason: 1-sentence explanation of why

Return JSON array only, no other text:
[{"id": "mem_xxx", "level": "sensitive", "reason": "Contains salary information"}]

If all memories are safe, still return the array with level "safe" for each."""

CLASSIFY_SINGLE_PROMPT = """You are a privacy classifier for a personal memory system.
Classify this single memory's sensitivity level.

Levels:
- safe: general knowledge, preferences, project details, technical notes
- sensitive: personal health, finances, relationships, private opinions,
  emotional states, family details, anything embarrassing if leaked
- critical: passwords, API keys, tokens, SSNs, credit cards, legal matters,
  content that could cause direct harm if exposed

Return JSON only, no other text:
{"level": "safe", "reason": "General technical preference"}"""


def _parse_json_array(text: str) -> list[dict]:
    """Parse JSON array from LLM response, with fallback extraction."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return []


def _parse_json_object(text: str) -> dict:
    """Parse JSON object from LLM response, with fallback extraction."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}


async def classify_single(
    store: Store,
    memory_id: str,
    user_id: str = "local",
) -> dict:
    """Classify a single memory's sensitivity using Opus.

    Returns {"level": "safe|sensitive|critical", "reason": "..."}.
    Returns {"level": "unknown", "reason": "classification failed"} on error.
    """
    api_key = get_api_key()
    if not api_key:
        return {"level": "unknown", "reason": "no API key configured"}

    mem = store.db.get_memory(memory_id, user_id=user_id)
    if not mem:
        return {"level": "unknown", "reason": "memory not found"}

    try:
        text = await _call_anthropic(
            CLASSIFY_SINGLE_PROMPT,
            f"Memory content:\n{mem.content}",
            api_key,
            max_tokens=256,
        )
        result = _parse_json_object(text)
        level = result.get("level", "unknown")
        reason = result.get("reason", "")

        if level in ("safe", "sensitive", "critical"):
            store.db.update_sensitivity(memory_id, level, reason, user_id=user_id)
            return {"level": level, "reason": reason}

        return {"level": "unknown", "reason": "invalid classification response"}
    except Exception as e:
        log.warning("classify_single failed for %s: %s", memory_id, e)
        return {"level": "unknown", "reason": str(e)}


async def classify_memories(
    store: Store,
    user_id: str = "local",
    batch_size: int = 20,
    force: bool = False,
) -> str:
    """Batch-classify memories for sensitivity using Opus.

    Args:
        store: Memory store instance.
        user_id: User to classify for.
        batch_size: Memories per API call.
        force: If True, re-classify all memories (not just unclassified).

    Returns summary string.
    """
    api_key = get_api_key()
    if not api_key:
        return "No API key configured. Cannot classify memories."

    if force:
        memories = store.db.list_memories(limit=500, user_id=user_id)
    else:
        memories = store.db.list_memories_by_sensitivity(
            None, limit=500, user_id=user_id
        )

    if not memories:
        return "No memories to classify."

    total = len(memories)
    counts = {"safe": 0, "sensitive": 0, "critical": 0, "failed": 0}

    # Process in batches
    for i in range(0, total, batch_size):
        batch = memories[i : i + batch_size]
        batch_text = "\n".join(
            f"[{m.id}] {m.content}" for m in batch
        )

        try:
            text = await _call_anthropic(
                CLASSIFY_PROMPT,
                f"Memories to classify:\n{batch_text}",
                api_key,
                max_tokens=2048,
            )
            results = _parse_json_array(text)

            # Index results by id for lookup
            by_id = {r["id"]: r for r in results if "id" in r}

            for mem in batch:
                r = by_id.get(mem.id)
                if r and r.get("level") in ("safe", "sensitive", "critical"):
                    store.db.update_sensitivity(
                        mem.id, r["level"], r.get("reason", ""),
                        user_id=user_id,
                    )
                    counts[r["level"]] += 1
                else:
                    counts["failed"] += 1

        except Exception as e:
            log.warning("batch classification failed: %s", e)
            counts["failed"] += len(batch)

    parts = [f"Classified {total} memories:"]
    for level in ("safe", "sensitive", "critical"):
        if counts[level]:
            parts.append(f"  {level}: {counts[level]}")
    if counts["failed"]:
        parts.append(f"  failed: {counts['failed']}")
    return "\n".join(parts)


async def reclassify_memory(
    store: Store,
    memory_id: str,
    new_level: str,
    user_id: str = "local",
) -> str:
    """Manually reclassify a memory's sensitivity level."""
    if new_level not in ("safe", "sensitive", "critical"):
        return f"Invalid level '{new_level}'. Use: safe, sensitive, critical"

    mem = store.db.get_memory(memory_id, user_id=user_id)
    if not mem:
        return "Memory not found."

    store.db.update_sensitivity(
        memory_id, new_level, "manually reclassified by user",
        user_id=user_id,
    )
    return f"Reclassified {memory_id} as {new_level}."
