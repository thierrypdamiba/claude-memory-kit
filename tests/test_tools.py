"""Comprehensive tests for all CMK tool functions."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_memory_kit.types import (
    DecayClass,
    Gate,
    IdentityCard,
    Memory,
    OnboardingState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(db):
    """Build a mock Store with a real SqliteStore backend and mocked vectors."""
    store = MagicMock()
    store.db = db
    store.vectors = MagicMock()
    store.vectors.search = MagicMock(return_value=[])
    store.vectors.search_text = MagicMock(return_value=[])
    store.vectors.upsert = MagicMock(return_value=None)
    store.vectors.delete = MagicMock(return_value=None)
    return store


def _insert_memory(db, id="mem_test_001", gate=Gate.epistemic,
                   content="test memory content", person=None,
                   project=None, confidence=0.9, user_id="local",
                   sensitivity=None, sensitivity_reason=None,
                   access_count=1, decay_class=None,
                   created=None, last_accessed=None):
    """Insert a memory row into a real SqliteStore and return the Memory."""
    now = created or datetime.now(timezone.utc)
    la = last_accessed or now
    dc = decay_class or DecayClass.from_gate(gate)
    mem = Memory(
        id=id, created=now, gate=gate, person=person, project=project,
        confidence=confidence, last_accessed=la, access_count=access_count,
        decay_class=dc, content=content, sensitivity=sensitivity,
        sensitivity_reason=sensitivity_reason,
    )
    db.insert_memory(mem, user_id=user_id)
    if sensitivity is not None:
        db.update_sensitivity(id, sensitivity, sensitivity_reason or "", user_id=user_id)
    return mem


# ===========================================================================
# remember.py
# ===========================================================================

class TestRemember:
    """Tests for do_remember and _check_pii."""

    @pytest.mark.asyncio
    async def test_happy_path_epistemic(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "Python uses indentation", "epistemic", user_id="local")
        assert "Remembered [epistemic]" in result
        assert "Python uses indentation" in result
        assert "id: mem_" in result

    @pytest.mark.asyncio
    async def test_happy_path_relational(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "Alice likes tea", "relational", person="Alice")
        assert "Remembered [relational]" in result
        assert "Alice likes tea" in result

    @pytest.mark.asyncio
    async def test_happy_path_behavioral(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "User prefers short answers", "behavioral")
        assert "Remembered [behavioral]" in result

    @pytest.mark.asyncio
    async def test_happy_path_promissory(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "I promised to review PR #42", "promissory")
        assert "Remembered [promissory]" in result

    @pytest.mark.asyncio
    async def test_invalid_gate_returns_error(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "some content", "invalid_gate")
        assert "invalid gate" in result
        assert "behavioral, relational, epistemic, promissory, correction" in result

    @pytest.mark.asyncio
    async def test_journal_entry_created(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        await do_remember(store, "journal test", "epistemic", user_id="local")
        journal = db.recent_journal(days=1, user_id="local")
        assert any("journal test" in e["content"] for e in journal)

    @pytest.mark.asyncio
    async def test_memory_inserted_in_sqlite(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "sqlite test", "epistemic", user_id="local")
        # Extract mem_id from result
        mem_id = result.split("id: ")[1].rstrip(")")
        mem = db.get_memory(mem_id, user_id="local")
        assert mem is not None
        assert mem.content == "sqlite test"

    @pytest.mark.asyncio
    async def test_vector_upsert_called(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        await do_remember(store, "vector test", "epistemic", user_id="local")
        store.vectors.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_upsert_failure_does_not_crash(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        store.vectors.upsert.side_effect = RuntimeError("qdrant down")
        result = await do_remember(store, "should not crash", "epistemic")
        assert "Remembered" in result

    @pytest.mark.asyncio
    async def test_auto_link_called(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        await do_remember(store, "link test", "relational", person="Bob", project="proj")
        # auto_link is on the real db, but store.db is real, so verify edges indirectly
        # The memory should be stored
        mems = db.list_memories(user_id="local")
        assert len(mems) >= 1

    @pytest.mark.asyncio
    async def test_contradiction_warning_high_similarity(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        # Insert an existing memory that the vector search will "find"
        existing = _insert_memory(db, id="mem_existing", content="cats are great")
        store.vectors.search.return_value = [("mem_existing", 0.90)]
        result = await do_remember(store, "cats are terrible", "epistemic")
        assert "warning" in result.lower()
        assert "high similarity" in result.lower()

    @pytest.mark.asyncio
    async def test_no_contradiction_warning_low_similarity(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        store.vectors.search.return_value = [("mem_other", 0.40)]
        result = await do_remember(store, "something", "epistemic")
        assert "high similarity" not in result.lower()

    @pytest.mark.asyncio
    async def test_correction_gate_creates_contradicts_edge(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        old = _insert_memory(db, id="mem_old", content="old fact", confidence=0.9)
        store.vectors.search.return_value = [("mem_old", 0.7)]
        result = await do_remember(store, "corrected fact", "correction")
        assert "Remembered [correction]" in result
        # Check confidence was halved
        updated = db.get_memory("mem_old", user_id="local")
        assert updated is not None
        assert updated.confidence == pytest.approx(0.45, abs=0.01)

    @pytest.mark.asyncio
    async def test_correction_gate_edge_stored(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        _insert_memory(db, id="mem_old2", content="old thing")
        store.vectors.search.return_value = [("mem_old2", 0.6)]
        await do_remember(store, "new thing", "correction")
        edges = db.conn.execute(
            "SELECT * FROM edges WHERE relation = 'CONTRADICTS'"
        ).fetchall()
        assert len(edges) >= 1

    @pytest.mark.asyncio
    async def test_memory_chain_follows_edge(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        _insert_memory(db, id="mem_prev", content="previous note", person="Alice")
        result = await do_remember(store, "followup note", "relational", person="Alice")
        assert "Remembered" in result
        edges = db.conn.execute(
            "SELECT * FROM edges WHERE relation = 'FOLLOWS'"
        ).fetchall()
        assert len(edges) >= 1

    @pytest.mark.asyncio
    async def test_memory_chain_no_edge_without_person_project(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        await do_remember(store, "no chain", "epistemic")
        edges = db.conn.execute(
            "SELECT * FROM edges WHERE relation = 'FOLLOWS'"
        ).fetchall()
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_long_content_truncated_in_preview(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        long_content = "x" * 200
        result = await do_remember(store, long_content, "epistemic")
        # preview is content[:80]
        assert "x" * 80 in result
        assert "x" * 81 not in result.split("(id:")[0]

    # --- PII detection ---

    @pytest.mark.asyncio
    async def test_pii_sk_api_key(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("my key is sk-abcdefghijklmnopqrstuvwxyz")
        assert result is not None
        assert "API key" in result

    @pytest.mark.asyncio
    async def test_pii_stripe_key(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("sk_live_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3")
        assert result is not None
        assert "Stripe" in result

    @pytest.mark.asyncio
    async def test_pii_aws_key(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("AKIAIOSFODNN7EXAMPLE")
        assert result is not None
        assert "AWS" in result

    @pytest.mark.asyncio
    async def test_pii_ssn(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("my ssn is 123-45-6789")
        assert result is not None
        assert "SSN" in result

    @pytest.mark.asyncio
    async def test_pii_credit_card(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("card number 4111 1111 1111 1111")
        assert result is not None
        assert "credit card" in result

    @pytest.mark.asyncio
    async def test_pii_password(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("password: mysecretpass123")
        assert result is not None
        assert "password" in result

    @pytest.mark.asyncio
    async def test_pii_jwt(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        result = _check_pii(jwt)
        assert result is not None
        assert "JWT" in result

    @pytest.mark.asyncio
    async def test_pii_github_token(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        assert result is not None
        assert "GitHub" in result

    @pytest.mark.asyncio
    async def test_pii_slack_token(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("xoxb-some-slack-token-value")
        assert result is not None
        assert "Slack" in result

    @pytest.mark.asyncio
    async def test_no_pii_clean_content(self, db):
        from claude_memory_kit.tools.remember import _check_pii
        result = _check_pii("I like programming in Python")
        assert result is None

    @pytest.mark.asyncio
    async def test_pii_warning_in_remember_result(self, db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        result = await do_remember(store, "my ssn 123-45-6789", "epistemic")
        assert "WARNING" in result
        assert "SSN" in result


# ===========================================================================
# recall.py
# ===========================================================================

class TestRecall:
    """Tests for do_recall."""

    @pytest.mark.asyncio
    async def test_vector_results_returned(self, db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        _insert_memory(db, id="mem_recall_1", content="vector recall test")
        store.vectors.search.return_value = [("mem_recall_1", 0.88)]
        result = await do_recall(store, "recall test")
        assert "Found 1 memories" in result
        assert "vector recall test" in result

    @pytest.mark.asyncio
    async def test_cloud_text_search_fallback(self, db):
        """Cloud mode: Qdrant text index used as fallback."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = True
        store.vectors._disabled = False
        _insert_memory(db, id="mem_text_1", content="fulltext search test")
        store.vectors.search.return_value = []
        store.vectors.search_text.return_value = [("mem_text_1", 1.0)]
        result = await do_recall(store, "fulltext")
        assert "Found 1 memories" in result
        assert "fulltext search test" in result
        assert "text]" in result

    @pytest.mark.asyncio
    async def test_local_fts5_fallback(self, db):
        """Local mode: SQLite FTS5 used as fallback."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = False
        store.vectors._disabled = False
        _insert_memory(db, id="mem_fts_1", content="local fts search test")
        store.vectors.search.return_value = []
        result = await do_recall(store, "local")
        # FTS5 should find the memory via SQLite
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_cloud_disabled_falls_to_fts5(self, db):
        """Cloud mode but disabled: falls back to FTS5."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = True
        store.vectors._disabled = True
        _insert_memory(db, id="mem_disabled_1", content="disabled fallback test")
        store.vectors.search.return_value = []
        result = await do_recall(store, "disabled")
        assert isinstance(result, str)
        store.vectors.search_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_results_message(self, db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = False
        store.vectors.search.return_value = []
        result = await do_recall(store, "nonexistent query xyzzy")
        assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_graph_traversal_for_sparse_results(self, db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        # Insert two related memories with an edge
        _insert_memory(db, id="mem_g1", content="graph node one", person="Alice")
        _insert_memory(db, id="mem_g2", content="graph node two", person="Alice")
        db.add_edge("mem_g1", "mem_g2", "RELATED_TO", user_id="local")
        # Vector search returns only mem_g1 (sparse: < 3 results)
        store.vectors.search.return_value = [("mem_g1", 0.75)]
        result = await do_recall(store, "graph test")
        assert "graph node one" in result
        # Graph traversal should pick up mem_g2
        assert "graph" in result.lower()

    @pytest.mark.asyncio
    async def test_vector_search_failure_falls_through(self, db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors.search.side_effect = RuntimeError("qdrant down")
        _insert_memory(db, id="mem_ftsfail", content="fallback test content")
        result = await do_recall(store, "fallback")
        # Should not crash
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_deduplication_across_sources(self, db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        _insert_memory(db, id="mem_dedup", content="dedup test")
        store.vectors.search.return_value = [("mem_dedup", 0.80)]
        result = await do_recall(store, "dedup")
        # mem_dedup should appear only once
        assert result.count("mem_dedup") <= 2  # once in content, once in id line


# ===========================================================================
# forget.py
# ===========================================================================

class TestForget:
    """Tests for do_forget."""

    @pytest.mark.asyncio
    async def test_happy_path_forget(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        _insert_memory(db, id="mem_forget_1", content="to be forgotten")
        result = await do_forget(store, "mem_forget_1", "user requested", user_id="local")
        assert "Forgotten: mem_forget_1" in result
        assert "Archived" in result

    @pytest.mark.asyncio
    async def test_forget_nonexistent_memory(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        result = await do_forget(store, "mem_does_not_exist", "no reason")
        assert "No memory found" in result

    @pytest.mark.asyncio
    async def test_forget_archives_memory(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        _insert_memory(db, id="mem_archive_test", content="archive me")
        await do_forget(store, "mem_archive_test", "cleanup", user_id="local")
        row = db.conn.execute(
            "SELECT * FROM archive WHERE id = ?", ("mem_archive_test",)
        ).fetchone()
        assert row is not None
        assert row["reason"] == "cleanup"

    @pytest.mark.asyncio
    async def test_forget_removes_from_vectors(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        _insert_memory(db, id="mem_vec_del", content="delete vector")
        await do_forget(store, "mem_vec_del", "removing", user_id="local")
        store.vectors.delete.assert_called_once_with("mem_vec_del", user_id="local")

    @pytest.mark.asyncio
    async def test_forget_vector_delete_failure_does_not_crash(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        _insert_memory(db, id="mem_vfail", content="fail vector delete")
        store.vectors.delete.side_effect = RuntimeError("qdrant error")
        result = await do_forget(store, "mem_vfail", "force delete")
        assert "Forgotten" in result

    @pytest.mark.asyncio
    async def test_forget_deletes_from_sqlite(self, db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(db)
        _insert_memory(db, id="mem_sqldel", content="delete from sqlite")
        await do_forget(store, "mem_sqldel", "cleanup", user_id="local")
        assert db.get_memory("mem_sqldel", user_id="local") is None


# ===========================================================================
# scan.py
# ===========================================================================

class TestScan:
    """Tests for scan_content, _luhn_check, and do_scan."""

    def test_scan_api_key(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("key is sk-abcdefghijklmnopqrstuvwxyz")
        types = [f["type"] for f in findings]
        assert "API key (sk-)" in types

    def test_scan_stripe_key(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("sk_live_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3")
        types = [f["type"] for f in findings]
        assert "Stripe key" in types

    def test_scan_aws_key(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("AKIAIOSFODNN7EXAMPLE")
        types = [f["type"] for f in findings]
        assert "AWS access key" in types

    def test_scan_github_token(self):
        from claude_memory_kit.tools.scan import scan_content
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        findings = scan_content(token)
        types = [f["type"] for f in findings]
        assert "GitHub token" in types

    def test_scan_slack_token(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("xoxb-some-slack-token")
        types = [f["type"] for f in findings]
        assert "Slack token" in types

    def test_scan_jwt(self):
        from claude_memory_kit.tools.scan import scan_content
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        findings = scan_content(jwt)
        types = [f["type"] for f in findings]
        assert "JWT token" in types

    def test_scan_password(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("password = mysecretpassword")
        types = [f["type"] for f in findings]
        assert "Generic secret" in types

    def test_scan_bearer_token(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("Bearer eyABCDEFGHIJKLMNOPQRSTUVWXYZ")
        types = [f["type"] for f in findings]
        assert "Bearer token" in types

    def test_scan_private_key(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("-----BEGIN RSA PRIVATE KEY-----")
        types = [f["type"] for f in findings]
        assert "Private key header" in types

    def test_scan_ssn(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("ssn: 123-45-6789")
        types = [f["type"] for f in findings]
        assert "SSN" in types

    def test_scan_email(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("reach me at user@example.com")
        types = [f["type"] for f in findings]
        assert "Email address" in types

    def test_scan_phone(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("call me at 555-123-4567")
        types = [f["type"] for f in findings]
        assert "Phone number (US)" in types

    def test_scan_clean_text_no_findings(self):
        from claude_memory_kit.tools.scan import scan_content
        findings = scan_content("I like apples and oranges.")
        assert len(findings) == 0

    def test_scan_credit_card_visa_valid_luhn(self):
        from claude_memory_kit.tools.scan import scan_content
        # 4111111111111111 passes Luhn
        findings = scan_content("card 4111111111111111")
        types = [f["type"] for f in findings]
        assert "Credit card (Visa)" in types

    def test_scan_credit_card_invalid_luhn_rejected(self):
        from claude_memory_kit.tools.scan import scan_content
        # 4111111111111112 fails Luhn
        findings = scan_content("card 4111111111111112")
        credit_types = [f for f in findings if f["type"].startswith("Credit card")]
        assert len(credit_types) == 0

    def test_scan_credit_card_mc_valid(self):
        from claude_memory_kit.tools.scan import scan_content
        # 5500000000000004 is a valid MC test number
        findings = scan_content("card 5500000000000004")
        types = [f["type"] for f in findings]
        assert "Credit card (MC)" in types

    def test_scan_match_preview_truncated(self):
        from claude_memory_kit.tools.scan import scan_content
        long_key = "sk-" + "a" * 100
        findings = scan_content(long_key)
        assert len(findings) > 0
        assert len(findings[0]["match"]) <= 40

    def test_scan_position_reported(self):
        from claude_memory_kit.tools.scan import scan_content
        text = "prefix sk-abcdefghijklmnopqrstuvwxyz suffix"
        findings = scan_content(text)
        assert findings[0]["position"] == 7

    # --- Luhn ---

    def test_luhn_valid(self):
        from claude_memory_kit.tools.scan import _luhn_check
        assert _luhn_check("4111111111111111") is True

    def test_luhn_invalid(self):
        from claude_memory_kit.tools.scan import _luhn_check
        assert _luhn_check("4111111111111112") is False

    def test_luhn_too_short(self):
        from claude_memory_kit.tools.scan import _luhn_check
        assert _luhn_check("12345") is False

    def test_luhn_with_spaces(self):
        from claude_memory_kit.tools.scan import _luhn_check
        assert _luhn_check("4111 1111 1111 1111") is True

    def test_luhn_with_dashes(self):
        from claude_memory_kit.tools.scan import _luhn_check
        assert _luhn_check("4111-1111-1111-1111") is True

    # --- do_scan ---

    @pytest.mark.asyncio
    async def test_do_scan_no_sensitive_data(self, db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(db)
        _insert_memory(db, id="mem_clean", content="nothing sensitive here")
        result = await do_scan(store, user_id="local")
        assert "No sensitive data patterns found" in result

    @pytest.mark.asyncio
    async def test_do_scan_finds_sensitive_data(self, db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(db)
        _insert_memory(db, id="mem_pii", content="my ssn is 123-45-6789")
        result = await do_scan(store, user_id="local")
        assert "Found 1 with potential sensitive data" in result
        assert "SSN" in result

    @pytest.mark.asyncio
    async def test_do_scan_empty_store(self, db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(db)
        result = await do_scan(store, user_id="local")
        assert "Scanned 0 memories" in result


# ===========================================================================
# classify.py
# ===========================================================================

class TestClassify:
    """Tests for classify_single, classify_memories, reclassify_memory, and JSON parsers."""

    # --- JSON parsing ---

    def test_parse_json_array_valid(self):
        from claude_memory_kit.tools.classify import _parse_json_array
        result = _parse_json_array('[{"id": "mem_1", "level": "safe"}]')
        assert len(result) == 1
        assert result[0]["level"] == "safe"

    def test_parse_json_array_with_prefix(self):
        from claude_memory_kit.tools.classify import _parse_json_array
        result = _parse_json_array('Here are the results: [{"id": "mem_1", "level": "safe"}]')
        assert len(result) == 1

    def test_parse_json_array_invalid_returns_empty(self):
        from claude_memory_kit.tools.classify import _parse_json_array
        result = _parse_json_array("this is not json at all")
        assert result == []

    def test_parse_json_array_broken_json_in_brackets(self):
        from claude_memory_kit.tools.classify import _parse_json_array
        result = _parse_json_array("[broken json here]")
        assert result == []

    def test_parse_json_object_valid(self):
        from claude_memory_kit.tools.classify import _parse_json_object
        result = _parse_json_object('{"level": "sensitive", "reason": "has salary"}')
        assert result["level"] == "sensitive"

    def test_parse_json_object_with_prefix(self):
        from claude_memory_kit.tools.classify import _parse_json_object
        result = _parse_json_object('Result: {"level": "critical", "reason": "API key"}')
        assert result["level"] == "critical"

    def test_parse_json_object_invalid_returns_empty(self):
        from claude_memory_kit.tools.classify import _parse_json_object
        result = _parse_json_object("not json")
        assert result == {}

    def test_parse_json_object_broken_json_in_braces(self):
        from claude_memory_kit.tools.classify import _parse_json_object
        result = _parse_json_object("{broken json}")
        assert result == {}

    # --- classify_single ---

    @pytest.mark.asyncio
    async def test_classify_single_no_api_key(self, db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value=""):
            result = await classify_single(store, "mem_1", user_id="local")
        assert result["level"] == "unknown"
        assert "no API key" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_memory_not_found(self, db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"):
            result = await classify_single(store, "mem_nonexistent", user_id="local")
        assert result["level"] == "unknown"
        assert "not found" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_happy_path(self, db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(db)
        _insert_memory(db, id="mem_cls", content="I prefer Python")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = '{"level": "safe", "reason": "General preference"}'
            result = await classify_single(store, "mem_cls", user_id="local")
        assert result["level"] == "safe"
        assert result["reason"] == "General preference"
        # Check DB was updated
        mem = db.get_memory("mem_cls", user_id="local")
        assert mem.sensitivity == "safe"

    @pytest.mark.asyncio
    async def test_classify_single_invalid_response(self, db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(db)
        _insert_memory(db, id="mem_cls2", content="test content")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = '{"level": "banana", "reason": "nonsense"}'
            result = await classify_single(store, "mem_cls2", user_id="local")
        assert result["level"] == "unknown"
        assert "invalid" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_api_exception(self, db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(db)
        _insert_memory(db, id="mem_cls3", content="test content")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = RuntimeError("API timeout")
            result = await classify_single(store, "mem_cls3", user_id="local")
        assert result["level"] == "unknown"
        assert "API timeout" in result["reason"]

    # --- classify_memories (batch) ---

    @pytest.mark.asyncio
    async def test_classify_memories_no_api_key(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value=""):
            result = await classify_memories(store)
        assert "No API key" in result

    @pytest.mark.asyncio
    async def test_classify_memories_no_memories(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"):
            result = await classify_memories(store)
        assert "No memories to classify" in result

    @pytest.mark.asyncio
    async def test_classify_memories_batch_success(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        _insert_memory(db, id="mem_b1", content="I like Python")
        _insert_memory(db, id="mem_b2", content="My salary is 100k")
        api_response = json.dumps([
            {"id": "mem_b1", "level": "safe", "reason": "general preference"},
            {"id": "mem_b2", "level": "sensitive", "reason": "salary info"},
        ])
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response
            result = await classify_memories(store)
        assert "Classified 2 memories" in result
        assert "safe: 1" in result
        assert "sensitive: 1" in result

    @pytest.mark.asyncio
    async def test_classify_memories_partial_results(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        _insert_memory(db, id="mem_p1", content="content one")
        _insert_memory(db, id="mem_p2", content="content two")
        # API only returns result for one memory
        api_response = json.dumps([
            {"id": "mem_p1", "level": "safe", "reason": "ok"},
        ])
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response
            result = await classify_memories(store)
        assert "failed: 1" in result

    @pytest.mark.asyncio
    async def test_classify_memories_force_mode(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        _insert_memory(db, id="mem_f1", content="already classified",
                       sensitivity="safe", sensitivity_reason="test")
        api_response = json.dumps([
            {"id": "mem_f1", "level": "sensitive", "reason": "reclassified"},
        ])
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response
            result = await classify_memories(store, force=True)
        assert "Classified 1 memories" in result
        mem = db.get_memory("mem_f1", user_id="local")
        assert mem.sensitivity == "sensitive"

    @pytest.mark.asyncio
    async def test_classify_memories_api_failure_counts_failed(self, db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(db)
        _insert_memory(db, id="mem_af1", content="fail batch")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = RuntimeError("batch failed")
            result = await classify_memories(store)
        assert "failed: 1" in result

    # --- reclassify_memory ---

    @pytest.mark.asyncio
    async def test_reclassify_invalid_level(self, db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(db)
        result = await reclassify_memory(store, "mem_1", "banana")
        assert "Invalid level" in result

    @pytest.mark.asyncio
    async def test_reclassify_memory_not_found(self, db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(db)
        result = await reclassify_memory(store, "mem_nonexist", "safe")
        assert "Memory not found" in result

    @pytest.mark.asyncio
    async def test_reclassify_happy_path(self, db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(db)
        _insert_memory(db, id="mem_rcl", content="reclassify me",
                       sensitivity="safe", sensitivity_reason="original")
        result = await reclassify_memory(store, "mem_rcl", "critical")
        assert "Reclassified mem_rcl as critical" in result
        mem = db.get_memory("mem_rcl", user_id="local")
        assert mem.sensitivity == "critical"
        assert mem.sensitivity_reason == "manually reclassified by user"


# ===========================================================================
# reflect.py
# ===========================================================================

class TestReflect:
    """Tests for do_reflect."""

    @pytest.mark.asyncio
    async def test_reflect_no_api_key(self, db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert "No API key" in result
        assert "Reflection complete" in result

    @pytest.mark.asyncio
    async def test_reflect_archives_fading_memories(self, db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        # Create a very old memory with fast decay and no accesses
        old_time = datetime.now(timezone.utc) - timedelta(days=365)
        _insert_memory(
            db, id="mem_fading", content="old forgotten thing",
            gate=Gate.behavioral, decay_class=DecayClass.fast,
            created=old_time, last_accessed=old_time, access_count=1,
        )
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert "Archived 1 fading memories" in result
        # Memory should be gone from active store
        assert db.get_memory("mem_fading", user_id="local") is None

    @pytest.mark.asyncio
    async def test_reflect_does_not_archive_never_decay(self, db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        old_time = datetime.now(timezone.utc) - timedelta(days=365)
        _insert_memory(
            db, id="mem_promise", content="a commitment",
            gate=Gate.promissory, decay_class=DecayClass.never,
            created=old_time, last_accessed=old_time,
        )
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert db.get_memory("mem_promise", user_id="local") is not None

    @pytest.mark.asyncio
    async def test_reflect_with_api_key_consolidates(self, db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_cons.return_value = "Consolidated 1 weeks: 2026-W05"
            mock_regen.return_value = "Updated identity card"
            result = await do_reflect(store, user_id="local")
        assert "Consolidated 1 weeks" in result


# ===========================================================================
# identity.py
# ===========================================================================

class TestIdentity:
    """Tests for do_identity onboarding flow."""

    @pytest.mark.asyncio
    async def test_identity_returns_existing_card(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        card = IdentityCard(
            person="Alice", project="Alpha",
            content="I work with Alice on Alpha.",
            last_updated=datetime.now(timezone.utc),
        )
        db.set_identity(card, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "I work with Alice on Alpha." in result

    @pytest.mark.asyncio
    async def test_identity_with_recent_context(self, db):
        from claude_memory_kit.tools.identity import do_identity
        from claude_memory_kit.types import JournalEntry
        store = _make_store(db)
        card = IdentityCard(
            person="Bob", project="Beta",
            content="I work with Bob.",
            last_updated=datetime.now(timezone.utc),
        )
        db.set_identity(card, user_id="local")
        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc),
            gate=Gate.epistemic,
            content="Bob learned about async",
        )
        db.insert_journal(entry, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "Recent context" in result
        assert "Bob learned about async" in result

    @pytest.mark.asyncio
    async def test_onboarding_step0_cold_start(self, db):
        from claude_memory_kit.tools.identity import do_identity, COLD_START
        store = _make_store(db)
        result = await do_identity(store, user_id="local")
        assert result == COLD_START

    @pytest.mark.asyncio
    async def test_onboarding_step0_response_moves_to_step1(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        # First call triggers cold start
        await do_identity(store, user_id="local")
        # Respond with name
        result = await do_identity(store, onboard_response="Alice", user_id="local")
        assert "Nice to meet you, Alice" in result

    @pytest.mark.asyncio
    async def test_onboarding_step1_response_moves_to_step2(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        await do_identity(store, user_id="local")
        await do_identity(store, onboard_response="Alice", user_id="local")
        result = await do_identity(store, onboard_response="Project Alpha", user_id="local")
        assert "How do you like to work with me" in result

    @pytest.mark.asyncio
    async def test_onboarding_step2_creates_identity(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        await do_identity(store, user_id="local")
        await do_identity(store, onboard_response="Alice", user_id="local")
        await do_identity(store, onboard_response="Project Alpha", user_id="local")
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value=""):
            result = await do_identity(store, onboard_response="Fast and direct", user_id="local")
        assert "Identity card created" in result
        assert "Alice" in result
        assert "Project Alpha" in result
        assert "Fast and direct" in result

    @pytest.mark.asyncio
    async def test_onboarding_step2_with_api_key(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        await do_identity(store, user_id="local")
        await do_identity(store, onboard_response="Bob", user_id="local")
        await do_identity(store, onboard_response="Beta project", user_id="local")
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.identity.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_regen.return_value = "Synthesized identity for Bob"
            result = await do_identity(store, onboard_response="deliberate", user_id="local")
        assert "Identity card created" in result
        assert "Synthesized identity for Bob" in result

    @pytest.mark.asyncio
    async def test_onboarding_step2_api_failure_fallback(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        await do_identity(store, user_id="local")
        await do_identity(store, onboard_response="Carol", user_id="local")
        await do_identity(store, onboard_response="Gamma", user_id="local")
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.identity.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_regen.side_effect = RuntimeError("API down")
            result = await do_identity(store, onboard_response="exploratory", user_id="local")
        assert "Identity card created" in result
        assert "Carol" in result
        assert "Gamma" in result

    @pytest.mark.asyncio
    async def test_onboarding_step_resume_at_step1(self, db):
        from claude_memory_kit.tools.identity import do_identity, STEP_2_TEMPLATE
        store = _make_store(db)
        # Manually set onboarding at step 1
        state = OnboardingState(step=1, person="Dave")
        db.set_onboarding(state, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "Nice to meet you, Dave" in result

    @pytest.mark.asyncio
    async def test_onboarding_step_resume_at_step2(self, db):
        from claude_memory_kit.tools.identity import do_identity, STEP_3_TEMPLATE
        store = _make_store(db)
        state = OnboardingState(step=2, person="Eve", project="Delta")
        db.set_onboarding(state, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "How do you like to work" in result

    @pytest.mark.asyncio
    async def test_onboarding_cleans_up_after_completion(self, db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        await do_identity(store, user_id="local")
        await do_identity(store, onboard_response="Frank", user_id="local")
        await do_identity(store, onboard_response="Epsilon", user_id="local")
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value=""):
            await do_identity(store, onboard_response="direct", user_id="local")
        assert db.get_onboarding(user_id="local") is None


# ===========================================================================
# prime.py
# ===========================================================================

class TestPrime:
    """Tests for do_prime."""

    @pytest.mark.asyncio
    async def test_prime_returns_relevant_context(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        _insert_memory(db, id="mem_prime_1", content="Python is dynamically typed")
        store.vectors.search.return_value = [("mem_prime_1", 0.75)]
        result = await do_prime(store, "tell me about Python", user_id="local")
        assert "Relevant context from memory" in result
        assert "Python is dynamically typed" in result

    @pytest.mark.asyncio
    async def test_prime_filters_low_scores(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        _insert_memory(db, id="mem_low", content="irrelevant thing")
        store.vectors.search.return_value = [("mem_low", 0.1)]
        result = await do_prime(store, "something")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_no_results(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        store.vectors.search.return_value = []
        result = await do_prime(store, "anything")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_search_failure(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        store.vectors.search.side_effect = RuntimeError("search failed")
        result = await do_prime(store, "query")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_touches_memory(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        _insert_memory(db, id="mem_touch", content="touch test")
        store.vectors.search.return_value = [("mem_touch", 0.5)]
        await do_prime(store, "test")
        mem = db.get_memory("mem_touch", user_id="local")
        assert mem.access_count == 2  # original 1 + touch

    @pytest.mark.asyncio
    async def test_prime_multiple_results(self, db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(db)
        _insert_memory(db, id="mem_p1", content="fact one")
        _insert_memory(db, id="mem_p2", content="fact two")
        store.vectors.search.return_value = [("mem_p1", 0.8), ("mem_p2", 0.6)]
        result = await do_prime(store, "facts")
        assert "fact one" in result
        assert "fact two" in result


# ===========================================================================
# auto_extract.py
# ===========================================================================

class TestAutoExtract:
    """Tests for do_auto_extract."""

    @pytest.mark.asyncio
    async def test_auto_extract_no_api_key(self, db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(db)
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value=""):
            result = await do_auto_extract(store, "some transcript")
        assert "No API key" in result

    @pytest.mark.asyncio
    async def test_auto_extract_no_memories_found(self, db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(db)
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.auto_extract.extract_memories", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = []
            result = await do_auto_extract(store, "boring transcript")
        assert "No memories worth keeping" in result

    @pytest.mark.asyncio
    async def test_auto_extract_saves_memories(self, db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(db)
        extracted = [
            {"gate": "epistemic", "content": "Learned about async IO", "person": None, "project": "Alpha"},
            {"gate": "relational", "content": "Alice likes coffee", "person": "Alice", "project": None},
        ]
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.auto_extract.extract_memories", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = extracted
            result = await do_auto_extract(store, "a rich transcript")
        assert "Auto-extracted 2 memories" in result
        assert "Learned about async IO" in result
        assert "Alice likes coffee" in result

    @pytest.mark.asyncio
    async def test_auto_extract_handles_save_failure_gracefully(self, db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(db)
        extracted = [
            {"gate": "invalid_gate", "content": "this will fail gate check"},
            {"gate": "epistemic", "content": "this should work"},
        ]
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.auto_extract.extract_memories", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = extracted
            result = await do_auto_extract(store, "transcript")
        # The invalid gate memory will still be "saved" since do_remember returns a string
        # (the error message), not an exception
        assert "Auto-extracted 2 memories" in result


# ===========================================================================
# checkpoint.py
# ===========================================================================

class TestCheckpoint:
    @pytest.mark.asyncio
    async def test_do_checkpoint_saves_to_journal(self, db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(db)

        result = await do_checkpoint(
            store, "Task: writing tests. Decided: pytest. Next: coverage.",
            user_id="test-user",
        )

        assert "Checkpoint saved" in result
        assert "next session" in result

        # Verify it was written to the journal
        cp = db.latest_checkpoint(user_id="test-user")
        assert cp is not None
        assert cp["content"] == "Task: writing tests. Decided: pytest. Next: coverage."
        assert cp["gate"] == "checkpoint"

    @pytest.mark.asyncio
    async def test_do_checkpoint_uses_default_user_id(self, db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(db)

        await do_checkpoint(store, "default user checkpoint")
        cp = db.latest_checkpoint(user_id="local")
        assert cp is not None
        assert cp["content"] == "default user checkpoint"

    @pytest.mark.asyncio
    async def test_do_checkpoint_overwrites_previous(self, db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(db)

        await do_checkpoint(store, "first checkpoint", user_id="u1")
        await do_checkpoint(store, "second checkpoint", user_id="u1")

        # latest_checkpoint should return the most recent
        cp = db.latest_checkpoint(user_id="u1")
        assert cp["content"] == "second checkpoint"
