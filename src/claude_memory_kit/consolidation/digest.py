import logging
from collections import defaultdict

from ..extract import consolidate_entries
from ..types import Gate

log = logging.getLogger("cmk")


async def consolidate_journals(
    db, api_key: str, user_id: str = "local"
) -> str | None:
    """Consolidate old journal entries into weekly digests."""
    stale_dates = db.stale_journal_dates(max_age_days=14, user_id=user_id)
    if not stale_dates:
        return None

    # Group by ISO week
    from datetime import datetime
    week_groups: dict[str, list[str]] = defaultdict(list)
    for date_str in stale_dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_key = dt.strftime("%G-W%V")
        week_groups[week_key].append(date_str)

    digests_written = []
    for week_key, dates in week_groups.items():
        combined = []
        for date in dates:
            entries = db.journal_by_date(date, user_id=user_id)
            for e in entries:
                combined.append(
                    f"[{e['gate']}] {e['content']}"
                )
        if not combined:
            continue

        digest = await consolidate_entries("\n".join(combined), api_key)

        # Store digest as a special journal entry
        db.insert_journal_raw(
            date=week_key,
            gate=Gate.digest,
            content=f"# Week {week_key}\n\n{digest}",
            user_id=user_id,
        )

        # Archive original entries
        for date in dates:
            db.archive_journal_date(date, user_id=user_id)

        digests_written.append(week_key)

    if not digests_written:
        return None
    return f"Consolidated {len(digests_written)} weeks: {', '.join(digests_written)}"
