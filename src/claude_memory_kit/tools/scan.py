import re
import logging

from ..store import Store

log = logging.getLogger("cmk")

# Patterns for common sensitive data: (label, compiled regex)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("API key (sk-)", re.compile(r"sk-[a-zA-Z0-9_-]{20,}")),
    ("Stripe key", re.compile(r"sk_(?:live|test)_[a-zA-Z0-9]{20,}")),
    ("Stripe publishable key", re.compile(r"pk_(?:live|test)_[a-zA-Z0-9]{20,}")),
    ("CMK secret key", re.compile(r"cmk-sk-[a-zA-Z0-9_-]{10,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(r"gh[ps]_[A-Za-z0-9_]{36,}")),
    ("Slack token", re.compile(r"xox[baprs]-[a-zA-Z0-9-]+")),
    ("JWT token", re.compile(r"eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}")),
    ("Generic secret", re.compile(r"(?i)(?:password|passwd|secret|token)\s*[=:]\s*\S{8,}")),
    ("Bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("Private key header", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("Credit card (Visa)", re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b")),
    ("Credit card (MC)", re.compile(r"\b5[1-5][0-9]{14}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("Email address", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("Phone number (US)", re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
]


def _luhn_check(num_str: str) -> bool:
    """Verify a number string passes the Luhn algorithm."""
    digits = [int(d) for d in num_str if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def scan_content(text: str) -> list[dict]:
    """Scan a string for PII/sensitive data patterns. Returns list of findings."""
    findings = []
    for label, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            # For credit card patterns, verify with Luhn
            if label.startswith("Credit card"):
                digits = re.sub(r"\D", "", match.group())
                if not _luhn_check(digits):
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
    memories = store.db.list_memories(limit=limit, user_id=user_id)

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
