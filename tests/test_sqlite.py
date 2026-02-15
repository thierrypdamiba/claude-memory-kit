"""Comprehensive tests for SqliteStore."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from claude_memory_kit.types import (
    DecayClass,
    Gate,
    IdentityCard,
    JournalEntry,
    Memory,
    OnboardingState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return f"u_{uuid.uuid4().hex[:8]}"


def _mid() -> str:
    return f"mem_{uuid.uuid4().hex[:12]}"


# ===========================================================================
# Migration
# ===========================================================================


class TestMigration:
    def test_migrate_creates_tables(self, db):
        tables = {
            r[0]
            for r in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "memories", "journal", "identity", "edges",
            "relationships", "onboarding", "archive",
            "users", "api_keys", "rules", "memories_fts",
        }
        assert expected.issubset(tables)

    def test_migrate_idempotent(self, db):
        """Running migrate() twice must not raise."""
        db.migrate()
        db.migrate()
        count = db.count_memories()
        assert count == 0

    def test_fts_triggers_exist(self, db):
        triggers = {
            r[0]
            for r in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
        }
        assert {"memories_ai", "memories_ad", "memories_au"}.issubset(triggers)

    def test_indexes_exist(self, db):
        indexes = {
            r[0]
            for r in db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        assert "idx_memories_user" in indexes
        assert "idx_journal_user" in indexes
        assert "idx_rules_user" in indexes
        assert "idx_memories_user_sensitivity" in indexes


# ===========================================================================
# Memory CRUD
# ===========================================================================


class TestMemoryCRUD:
    def test_insert_and_get(self, db, make_memory):
        mem = make_memory(id="m1", content="hello world")
        db.insert_memory(mem)
        got = db.get_memory("m1")
        assert got is not None
        assert got.id == "m1"
        assert got.content == "hello world"
        assert got.gate == Gate.epistemic

    def test_get_nonexistent(self, db):
        assert db.get_memory("does_not_exist") is None

    def test_insert_replaces_on_same_id(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="v1"))
        db.insert_memory(make_memory(id="m1", content="v2"))
        got = db.get_memory("m1")
        assert got.content == "v2"

    def test_delete_returns_memory(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        deleted = db.delete_memory("m1")
        assert deleted is not None
        assert deleted.id == "m1"
        assert db.get_memory("m1") is None

    def test_delete_nonexistent_returns_none(self, db):
        assert db.delete_memory("ghost") is None

    def test_update_content(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="old"))
        db.update_memory("m1", content="new")
        assert db.get_memory("m1").content == "new"

    def test_update_gate(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", gate=Gate.epistemic))
        db.update_memory("m1", gate="relational")
        assert db.get_memory("m1").gate == Gate.relational

    def test_update_person_and_project(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.update_memory("m1", person="Alice", project="Alpha")
        got = db.get_memory("m1")
        assert got.person == "Alice"
        assert got.project == "Alpha"

    def test_update_ignores_disallowed_keys(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="safe"))
        db.update_memory("m1", content="updated", created="HACKED")
        got = db.get_memory("m1")
        assert got.content == "updated"
        assert got.id == "m1"

    def test_update_with_no_valid_keys_is_noop(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="unchanged"))
        db.update_memory("m1", bogus="value")
        assert db.get_memory("m1").content == "unchanged"

    def test_touch_increments_access(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", access_count=1))
        db.touch_memory("m1")
        got = db.get_memory("m1")
        assert got.access_count == 2
        db.touch_memory("m1")
        got = db.get_memory("m1")
        assert got.access_count == 3

    def test_touch_updates_last_accessed(self, db, make_memory):
        mem = make_memory(id="m1")
        db.insert_memory(mem)
        original_accessed = db.get_memory("m1").last_accessed
        db.touch_memory("m1")
        new_accessed = db.get_memory("m1").last_accessed
        assert new_accessed >= original_accessed

    def test_set_pinned(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.set_pinned("m1", True)
        got = db.get_memory("m1")
        assert got.pinned is True
        db.set_pinned("m1", False)
        got = db.get_memory("m1")
        assert got.pinned is False

    def test_count_memories(self, db, make_memory):
        assert db.count_memories() == 0
        db.insert_memory(make_memory(id="m1"))
        db.insert_memory(make_memory(id="m2"))
        assert db.count_memories() == 2

    def test_count_by_gate(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", gate=Gate.epistemic))
        db.insert_memory(make_memory(id="m2", gate=Gate.epistemic))
        db.insert_memory(make_memory(id="m3", gate=Gate.relational))
        counts = db.count_by_gate()
        assert counts["epistemic"] == 2
        assert counts["relational"] == 1

    def test_update_confidence(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", confidence=0.9))
        db.update_confidence("m1", 0.5)
        assert db.get_memory("m1").confidence == pytest.approx(0.5)


# ===========================================================================
# List / Filter
# ===========================================================================


class TestListAndFilter:
    def test_list_respects_limit_and_offset(self, db, make_memory):
        for i in range(5):
            db.insert_memory(make_memory(id=f"m{i}", content=f"c{i}"))
        page1 = db.list_memories(limit=2, offset=0)
        page2 = db.list_memories(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids = {m.id for m in page1} | {m.id for m in page2}
        assert len(ids) == 4  # no overlap

    def test_list_filter_by_gate(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", gate=Gate.epistemic))
        db.insert_memory(make_memory(id="m2", gate=Gate.relational))
        results = db.list_memories(gate="epistemic")
        assert len(results) == 1
        assert results[0].id == "m1"

    def test_list_filter_by_person(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", person="Alice"))
        db.insert_memory(make_memory(id="m2", person="Bob"))
        results = db.list_memories(person="Alice")
        assert len(results) == 1
        assert results[0].person == "Alice"

    def test_list_filter_by_project(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", project="Alpha"))
        db.insert_memory(make_memory(id="m2", project="Beta"))
        results = db.list_memories(project="Alpha")
        assert len(results) == 1
        assert results[0].project == "Alpha"

    def test_list_combined_filters(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", gate=Gate.epistemic, person="Alice", project="Alpha"))
        db.insert_memory(make_memory(id="m2", gate=Gate.epistemic, person="Alice", project="Beta"))
        db.insert_memory(make_memory(id="m3", gate=Gate.relational, person="Alice", project="Alpha"))
        results = db.list_memories(gate="epistemic", person="Alice", project="Alpha")
        assert len(results) == 1
        assert results[0].id == "m1"

    def test_list_empty_result(self, db):
        results = db.list_memories(gate="relational")
        assert results == []


# ===========================================================================
# Full-text search
# ===========================================================================


class TestFTS:
    def test_search_finds_matching_content(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="quantum computing is fascinating"))
        db.insert_memory(make_memory(id="m2", content="cooking pasta requires boiling water"))
        results = db.search_fts("quantum")
        assert len(results) == 1
        assert results[0].id == "m1"

    def test_search_respects_limit(self, db, make_memory):
        for i in range(10):
            db.insert_memory(make_memory(id=f"m{i}", content=f"repeated keyword alpha item {i}"))
        results = db.search_fts("alpha", limit=3)
        assert len(results) == 3

    def test_search_no_match(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="hello world"))
        results = db.search_fts("xyznonexistent")
        assert results == []

    def test_search_respects_user_id(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="secret formula"), user_id="alice")
        db.insert_memory(make_memory(id="m2", content="secret formula copy"), user_id="bob")
        results = db.search_fts("secret", user_id="alice")
        assert len(results) == 1
        assert results[0].id == "m1"

    def test_fts_reflects_updated_content(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="old keyword banana"))
        db.update_memory("m1", content="new keyword cherry")
        results = db.search_fts("cherry")
        assert len(results) == 1
        assert results[0].id == "m1"
        # old keyword should no longer match
        results_old = db.search_fts("banana")
        assert len(results_old) == 0

    def test_fts_handles_bad_query_gracefully(self, db):
        """Invalid FTS syntax should return empty, not raise."""
        results = db.search_fts("AND OR NOT")
        assert results == []


# ===========================================================================
# Sensitivity
# ===========================================================================


class TestSensitivity:
    def test_update_and_read_sensitivity(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.update_sensitivity("m1", "sensitive", "contains PII")
        got = db.get_memory("m1")
        assert got.sensitivity == "sensitive"
        assert got.sensitivity_reason == "contains PII"

    def test_list_unclassified(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))  # no sensitivity set
        db.insert_memory(make_memory(id="m2"))
        db.update_sensitivity("m2", "sensitive", "reason")
        unclassified = db.list_memories_by_sensitivity(None)
        assert len(unclassified) == 1
        assert unclassified[0].id == "m1"

    def test_list_unclassified_string(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        results = db.list_memories_by_sensitivity("unclassified")
        assert len(results) == 1

    def test_list_flagged_combines_sensitive_and_critical(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.insert_memory(make_memory(id="m2"))
        db.insert_memory(make_memory(id="m3"))
        db.insert_memory(make_memory(id="m4"))
        db.update_sensitivity("m1", "sensitive", "r1")
        db.update_sensitivity("m2", "critical", "r2")
        db.update_sensitivity("m3", "low", "r3")
        # m4 has no sensitivity
        flagged = db.list_memories_by_sensitivity("flagged")
        ids = {m.id for m in flagged}
        assert ids == {"m1", "m2"}

    def test_list_specific_sensitivity_level(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.insert_memory(make_memory(id="m2"))
        db.update_sensitivity("m1", "low", "just info")
        db.update_sensitivity("m2", "sensitive", "pii")
        results = db.list_memories_by_sensitivity("low")
        assert len(results) == 1
        assert results[0].id == "m1"

    def test_count_by_sensitivity(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"))
        db.insert_memory(make_memory(id="m2"))
        db.insert_memory(make_memory(id="m3"))
        db.update_sensitivity("m1", "sensitive", "r")
        db.update_sensitivity("m2", "sensitive", "r")
        counts = db.count_by_sensitivity()
        assert counts.get("sensitive") == 2
        assert counts.get("unclassified") == 1

    def test_list_by_sensitivity_respects_user_id(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"), user_id="alice")
        db.insert_memory(make_memory(id="m2"), user_id="bob")
        db.update_sensitivity("m1", "sensitive", "r", user_id="alice")
        db.update_sensitivity("m2", "sensitive", "r", user_id="bob")
        results = db.list_memories_by_sensitivity("sensitive", user_id="alice")
        assert len(results) == 1
        assert results[0].id == "m1"


# ===========================================================================
# Journal
# ===========================================================================


class TestJournal:
    def _make_entry(self, content="journal entry", person=None, project=None,
                    gate=Gate.epistemic, ts=None):
        return JournalEntry(
            timestamp=ts or datetime.now(timezone.utc),
            gate=gate,
            content=content,
            person=person,
            project=project,
        )

    def test_insert_and_recent(self, db):
        db.insert_journal(self._make_entry(content="today happened"))
        rows = db.recent_journal(days=1)
        assert len(rows) == 1
        assert rows[0]["content"] == "today happened"

    def test_journal_by_date(self, db):
        ts = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        db.insert_journal(self._make_entry(content="june entry", ts=ts))
        db.insert_journal(self._make_entry(content="today entry"))
        rows = db.journal_by_date("2025-06-15")
        assert len(rows) == 1
        assert rows[0]["content"] == "june entry"

    def test_stale_journal_dates(self, db):
        old_ts = datetime.now(timezone.utc) - timedelta(days=30)
        db.insert_journal(self._make_entry(content="old", ts=old_ts))
        db.insert_journal(self._make_entry(content="recent"))
        stale = db.stale_journal_dates(max_age_days=14)
        assert len(stale) == 1
        assert stale[0] == old_ts.strftime("%Y-%m-%d")

    def test_archive_journal_date_deletes(self, db):
        ts = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        db.insert_journal(self._make_entry(content="old entry", ts=ts))
        db.archive_journal_date("2025-01-01")
        rows = db.journal_by_date("2025-01-01")
        assert rows == []

    def test_journal_user_isolation(self, db):
        entry = self._make_entry(content="private")
        db.insert_journal(entry, user_id="alice")
        assert len(db.recent_journal(user_id="alice")) == 1
        assert len(db.recent_journal(user_id="bob")) == 0

    def test_latest_checkpoint_returns_none_when_empty(self, db):
        assert db.latest_checkpoint(user_id="test-user") is None

    def test_latest_checkpoint_returns_most_recent(self, db):
        # Insert two checkpoints
        db.conn.execute(
            "INSERT INTO journal "
            "(date, timestamp, gate, content, person, project, user_id) "
            "VALUES (?, ?, 'checkpoint', ?, NULL, NULL, ?)",
            ("2026-02-14", "2026-02-14T10:00:00+00:00", "Old checkpoint", "test-user"),
        )
        db.conn.execute(
            "INSERT INTO journal "
            "(date, timestamp, gate, content, person, project, user_id) "
            "VALUES (?, ?, 'checkpoint', ?, NULL, NULL, ?)",
            ("2026-02-15", "2026-02-15T12:00:00+00:00", "Latest checkpoint", "test-user"),
        )
        db.conn.commit()

        result = db.latest_checkpoint(user_id="test-user")
        assert result is not None
        assert result["content"] == "Latest checkpoint"
        assert result["gate"] == "checkpoint"

    def test_latest_checkpoint_user_isolation(self, db):
        db.conn.execute(
            "INSERT INTO journal "
            "(date, timestamp, gate, content, person, project, user_id) "
            "VALUES (?, ?, 'checkpoint', ?, NULL, NULL, ?)",
            ("2026-02-15", "2026-02-15T12:00:00+00:00", "Alice checkpoint", "alice"),
        )
        db.conn.commit()

        assert db.latest_checkpoint(user_id="alice") is not None
        assert db.latest_checkpoint(user_id="bob") is None


# ===========================================================================
# Identity
# ===========================================================================


class TestIdentity:
    def test_set_and_get_identity(self, db):
        card = IdentityCard(
            person="Thierry",
            project="CMK",
            content="I am the developer",
            last_updated=datetime.now(timezone.utc),
        )
        db.set_identity(card)
        got = db.get_identity()
        assert got is not None
        assert got.person == "Thierry"
        assert got.content == "I am the developer"

    def test_get_identity_returns_none_when_empty(self, db):
        assert db.get_identity() is None

    def test_set_identity_upserts(self, db):
        card1 = IdentityCard(
            person="A", project="P", content="first",
            last_updated=datetime.now(timezone.utc),
        )
        card2 = IdentityCard(
            person="B", project="Q", content="second",
            last_updated=datetime.now(timezone.utc),
        )
        db.set_identity(card1)
        db.set_identity(card2)
        got = db.get_identity()
        assert got.content == "second"

    def test_identity_user_isolation(self, db):
        card = IdentityCard(
            person="A", project=None, content="alice's card",
            last_updated=datetime.now(timezone.utc),
        )
        db.set_identity(card, user_id="alice")
        assert db.get_identity(user_id="alice") is not None
        assert db.get_identity(user_id="bob") is None


# ===========================================================================
# Graph edges
# ===========================================================================


class TestEdges:
    def test_add_edge_and_find_related(self, db, make_memory):
        db.insert_memory(make_memory(id="A", content="memory A"))
        db.insert_memory(make_memory(id="B", content="memory B"))
        db.add_edge("A", "B", "RELATED_TO")
        related = db.find_related("A", depth=1)
        assert len(related) == 1
        assert related[0]["id"] == "B"
        assert related[0]["relation"] == "RELATED_TO"

    def test_find_related_depth_2(self, db, make_memory):
        db.insert_memory(make_memory(id="A", content="A"))
        db.insert_memory(make_memory(id="B", content="B"))
        db.insert_memory(make_memory(id="C", content="C"))
        db.add_edge("A", "B", "RELATED_TO")
        db.add_edge("B", "C", "RELATED_TO")
        related = db.find_related("A", depth=2)
        ids = {r["id"] for r in related}
        assert "B" in ids
        assert "C" in ids

    def test_find_related_no_edges(self, db, make_memory):
        db.insert_memory(make_memory(id="lonely"))
        assert db.find_related("lonely") == []

    def test_edge_is_idempotent(self, db, make_memory):
        db.insert_memory(make_memory(id="A", content="A"))
        db.insert_memory(make_memory(id="B", content="B"))
        db.add_edge("A", "B", "RELATED_TO")
        db.add_edge("A", "B", "RELATED_TO")  # duplicate, should be ignored
        related = db.find_related("A", depth=1)
        assert len(related) == 1

    def test_edge_user_isolation(self, db, make_memory):
        db.insert_memory(make_memory(id="A", content="A"), user_id="alice")
        db.insert_memory(make_memory(id="B", content="B"), user_id="alice")
        db.add_edge("A", "B", "RELATED_TO", user_id="alice")
        assert len(db.find_related("A", depth=1, user_id="alice")) == 1
        assert len(db.find_related("A", depth=1, user_id="bob")) == 0


# ===========================================================================
# Auto-link
# ===========================================================================


class TestAutoLink:
    def test_auto_link_by_person(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", person="Alice"))
        db.insert_memory(make_memory(id="m2", person="Alice"))
        db.auto_link("m1", person="Alice", project=None)
        related = db.find_related("m1", depth=1)
        assert len(related) == 1
        assert related[0]["id"] == "m2"

    def test_auto_link_by_project(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", project="Alpha"))
        db.insert_memory(make_memory(id="m2", project="Alpha"))
        db.auto_link("m1", person=None, project="Alpha")
        related = db.find_related("m1", depth=1)
        assert len(related) == 1
        assert related[0]["id"] == "m2"

    def test_auto_link_both(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", person="Alice", project="Alpha"))
        db.insert_memory(make_memory(id="m2", person="Alice", project="Beta"))
        db.insert_memory(make_memory(id="m3", person="Bob", project="Alpha"))
        db.auto_link("m1", person="Alice", project="Alpha")
        related = db.find_related("m1", depth=1)
        ids = {r["id"] for r in related}
        assert "m2" in ids  # same person
        assert "m3" in ids  # same project

    def test_auto_link_no_matches(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", person="Solo"))
        db.auto_link("m1", person="Solo", project=None)
        assert db.find_related("m1", depth=1) == []


# ===========================================================================
# Onboarding
# ===========================================================================


class TestOnboarding:
    def test_set_and_get_onboarding(self, db):
        state = OnboardingState(step=2, person="Me", project="Proj", style="casual")
        db.set_onboarding(state)
        got = db.get_onboarding()
        assert got is not None
        assert got.step == 2
        assert got.style == "casual"

    def test_get_onboarding_returns_none_when_empty(self, db):
        assert db.get_onboarding() is None

    def test_delete_onboarding(self, db):
        db.set_onboarding(OnboardingState(step=1))
        db.delete_onboarding()
        assert db.get_onboarding() is None

    def test_onboarding_upserts(self, db):
        db.set_onboarding(OnboardingState(step=1))
        db.set_onboarding(OnboardingState(step=3))
        assert db.get_onboarding().step == 3


# ===========================================================================
# Archive
# ===========================================================================


class TestArchive:
    def test_archive_memory(self, db):
        db.archive_memory("m1", "epistemic", "old content", "stale")
        row = db.conn.execute(
            "SELECT * FROM archive WHERE id = ?", ("m1",)
        ).fetchone()
        assert row is not None
        assert row["reason"] == "stale"
        assert row["original_gate"] == "epistemic"

    def test_archive_upserts(self, db):
        db.archive_memory("m1", "epistemic", "v1", "reason1")
        db.archive_memory("m1", "relational", "v2", "reason2")
        row = db.conn.execute(
            "SELECT * FROM archive WHERE id = ?", ("m1",)
        ).fetchone()
        assert row["content"] == "v2"
        assert row["original_gate"] == "relational"


# ===========================================================================
# Users
# ===========================================================================


class TestUsers:
    def test_upsert_and_get_user(self, db):
        db.upsert_user("u1", email="u1@example.com", name="User One")
        user = db.get_user("u1")
        assert user is not None
        assert user["email"] == "u1@example.com"
        assert user["name"] == "User One"
        assert user["plan"] == "free"

    def test_get_user_nonexistent(self, db):
        assert db.get_user("ghost") is None

    def test_upsert_updates_last_seen(self, db):
        db.upsert_user("u1", email="a@b.com")
        first = db.get_user("u1")
        db.upsert_user("u1", name="Updated")
        second = db.get_user("u1")
        assert second["name"] == "Updated"
        assert second["last_seen"] >= first["last_seen"]

    def test_upsert_preserves_existing_email(self, db):
        db.upsert_user("u1", email="original@test.com")
        db.upsert_user("u1")  # no email passed
        user = db.get_user("u1")
        assert user["email"] == "original@test.com"


# ===========================================================================
# API Keys
# ===========================================================================


class TestAPIKeys:
    def test_insert_and_get_by_hash(self, db):
        db.insert_api_key("k1", "u1", "hash123", "cmk_", name="test key")
        got = db.get_api_key_by_hash("hash123")
        assert got is not None
        assert got["id"] == "k1"
        assert got["user_id"] == "u1"
        assert got["name"] == "test key"

    def test_get_by_hash_nonexistent(self, db):
        assert db.get_api_key_by_hash("no_such_hash") is None

    def test_get_by_hash_updates_last_used(self, db):
        db.insert_api_key("k1", "u1", "hash1", "cmk_")
        # First call updates the DB but returns the pre-update row
        db.get_api_key_by_hash("hash1")
        # Second call returns the row that was updated by the first call
        second = db.get_api_key_by_hash("hash1")
        assert second["last_used"] is not None

    def test_list_api_keys(self, db):
        db.insert_api_key("k1", "u1", "h1", "cmk_", name="key1")
        db.insert_api_key("k2", "u1", "h2", "cmk_", name="key2")
        db.insert_api_key("k3", "u2", "h3", "cmk_", name="other")
        keys = db.list_api_keys("u1")
        assert len(keys) == 2
        names = {k["name"] for k in keys}
        assert names == {"key1", "key2"}

    def test_revoke_api_key(self, db):
        db.insert_api_key("k1", "u1", "hash1", "cmk_")
        assert db.revoke_api_key("k1", "u1") is True
        # Revoked key should not be returned
        assert db.get_api_key_by_hash("hash1") is None

    def test_revoke_nonexistent_key(self, db):
        assert db.revoke_api_key("ghost", "u1") is False

    def test_revoke_wrong_user(self, db):
        db.insert_api_key("k1", "u1", "hash1", "cmk_")
        assert db.revoke_api_key("k1", "u2") is False
        # Key should still work
        assert db.get_api_key_by_hash("hash1") is not None


# ===========================================================================
# Rules
# ===========================================================================


class TestRules:
    def test_insert_and_get_rule(self, db):
        db.insert_rule("r1", "local", "global", "never swear", "enforce")
        rule = db.get_rule("r1")
        assert rule is not None
        assert rule["condition"] == "never swear"
        assert rule["enforcement"] == "enforce"

    def test_get_rule_nonexistent(self, db):
        assert db.get_rule("ghost") is None

    def test_list_rules(self, db):
        db.insert_rule("r1", "local", "global", "rule1")
        db.insert_rule("r2", "local", "project", "rule2")
        rules = db.list_rules()
        assert len(rules) == 2

    def test_list_rules_user_isolation(self, db):
        db.insert_rule("r1", "alice", "global", "alice rule")
        db.insert_rule("r2", "bob", "global", "bob rule")
        assert len(db.list_rules(user_id="alice")) == 1
        assert len(db.list_rules(user_id="bob")) == 1

    def test_update_rule(self, db):
        db.insert_rule("r1", "local", "global", "old condition")
        result = db.update_rule("r1", condition="new condition", enforcement="block")
        assert result is True
        rule = db.get_rule("r1")
        assert rule["condition"] == "new condition"
        assert rule["enforcement"] == "block"

    def test_update_rule_no_valid_keys(self, db):
        db.insert_rule("r1", "local", "global", "cond")
        assert db.update_rule("r1", bogus="val") is False

    def test_update_rule_nonexistent(self, db):
        assert db.update_rule("ghost", condition="x") is False

    def test_delete_rule(self, db):
        db.insert_rule("r1", "local", "global", "cond")
        assert db.delete_rule("r1") is True
        assert db.get_rule("r1") is None

    def test_delete_rule_nonexistent(self, db):
        assert db.delete_rule("ghost") is False

    def test_touch_rule(self, db):
        db.insert_rule("r1", "local", "global", "cond")
        rule_before = db.get_rule("r1")
        assert rule_before["last_triggered"] is None
        db.touch_rule("r1")
        rule_after = db.get_rule("r1")
        assert rule_after["last_triggered"] is not None


# ===========================================================================
# User data migration
# ===========================================================================


class TestUserDataMigration:
    def test_count_user_data_empty(self, db):
        counts = db.count_user_data("nobody")
        assert counts["memories"] == 0
        assert counts["journal"] == 0
        assert counts["identity"] == 0
        assert counts["onboarding"] == 0

    def test_count_user_data(self, db, make_memory):
        uid = "testuser"
        db.insert_memory(make_memory(id="m1"), user_id=uid)
        db.insert_memory(make_memory(id="m2"), user_id=uid)
        db.insert_journal(
            JournalEntry(
                timestamp=datetime.now(timezone.utc),
                gate=Gate.epistemic,
                content="journal",
            ),
            user_id=uid,
        )
        db.set_identity(
            IdentityCard(
                content="identity", last_updated=datetime.now(timezone.utc)
            ),
            user_id=uid,
        )
        counts = db.count_user_data(uid)
        assert counts["memories"] == 2
        assert counts["journal"] == 1
        assert counts["identity"] == 1

    def test_migrate_user_data_moves_records(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"), user_id="old")
        db.insert_memory(make_memory(id="m2"), user_id="old")
        db.insert_journal(
            JournalEntry(
                timestamp=datetime.now(timezone.utc),
                gate=Gate.epistemic,
                content="j",
            ),
            user_id="old",
        )
        db.set_identity(
            IdentityCard(content="id", last_updated=datetime.now(timezone.utc)),
            user_id="old",
        )
        db.set_onboarding(OnboardingState(step=1), user_id="old")

        result = db.migrate_user_data("old", "new")
        assert result["memories"] == 2
        assert result["journal"] == 1
        assert result["identity"] == 1
        assert result["onboarding"] == 1

        # Old user should have nothing
        assert db.count_user_data("old")["memories"] == 0
        # New user should have everything
        assert db.count_user_data("new")["memories"] == 2
        assert db.get_identity(user_id="new") is not None

    def test_migrate_user_data_skips_identity_if_target_exists(self, db):
        db.set_identity(
            IdentityCard(content="source", last_updated=datetime.now(timezone.utc)),
            user_id="old",
        )
        db.set_identity(
            IdentityCard(content="target", last_updated=datetime.now(timezone.utc)),
            user_id="new",
        )
        result = db.migrate_user_data("old", "new")
        assert result["identity"] == 0
        # Target identity should be preserved
        assert db.get_identity(user_id="new").content == "target"
        # Source should be deleted
        assert db.get_identity(user_id="old") is None

    def test_migrate_user_data_skips_onboarding_if_target_exists(self, db):
        db.set_onboarding(OnboardingState(step=1), user_id="old")
        db.set_onboarding(OnboardingState(step=5), user_id="new")
        result = db.migrate_user_data("old", "new")
        assert result["onboarding"] == 0
        assert db.get_onboarding(user_id="new").step == 5


# ===========================================================================
# User isolation (cross-cutting)
# ===========================================================================


class TestUserIsolation:
    def test_memory_user_isolation(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"), user_id="alice")
        db.insert_memory(make_memory(id="m2"), user_id="bob")
        assert db.get_memory("m1", user_id="alice") is not None
        assert db.get_memory("m1", user_id="bob") is None
        assert db.count_memories(user_id="alice") == 1
        assert db.count_memories(user_id="bob") == 1

    def test_touch_only_affects_own_user(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", access_count=1), user_id="alice")
        db.touch_memory("m1", user_id="bob")  # wrong user
        got = db.get_memory("m1", user_id="alice")
        assert got.access_count == 1  # unchanged

    def test_delete_only_affects_own_user(self, db, make_memory):
        db.insert_memory(make_memory(id="m1"), user_id="alice")
        result = db.delete_memory("m1", user_id="bob")
        assert result is None
        assert db.get_memory("m1", user_id="alice") is not None

    def test_update_memory_only_affects_own_user(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", content="original"), user_id="alice")
        db.update_memory("m1", user_id="bob", content="hacked")
        assert db.get_memory("m1", user_id="alice").content == "original"

    def test_count_by_gate_user_isolation(self, db, make_memory):
        db.insert_memory(make_memory(id="m1", gate=Gate.epistemic), user_id="alice")
        db.insert_memory(make_memory(id="m2", gate=Gate.epistemic), user_id="bob")
        counts_alice = db.count_by_gate(user_id="alice")
        assert counts_alice.get("epistemic", 0) == 1

    def test_rules_user_isolation(self, db):
        db.insert_rule("r1", "alice", "global", "alice rule")
        assert db.get_rule("r1", user_id="alice") is not None
        assert db.get_rule("r1", user_id="bob") is None

    def test_archive_user_isolation(self, db):
        db.archive_memory("a1", "epistemic", "data", "reason", user_id="alice")
        row = db.conn.execute(
            "SELECT * FROM archive WHERE id = ? AND user_id = ?",
            ("a1", "alice"),
        ).fetchone()
        assert row is not None
        row_bob = db.conn.execute(
            "SELECT * FROM archive WHERE id = ? AND user_id = ?",
            ("a1", "bob"),
        ).fetchone()
        assert row_bob is None


# ===========================================================================
# Edge cases and miscellaneous
# ===========================================================================


class TestEdgeCases:
    def test_memory_with_all_gates(self, db, make_memory):
        for gate in Gate:
            mid = f"m_{gate.value}"
            db.insert_memory(make_memory(id=mid, gate=gate))
            got = db.get_memory(mid)
            assert got.gate == gate
            assert got.decay_class == DecayClass.from_gate(gate)

    def test_memory_with_long_content(self, db, make_memory):
        long_content = "x" * 100_000
        db.insert_memory(make_memory(id="long", content=long_content))
        got = db.get_memory("long")
        assert len(got.content) == 100_000

    def test_empty_list_memories(self, db):
        assert db.list_memories() == []

    def test_list_memories_default_user(self, db, make_memory):
        """Memories inserted with default user_id='local' are listed by default."""
        db.insert_memory(make_memory(id="m1"))
        results = db.list_memories()
        assert len(results) == 1

    def test_find_related_with_no_memories(self, db):
        """find_related on nonexistent memory returns empty list."""
        assert db.find_related("nonexistent") == []

    def test_stale_journal_no_stale(self, db):
        """No stale dates when journal is recent."""
        db.insert_journal(
            JournalEntry(
                timestamp=datetime.now(timezone.utc),
                gate=Gate.epistemic,
                content="fresh",
            ),
        )
        assert db.stale_journal_dates(max_age_days=14) == []

    def test_sensitivity_limit_and_offset(self, db, make_memory):
        for i in range(5):
            db.insert_memory(make_memory(id=f"m{i}"))
        results = db.list_memories_by_sensitivity(None, limit=2, offset=0)
        assert len(results) == 2
        results2 = db.list_memories_by_sensitivity(None, limit=2, offset=2)
        assert len(results2) == 2

    def test_set_pinned_adds_column_dynamically(self, tmp_store_path):
        """set_pinned handles ALTER TABLE gracefully even on fresh db."""
        from claude_memory_kit.store.sqlite import SqliteStore
        store = SqliteStore(tmp_store_path)
        store.migrate()
        from claude_memory_kit.types import Memory, Gate, DecayClass
        now = datetime.now(timezone.utc)
        mem = Memory(
            id="pin_test", created=now, gate=Gate.epistemic,
            last_accessed=now, access_count=1,
            decay_class=DecayClass.moderate, content="pin me",
        )
        store.insert_memory(mem)
        store.set_pinned("pin_test", True)
        got = store.get_memory("pin_test")
        assert got.pinned is True

    def test_recent_journal_respects_limit(self, db):
        for i in range(50):
            db.insert_journal(
                JournalEntry(
                    timestamp=datetime.now(timezone.utc),
                    gate=Gate.epistemic,
                    content=f"entry {i}",
                ),
            )
        # days=1 means limit = 1*20 = 20
        rows = db.recent_journal(days=1)
        assert len(rows) <= 20
