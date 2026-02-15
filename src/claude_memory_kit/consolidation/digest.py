import logging
from collections import defaultdict

from ..extract import consolidate_entries
from ..store.sqlite import SqliteStore

log = logging.getLogger("cmk")


async def consolidate_journals(
    db: SqliteStore, api_key: str, user_id: str = "local"
) -> str | None:
    """Consolidate old journal entries into weekly digests."""
    stale_dates = db.stale_journal_dates(max_age_days=14, user_id=user_id)
    if not stale_dates:
        return None

    # Group by ISO week
    from datetime import datetime
    week_groups: dict[str, list[str]] = defaultdict(list)
    for date_str in stale_dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            log.warning("skipping malformed journal date: %s", date_str)
            continue
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

        try:
            digest = await consolidate_entries("\n".join(combined), api_key)
        except Exception as e:
            log.warning("consolidation failed for %s: %s", week_key, e)
            continue

        # Store digest as a special journal entry
        db.conn.execute(
            "INSERT INTO journal "
            "(date, timestamp, gate, content, person, project, user_id) "
            "VALUES (?, datetime('now'), 'epistemic', ?, NULL, NULL, ?)",
            (week_key, f"# Week {week_key}\n\n{digest}", user_id),
        )
        db.conn.commit()

        # Archive original entries
        for date in dates:
            db.archive_journal_date(date, user_id=user_id)

        digests_written.append(week_key)

    if not digests_written:
        return None
    return f"Consolidated {len(digests_written)} weeks: {', '.join(digests_written)}"
