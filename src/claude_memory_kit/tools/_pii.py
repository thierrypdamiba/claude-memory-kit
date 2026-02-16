"""Shared PII/sensitive-data detection patterns.

Used by both remember.py (inline warning) and scan.py (bulk scan).
This is the single source of truth for pattern definitions.
"""

import re

# Canonical pattern list: (label, compiled regex)
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
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


def luhn_check(num_str: str) -> bool:
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


def check_pii(content: str) -> str | None:
    """Quick check for PII patterns. Returns warning string or None."""
    for label, pattern in PII_PATTERNS:
        if pattern.search(content):
            return f"This memory appears to contain a {label}. Consider removing sensitive data."
    return None
