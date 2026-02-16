"""Tests for QdrantStore (cloud-only store backed by Qdrant payloads)."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, MatchValue

from claude_memory_kit.store.qdrant_store import QdrantStore, _stable_id, _memory_from_payload
from claude_memory_kit.types import DecayClass, Gate, IdentityCard, JournalEntry, Memory


@pytest.fixture
def store():
    """Create a QdrantStore with an in-memory Qdrant client."""
    with patch("claude_memory_kit.store.qdrant_store.get_qdrant_config") as mock_cfg:
        mock_cfg.return_value = {"mode": "local"}
        qs = object.__new__(QdrantStore)
        qs._disabled = False
        qs._cloud = False
        qs._jina_key = ""
        qs._fastembed_dense = None
        qs._fastembed_sparse = None
        qs.client = QdrantClient(":memory:")
        qs.ensure_collection()
        yield qs


def _make_memory(
    mem_id: str = "mem_test_001",
    content: str = "test memory content",
    gate: Gate = Gate.epistemic,
    person: str | None = None,
    project: str | None = None,
    pinned: bool = False,
    sensitivity: str | None = None,
) -> Memory:
    now = datetime.now(timezone.utc)
    return Memory(
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
        pinned=pinned,
        sensitivity=sensitivity,
    )


class TestStableId:
    def test_deterministic(self):
        assert _stable_id("mem_123") == _stable_id("mem_123")

    def test_different_inputs(self):
        assert _stable_id("mem_a") != _stable_id("mem_b")


class TestMemoryFromPayload:
    def test_round_trip(self):
        now = time.time()
        payload = {
            "memory_id": "mem_001",
            "content": "hello world",
            "gate": "epistemic",
            "person": "Alice",
            "project": "cmk",
            "confidence": 0.85,
            "created": now,
            "last_accessed": now,
            "access_count": 3,
            "decay_class": "moderate",
            "pinned": True,
            "sensitivity": "safe",
            "sensitivity_reason": "no PII",
        }
        mem = _memory_from_payload(payload)
        assert mem.id == "mem_001"
        assert mem.content == "hello world"
        assert mem.gate == Gate.epistemic
        assert mem.person == "Alice"
        assert mem.project == "cmk"
        assert mem.confidence == 0.85
        assert mem.access_count == 3
        assert mem.pinned is True
        assert mem.sensitivity == "safe"

    def test_defaults(self):
        payload = {"memory_id": "x", "content": "y"}
        mem = _memory_from_payload(payload)
        assert mem.confidence == 0.9
        assert mem.access_count == 1
        assert mem.pinned is False
        assert mem.sensitivity is None


class TestInsertAndGetMemory:
    def test_insert_and_get(self, store: QdrantStore):
        mem = _make_memory(content="qdrant is great")
        store.insert_memory(mem, user_id="user1")

        result = store.get_memory(mem.id, user_id="user1")
        assert result is not None
        assert result.id == mem.id
        assert result.content == "qdrant is great"
        assert result.gate == Gate.epistemic

    def test_get_nonexistent(self, store: QdrantStore):
        assert store.get_memory("nonexistent", user_id="user1") is None

    def test_user_isolation(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="user_a")
        assert store.get_memory(mem.id, user_id="user_b") is None


class TestDeleteMemory:
    def test_delete_returns_memory(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="u1")

        deleted = store.delete_memory(mem.id, user_id="u1")
        assert deleted is not None
        assert deleted.id == mem.id

        assert store.get_memory(mem.id, user_id="u1") is None

    def test_delete_nonexistent(self, store: QdrantStore):
        assert store.delete_memory("nope", user_id="u1") is None


class TestListMemories:
    def test_list_basic(self, store: QdrantStore):
        for i in range(3):
            mem = _make_memory(mem_id=f"mem_{i}", content=f"content {i}")
            store.insert_memory(mem, user_id="u1")

        results = store.list_memories(user_id="u1")
        assert len(results) == 3

    def test_filter_by_gate(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", gate=Gate.epistemic), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2", gate=Gate.relational), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m3", gate=Gate.epistemic), user_id="u1")

        results = store.list_memories(user_id="u1", gate="epistemic")
        assert len(results) == 2

    def test_filter_by_person(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", person="Alice"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2", person="Bob"), user_id="u1")

        results = store.list_memories(user_id="u1", person="Alice")
        assert len(results) == 1
        assert results[0].person == "Alice"

    def test_limit_and_offset(self, store: QdrantStore):
        for i in range(5):
            store.insert_memory(_make_memory(mem_id=f"mem_{i}"), user_id="u1")

        page1 = store.list_memories(limit=2, offset=0, user_id="u1")
        assert len(page1) == 2

        page2 = store.list_memories(limit=2, offset=2, user_id="u1")
        assert len(page2) == 2


class TestTouchMemory:
    def test_increments_access_count(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="u1")

        store.touch_memory(mem.id, user_id="u1")
        result = store.get_memory(mem.id, user_id="u1")
        assert result.access_count == 2

    def test_touch_nonexistent(self, store: QdrantStore):
        store.touch_memory("nope", user_id="u1")  # should not raise


class TestUpdateMemory:
    def test_update_content(self, store: QdrantStore):
        mem = _make_memory(content="old content")
        store.insert_memory(mem, user_id="u1")

        store.update_memory(mem.id, user_id="u1", content="new content")
        result = store.get_memory(mem.id, user_id="u1")
        assert result.content == "new content"

    def test_update_gate(self, store: QdrantStore):
        mem = _make_memory(gate=Gate.epistemic)
        store.insert_memory(mem, user_id="u1")

        store.update_memory(mem.id, user_id="u1", gate="relational")
        result = store.get_memory(mem.id, user_id="u1")
        assert result.gate == Gate.relational


class TestSetPinned:
    def test_pin_and_unpin(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="u1")

        store.set_pinned(mem.id, True, user_id="u1")
        assert store.get_memory(mem.id, user_id="u1").pinned is True

        store.set_pinned(mem.id, False, user_id="u1")
        assert store.get_memory(mem.id, user_id="u1").pinned is False


class TestCountMemories:
    def test_count(self, store: QdrantStore):
        assert store.count_memories(user_id="u1") == 0
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")
        assert store.count_memories(user_id="u1") == 2

    def test_count_ignores_other_users(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u2")
        assert store.count_memories(user_id="u1") == 1


class TestCountByGate:
    def test_count_by_gate(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", gate=Gate.epistemic), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2", gate=Gate.epistemic), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m3", gate=Gate.relational), user_id="u1")

        counts = store.count_by_gate(user_id="u1")
        assert counts.get("epistemic") == 2
        assert counts.get("relational") == 1


class TestSensitivity:
    def test_update_and_filter(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="u1")

        store.update_sensitivity(mem.id, "sensitive", "contains PII", user_id="u1")
        result = store.get_memory(mem.id, user_id="u1")
        assert result.sensitivity == "sensitive"

    def test_list_by_sensitivity(self, store: QdrantStore):
        m1 = _make_memory(mem_id="m1", sensitivity="safe")
        m2 = _make_memory(mem_id="m2", sensitivity="sensitive")
        store.insert_memory(m1, user_id="u1")
        store.insert_memory(m2, user_id="u1")
        store.update_sensitivity("m2", "sensitive", "PII", user_id="u1")

        results = store.list_memories_by_sensitivity("sensitive", user_id="u1")
        assert len(results) == 1

    def test_count_by_sensitivity(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.update_sensitivity("m1", "safe", None, user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")
        store.update_sensitivity("m2", "critical", "passwords", user_id="u1")

        counts = store.count_by_sensitivity(user_id="u1")
        assert counts.get("safe") == 1
        assert counts.get("critical") == 1


class TestUpdateConfidence:
    def test_update(self, store: QdrantStore):
        mem = _make_memory()
        store.insert_memory(mem, user_id="u1")

        store.update_confidence(mem.id, 0.3, user_id="u1")
        result = store.get_memory(mem.id, user_id="u1")
        assert result.confidence == 0.3


class TestSearchText:
    def test_basic_text_search(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", content="python async programming"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2", content="rust ownership model"), user_id="u1")

        results = store.search_text("python", user_id="u1")
        assert len(results) >= 1
        assert any(mid == "m1" for mid, _ in results)

    def test_search_fts_returns_memories(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", content="vector database qdrant"), user_id="u1")

        results = store.search_fts("qdrant", user_id="u1")
        assert len(results) >= 1
        assert results[0].id == "m1"


class TestFindRecentInContext:
    def test_finds_matching_memory(self, store: QdrantStore):
        mem = _make_memory(mem_id="m1", person="Alice", project="cmk")
        store.insert_memory(mem, user_id="u1")

        cutoff = "2020-01-01T00:00:00+00:00"
        result = store.find_recent_in_context(
            exclude_id="m_other", cutoff=cutoff,
            person="Alice", project="cmk", user_id="u1",
        )
        assert result == "m1"

    def test_excludes_self(self, store: QdrantStore):
        mem = _make_memory(mem_id="m1", person="Alice")
        store.insert_memory(mem, user_id="u1")

        cutoff = "2020-01-01T00:00:00+00:00"
        result = store.find_recent_in_context(
            exclude_id="m1", cutoff=cutoff,
            person="Alice", project=None, user_id="u1",
        )
        assert result is None


class TestMigrateUserId:
    def test_migrate(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="old_user")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="old_user")

        count = store.migrate_user_id("old_user", "new_user")
        assert count == 2

        assert store.get_memory("m1", user_id="new_user") is not None
        assert store.get_memory("m1", user_id="old_user") is None


class TestDisabledStore:
    def test_disabled_returns_empty(self):
        qs = object.__new__(QdrantStore)
        qs._disabled = True
        qs.client = None

        assert qs.get_memory("x") is None
        assert qs.list_memories() == []
        assert qs.count_memories() == 0
        assert qs.count_by_gate() == {}
        assert qs.search("q") == []
        assert qs.search_text("q") == []
        assert qs.search_fts("q") == []
        assert qs.find_recent_in_context("x", "2020-01-01", None, None) is None
        assert qs.migrate_user_id("a", "b") == 0

        # Journal/identity/rules
        assert qs.recent_journal() == []
        assert qs.journal_by_date("2026-01-01") == []
        assert qs.latest_checkpoint() is None
        assert qs.stale_journal_dates() == []
        assert qs.get_identity() is None
        assert qs.list_rules() == []
        assert qs.get_rule("r1") is None
        assert qs.update_rule("r1") is False
        assert qs.delete_rule("r1") is False

        # These should not raise
        qs.insert_memory(_make_memory())
        qs.touch_memory("x")
        qs.update_memory("x")
        qs.set_pinned("x", True)
        qs.update_sensitivity("x", "safe", None)
        qs.update_confidence("x", 0.5)
        qs.delete("x")
        qs.ensure_collection()
        now = datetime.now(timezone.utc)
        qs.insert_journal(JournalEntry(timestamp=now, gate=Gate.epistemic, content="x"))
        qs.insert_journal_raw("2026-01-01", Gate.digest, "x")
        qs.archive_journal_date("2026-01-01")
        qs.set_identity(IdentityCard(content="x", last_updated=now))
        qs.insert_rule("r1", "u1", "all", "no secrets")
        qs.touch_rule("r1")


# ------------------------------------------------------------------ #
#  Graph edge tests                                                    #
# ------------------------------------------------------------------ #


class TestGraphEdges:
    def test_add_edge(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")

        store.add_edge("m1", "m2", "CONTRADICTS", user_id="u1")

        # Verify edge is in payload
        points = store._scroll_all([
            FieldCondition(key="memory_id", match=MatchValue(value="m1")),
            FieldCondition(key="user_id", match=MatchValue(value="u1")),
        ], limit=1)
        edges = points[0].payload.get("edges", [])
        assert len(edges) == 1
        assert edges[0]["to"] == "m2"
        assert edges[0]["relation"] == "CONTRADICTS"

    def test_add_edge_deduplication(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")

        store.add_edge("m1", "m2", "FOLLOWS", user_id="u1")
        store.add_edge("m1", "m2", "FOLLOWS", user_id="u1")  # duplicate

        points = store._scroll_all([
            FieldCondition(key="memory_id", match=MatchValue(value="m1")),
            FieldCondition(key="user_id", match=MatchValue(value="u1")),
        ], limit=1)
        edges = points[0].payload.get("edges", [])
        assert len(edges) == 1

    def test_add_edge_to_nonexistent_source(self, store: QdrantStore):
        store.add_edge("nope", "m2", "FOLLOWS", user_id="u1")  # should not raise

    def test_find_related_depth_1(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", content="origin"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2", content="neighbor"), user_id="u1")
        store.add_edge("m1", "m2", "CONTRADICTS", user_id="u1")

        related = store.find_related("m1", depth=1, user_id="u1")
        assert len(related) == 1
        assert related[0]["id"] == "m2"
        assert related[0]["relation"] == "CONTRADICTS"
        assert related[0]["depth"] == 1

    def test_find_related_depth_2(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m3"), user_id="u1")

        store.add_edge("m1", "m2", "FOLLOWS", user_id="u1")
        store.add_edge("m2", "m3", "FOLLOWS", user_id="u1")

        related = store.find_related("m1", depth=2, user_id="u1")
        ids = {r["id"] for r in related}
        assert "m2" in ids
        assert "m3" in ids
        assert len(related) == 2

    def test_find_related_no_cycles(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        store.insert_memory(_make_memory(mem_id="m2"), user_id="u1")

        store.add_edge("m1", "m2", "FOLLOWS", user_id="u1")
        store.add_edge("m2", "m1", "FOLLOWS", user_id="u1")  # cycle

        related = store.find_related("m1", depth=2, user_id="u1")
        # m1 is start node, should only find m2 (no revisiting m1)
        assert len(related) == 1
        assert related[0]["id"] == "m2"

    def test_find_related_empty(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1"), user_id="u1")
        related = store.find_related("m1", depth=2, user_id="u1")
        assert related == []

    def test_auto_link_is_noop(self, store: QdrantStore):
        store.insert_memory(_make_memory(mem_id="m1", person="Alice"), user_id="u1")
        store.auto_link("m1", "Alice", None, user_id="u1")
        # auto_link is a no-op, edges should be empty
        points = store._scroll_all([
            FieldCondition(key="memory_id", match=MatchValue(value="m1")),
        ], limit=1)
        assert points[0].payload.get("edges") == []


# ------------------------------------------------------------------ #
#  Journal tests                                                       #
# ------------------------------------------------------------------ #


class TestJournal:
    def test_insert_and_recent(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        entry = JournalEntry(
            timestamp=now, gate=Gate.epistemic,
            content="learned something new", person="Alice",
        )
        store.insert_journal(entry, user_id="u1")

        results = store.recent_journal(days=3, user_id="u1")
        assert len(results) == 1
        assert results[0]["content"] == "learned something new"
        assert results[0]["gate"] == "epistemic"

    def test_journal_by_date(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        entry = JournalEntry(timestamp=now, gate=Gate.behavioral, content="daily note")
        store.insert_journal(entry, user_id="u1")

        results = store.journal_by_date(today, user_id="u1")
        assert len(results) == 1
        assert results[0]["content"] == "daily note"

        results = store.journal_by_date("1999-01-01", user_id="u1")
        assert len(results) == 0

    def test_insert_journal_raw(self, store: QdrantStore):
        store.insert_journal_raw("2026-01-15", Gate.digest, "weekly digest", user_id="u1")

        results = store.journal_by_date("2026-01-15", user_id="u1")
        assert len(results) == 1
        assert results[0]["gate"] == "digest"

    def test_latest_checkpoint(self, store: QdrantStore):
        now = datetime.now(timezone.utc)

        # No checkpoints yet
        assert store.latest_checkpoint(user_id="u1") is None

        # Add a checkpoint
        cp = JournalEntry(timestamp=now, gate=Gate.checkpoint, content="session summary")
        store.insert_journal(cp, user_id="u1")

        result = store.latest_checkpoint(user_id="u1")
        assert result is not None
        assert result["content"] == "session summary"
        assert result["gate"] == "checkpoint"

    def test_stale_journal_dates(self, store: QdrantStore):
        # Insert old entry
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        old_entry = JournalEntry(timestamp=old_time, gate=Gate.epistemic, content="old note")
        store.insert_journal(old_entry, user_id="u1")

        # Insert recent entry
        now = datetime.now(timezone.utc)
        new_entry = JournalEntry(timestamp=now, gate=Gate.epistemic, content="new note")
        store.insert_journal(new_entry, user_id="u1")

        stale = store.stale_journal_dates(max_age_days=14, user_id="u1")
        old_date = old_time.strftime("%Y-%m-%d")
        assert old_date in stale

        today = now.strftime("%Y-%m-%d")
        assert today not in stale

    def test_archive_journal_date(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        entry = JournalEntry(timestamp=now, gate=Gate.epistemic, content="will be archived")
        store.insert_journal(entry, user_id="u1")

        store.archive_journal_date(today, user_id="u1")
        results = store.journal_by_date(today, user_id="u1")
        assert len(results) == 0

    def test_user_isolation(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        entry = JournalEntry(timestamp=now, gate=Gate.epistemic, content="private note")
        store.insert_journal(entry, user_id="u1")

        assert len(store.recent_journal(user_id="u1")) == 1
        assert len(store.recent_journal(user_id="u2")) == 0


# ------------------------------------------------------------------ #
#  Identity tests                                                      #
# ------------------------------------------------------------------ #


class TestIdentity:
    def test_set_and_get(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        card = IdentityCard(
            person="Thierry", project="cmk",
            content="I work with Thierry on CMK.",
            last_updated=now,
        )
        store.set_identity(card, user_id="u1")

        result = store.get_identity(user_id="u1")
        assert result is not None
        assert result.person == "Thierry"
        assert result.project == "cmk"
        assert result.content == "I work with Thierry on CMK."

    def test_get_nonexistent(self, store: QdrantStore):
        assert store.get_identity(user_id="nobody") is None

    def test_overwrite(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        card1 = IdentityCard(person="A", content="first", last_updated=now)
        store.set_identity(card1, user_id="u1")

        card2 = IdentityCard(person="B", content="second", last_updated=now)
        store.set_identity(card2, user_id="u1")

        result = store.get_identity(user_id="u1")
        assert result.person == "B"
        assert result.content == "second"

    def test_user_isolation(self, store: QdrantStore):
        now = datetime.now(timezone.utc)
        store.set_identity(
            IdentityCard(person="A", content="user1 card", last_updated=now),
            user_id="u1",
        )
        store.set_identity(
            IdentityCard(person="B", content="user2 card", last_updated=now),
            user_id="u2",
        )
        assert store.get_identity(user_id="u1").person == "A"
        assert store.get_identity(user_id="u2").person == "B"


# ------------------------------------------------------------------ #
#  Rule tests                                                          #
# ------------------------------------------------------------------ #


class TestRules:
    def test_insert_and_get(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "no secrets in logs")

        rule = store.get_rule("r1", user_id="u1")
        assert rule is not None
        assert rule["id"] == "r1"
        assert rule["scope"] == "all"
        assert rule["condition"] == "no secrets in logs"
        assert rule["enforcement"] == "suggest"

    def test_list_rules(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "rule one")
        store.insert_rule("r2", "u1", "api", "rule two")

        rules = store.list_rules(user_id="u1")
        assert len(rules) == 2

    def test_update_rule(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "old condition")

        result = store.update_rule("r1", user_id="u1", condition="new condition")
        assert result is True

        rule = store.get_rule("r1", user_id="u1")
        assert rule["condition"] == "new condition"

    def test_update_rejects_invalid_fields(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "cond")
        assert store.update_rule("r1", user_id="u1", bad_field="x") is False

    def test_update_nonexistent(self, store: QdrantStore):
        assert store.update_rule("nope", user_id="u1", scope="x") is False

    def test_delete_rule(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "cond")

        assert store.delete_rule("r1", user_id="u1") is True
        assert store.get_rule("r1", user_id="u1") is None

    def test_delete_nonexistent(self, store: QdrantStore):
        assert store.delete_rule("nope", user_id="u1") is False

    def test_touch_rule(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "cond")

        rule_before = store.get_rule("r1", user_id="u1")
        assert rule_before["last_triggered"] is None

        store.touch_rule("r1", user_id="u1")
        rule_after = store.get_rule("r1", user_id="u1")
        assert rule_after["last_triggered"] is not None

    def test_user_isolation(self, store: QdrantStore):
        store.insert_rule("r1", "u1", "all", "user1 rule")
        store.insert_rule("r1", "u2", "all", "user2 rule")

        assert store.get_rule("r1", user_id="u1")["condition"] == "user1 rule"
        assert store.get_rule("r1", user_id="u2")["condition"] == "user2 rule"
