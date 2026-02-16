import re
import logging

from ..store import Store
from ._pii import PII_PATTERNS, luhn_check

log = logging.getLogger("cmk")


def scan_content(text: str) -> list[dict]:
    """Scan a string for PII/sensitive data patterns. Returns list of findings."""
    findings = []
    for label, pattern in PII_PATTERNS:
        for match in pattern.finditer(text):
            # For credit card patterns, verify with Luhn
            if label.startswith("Credit card"):
                digits = re.sub(r"\D", "", match.group())
                if not luhn_check(digits):
                    continue
            findings.append({
                "type": label,
                "match": match.group()[:40],
                "position": match.start(),
            })
    return findings


async def do_scan(
    store: Store, user_id: str = "local", limit: int = 500
) -> str:
    """Scan all memories for PII/sensitive data patterns."""
    memories = store.qdrant.list_memories(limit=limit, user_id=user_id)

    flagged = []
    for mem in memories:
        findings = scan_content(mem.content)
        if findings:
            types = sorted(set(f["type"] for f in findings))
            preview = mem.content[:60] + "..." if len(mem.content) > 60 else mem.content
            flagged.append({
                "id": mem.id,
                "gate": mem.gate.value,
                "types": types,
                "preview": preview,
            })

    if not flagged:
        return f"Scanned {len(memories)} memories. No sensitive data patterns found."

    lines = [f"Scanned {len(memories)} memories. Found {len(flagged)} with potential sensitive data:\n"]
    for item in flagged:
        types_str = ", ".join(item["types"])
        lines.append(
            f"  [{item['gate']}] {item['id']}: {types_str}\n"
            f"    preview: {item['preview']}"
        )

    return "\n".join(lines)
