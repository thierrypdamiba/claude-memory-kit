import math
from datetime import datetime, timezone

from ..types import DecayClass, Memory


def compute_decay_score(memory: Memory) -> float:
    """0.0 = should archive, 1.0 = very alive."""
    return _recency(memory) * _frequency(memory)


def _recency(memory: Memory) -> float:
    half_life = memory.decay_class.half_life_days()
    if half_life is None:
        return 1.0  # never decays
    now = datetime.now(timezone.utc)
    days_since = (now - memory.last_accessed).total_seconds() / 86400
    return math.pow(0.5, days_since / half_life)


def _frequency(memory: Memory) -> float:
    # log(access_count + 1) normalized so 1 access = 1.0
    return math.log(memory.access_count + 1) / math.log(2)


def is_fading(memory: Memory) -> bool:
    if memory.decay_class == DecayClass.never:
        return False
    return compute_decay_score(memory) < 0.1
