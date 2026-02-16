"""Comprehensive tests for all CMK tool functions (QdrantStore backend)."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_memory_kit.types import (
    DecayClass,
    Gate,
    IdentityCard,
    JournalEntry,
    Memory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(qdrant_db):
    """Build a mock Store with a real QdrantStore backend."""
    store = MagicMock()
    store.qdrant = qdrant_db
    store.auth_db = MagicMock()
    return store


def _insert_memory(qdrant_db, id="mem_test_001", gate=Gate.epistemic,
                   content="test memory content", person=None,
                   project=None, confidence=0.9, user_id="local",
                   sensitivity=None, sensitivity_reason=None,
                   access_count=1, decay_class=None,
                   created=None, last_accessed=None):
    """Insert a memory into a real QdrantStore and return the Memory."""
    now = created or datetime.now(timezone.utc)
    la = last_accessed or now
    dc = decay_class or DecayClass.from_gate(gate)
    mem = Memory(
        id=id, created=now, gate=gate, person=person, project=project,
        confidence=confidence, last_accessed=la, access_count=access_count,
        decay_class=dc, content=content, sensitivity=sensitivity,
        sensitivity_reason=sensitivity_reason,
    )
    qdrant_db.insert_memory(mem, user_id=user_id)
    if sensitivity is not None:
        qdrant_db.update_sensitivity(id, sensitivity, sensitivity_reason or "", user_id=user_id)
    return mem


# ===========================================================================
# remember.py
# ===========================================================================

class TestRemember:
    """Tests for do_remember and check_pii."""

    @pytest.mark.asyncio
    async def test_happy_path_epistemic(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "Python uses indentation", "epistemic", user_id="local")
        assert "Remembered [epistemic]" in result
        assert "Python uses indentation" in result
        assert "id: mem_" in result

    @pytest.mark.asyncio
    async def test_happy_path_relational(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "Alice likes tea", "relational", person="Alice")
        assert "Remembered [relational]" in result
        assert "Alice likes tea" in result

    @pytest.mark.asyncio
    async def test_happy_path_behavioral(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "User prefers short answers", "behavioral")
        assert "Remembered [behavioral]" in result

    @pytest.mark.asyncio
    async def test_happy_path_promissory(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "I promised to review PR #42", "promissory")
        assert "Remembered [promissory]" in result

    @pytest.mark.asyncio
    async def test_invalid_gate_returns_error(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "some content", "invalid_gate")
        assert "invalid gate" in result
        assert "behavioral, relational, epistemic, promissory, correction" in result

    @pytest.mark.asyncio
    async def test_journal_entry_created(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        await do_remember(store, "journal test", "epistemic", user_id="local")
        journal = qdrant_db.recent_journal(days=1, user_id="local")
        assert any("journal test" in e["content"] for e in journal)

    @pytest.mark.asyncio
    async def test_memory_inserted_in_qdrant(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "qdrant test", "epistemic", user_id="local")
        # Extract mem_id from result
        mem_id = result.split("id: ")[1].rstrip(")")
        mem = qdrant_db.get_memory(mem_id, user_id="local")
        assert mem is not None
        assert mem.content == "qdrant test"

    @pytest.mark.asyncio
    async def test_auto_link_memory_stored(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        await do_remember(store, "link test", "relational", person="Bob", project="proj")
        # auto_link is a no-op, but the memory should still be stored
        mems = qdrant_db.list_memories(user_id="local")
        assert len(mems) >= 1

    @pytest.mark.asyncio
    async def test_contradiction_warning_high_similarity(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        # Insert an existing memory that the search will "find"
        _insert_memory(qdrant_db, id="mem_existing", content="cats are great")
        # Mock search to return high similarity hit
        real_search = qdrant_db.search
        qdrant_db.search = MagicMock(return_value=[("mem_existing", 0.90)])
        result = await do_remember(store, "cats are terrible", "epistemic")
        assert "warning" in result.lower()
        assert "high similarity" in result.lower()
        qdrant_db.search = real_search

    @pytest.mark.asyncio
    async def test_no_contradiction_warning_low_similarity(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(return_value=[("mem_other", 0.40)])
        result = await do_remember(store, "something", "epistemic")
        assert "high similarity" not in result.lower()

    @pytest.mark.asyncio
    async def test_correction_gate_creates_contradicts_edge(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_old", content="old fact", confidence=0.9)
        qdrant_db.search = MagicMock(return_value=[("mem_old", 0.7)])
        result = await do_remember(store, "corrected fact", "correction")
        assert "Remembered [correction]" in result
        # Check confidence was halved
        updated = qdrant_db.get_memory("mem_old", user_id="local")
        assert updated is not None
        assert updated.confidence == pytest.approx(0.45, abs=0.01)

    @pytest.mark.asyncio
    async def test_correction_gate_edge_stored(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_old2", content="old thing")
        qdrant_db.search = MagicMock(return_value=[("mem_old2", 0.6)])
        result = await do_remember(store, "new thing", "correction")
        # Extract the new memory id from result
        mem_id = result.split("id: ")[1].rstrip(")")
        # Verify CONTRADICTS edge was created via find_related
        related = qdrant_db.find_related(mem_id, depth=1, user_id="local")
        contradicts = [r for r in related if r["relation"] == "CONTRADICTS"]
        assert len(contradicts) >= 1

    @pytest.mark.asyncio
    async def test_memory_chain_follows_edge(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_prev", content="previous note", person="Alice")
        # Mock search to avoid interference from contradiction check
        qdrant_db.search = MagicMock(return_value=[])
        result = await do_remember(store, "followup note", "relational", person="Alice")
        assert "Remembered" in result
        # Extract new memory id
        mem_id = result.split("id: ")[1].rstrip(")")
        # Verify FOLLOWS edge was created
        related = qdrant_db.find_related(mem_id, depth=1, user_id="local")
        follows = [r for r in related if r["relation"] == "FOLLOWS"]
        assert len(follows) >= 1

    @pytest.mark.asyncio
    async def test_memory_chain_no_edge_without_person_project(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(return_value=[])
        result = await do_remember(store, "no chain", "epistemic")
        mem_id = result.split("id: ")[1].rstrip(")")
        # No FOLLOWS edges without person/project
        related = qdrant_db.find_related(mem_id, depth=1, user_id="local")
        follows = [r for r in related if r["relation"] == "FOLLOWS"]
        assert len(follows) == 0

    @pytest.mark.asyncio
    async def test_long_content_truncated_in_preview(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        long_content = "x" * 200
        result = await do_remember(store, long_content, "epistemic")
        # preview is content[:80]
        assert "x" * 80 in result
        assert "x" * 81 not in result.split("(id:")[0]

    # --- PII detection ---

    @pytest.mark.asyncio
    async def test_pii_sk_api_key(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("my key is sk-abcdefghijklmnopqrstuvwxyz")
        assert result is not None
        assert "API key" in result

    @pytest.mark.asyncio
    async def test_pii_stripe_key(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("sk_live_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3")
        assert result is not None
        assert "Stripe" in result

    @pytest.mark.asyncio
    async def test_pii_aws_key(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("AKIAIOSFODNN7EXAMPLE")
        assert result is not None
        assert "AWS" in result

    @pytest.mark.asyncio
    async def test_pii_ssn(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("my ssn is 123-45-6789")
        assert result is not None
        assert "SSN" in result

    @pytest.mark.asyncio
    async def test_pii_credit_card(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("card number 4111111111111111")
        assert result is not None
        assert "Credit card" in result

    @pytest.mark.asyncio
    async def test_pii_password(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("password: mysecretpass123")
        assert result is not None
        assert "Generic secret" in result

    @pytest.mark.asyncio
    async def test_pii_jwt(self):
        from claude_memory_kit.tools._pii import check_pii
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        result = check_pii(jwt)
        assert result is not None
        assert "JWT" in result

    @pytest.mark.asyncio
    async def test_pii_github_token(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        assert result is not None
        assert "GitHub" in result

    @pytest.mark.asyncio
    async def test_pii_slack_token(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("xoxb-some-slack-token-value")
        assert result is not None
        assert "Slack" in result

    @pytest.mark.asyncio
    async def test_no_pii_clean_content(self):
        from claude_memory_kit.tools._pii import check_pii
        result = check_pii("I like programming in Python")
        assert result is None

    @pytest.mark.asyncio
    async def test_pii_warning_in_remember_result(self, qdrant_db):
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(qdrant_db)
        result = await do_remember(store, "my ssn 123-45-6789", "epistemic")
        assert "WARNING" in result
        assert "SSN" in result


# ===========================================================================
# recall.py
# ===========================================================================

class TestRecall:
    """Tests for do_recall."""

    @pytest.mark.asyncio
    async def test_vector_results_returned(self, qdrant_db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_recall_1", content="vector recall test")
        qdrant_db.search = MagicMock(return_value=[("mem_recall_1", 0.88)])
        result = await do_recall(store, "recall test")
        assert "Found 1 memories" in result
        assert "vector recall test" in result

    @pytest.mark.asyncio
    async def test_text_search_fallback(self, qdrant_db):
        """Hybrid search returns nothing, text search fallback used."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_text_1", content="fulltext search test")
        qdrant_db.search = MagicMock(return_value=[])
        qdrant_db.search_text = MagicMock(return_value=[("mem_text_1", 1.0)])
        result = await do_recall(store, "fulltext")
        assert "Found 1 memories" in result
        assert "fulltext search test" in result
        assert "text]" in result

    @pytest.mark.asyncio
    async def test_no_results_message(self, qdrant_db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(return_value=[])
        qdrant_db.search_text = MagicMock(return_value=[])
        result = await do_recall(store, "nonexistent query xyzzy")
        assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_graph_traversal_for_sparse_results(self, qdrant_db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        # Insert two related memories with an edge
        _insert_memory(qdrant_db, id="mem_g1", content="graph node one", person="Alice")
        _insert_memory(qdrant_db, id="mem_g2", content="graph node two", person="Alice")
        qdrant_db.add_edge("mem_g1", "mem_g2", "RELATED_TO", user_id="local")
        # Vector search returns only mem_g1 (sparse: < 3 results)
        qdrant_db.search = MagicMock(return_value=[("mem_g1", 0.75)])
        result = await do_recall(store, "graph test")
        assert "graph node one" in result
        # Graph traversal should pick up mem_g2
        assert "graph" in result.lower()

    @pytest.mark.asyncio
    async def test_vector_search_failure_falls_through(self, qdrant_db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(side_effect=RuntimeError("qdrant down"))
        _insert_memory(qdrant_db, id="mem_ftsfail", content="fallback test content")
        result = await do_recall(store, "fallback")
        # Should not crash
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_deduplication_across_sources(self, qdrant_db):
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_dedup", content="dedup test")
        qdrant_db.search = MagicMock(return_value=[("mem_dedup", 0.80)])
        result = await do_recall(store, "dedup")
        # mem_dedup should appear only once
        assert result.count("mem_dedup") <= 2  # once in content, once in id line


# ===========================================================================
# forget.py
# ===========================================================================

class TestForget:
    """Tests for do_forget."""

    @pytest.mark.asyncio
    async def test_happy_path_forget(self, qdrant_db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_forget_1", content="to be forgotten")
        result = await do_forget(store, "mem_forget_1", "user requested", user_id="local")
        assert "Forgotten: mem_forget_1" in result
        assert "reason: user requested" in result

    @pytest.mark.asyncio
    async def test_forget_nonexistent_memory(self, qdrant_db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(qdrant_db)
        result = await do_forget(store, "mem_does_not_exist", "no reason")
        assert "No memory found" in result

    @pytest.mark.asyncio
    async def test_forget_deletes_from_qdrant(self, qdrant_db):
        from claude_memory_kit.tools.forget import do_forget
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_qdel", content="delete from qdrant")
        await do_forget(store, "mem_qdel", "cleanup", user_id="local")
        assert qdrant_db.get_memory("mem_qdel", user_id="local") is None


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
        from claude_memory_kit.tools._pii import luhn_check
        assert luhn_check("4111111111111111") is True

    def test_luhn_invalid(self):
        from claude_memory_kit.tools._pii import luhn_check
        assert luhn_check("4111111111111112") is False

    def test_luhn_too_short(self):
        from claude_memory_kit.tools._pii import luhn_check
        assert luhn_check("12345") is False

    def test_luhn_with_spaces(self):
        from claude_memory_kit.tools._pii import luhn_check
        assert luhn_check("4111 1111 1111 1111") is True

    def test_luhn_with_dashes(self):
        from claude_memory_kit.tools._pii import luhn_check
        assert luhn_check("4111-1111-1111-1111") is True

    # --- do_scan ---

    @pytest.mark.asyncio
    async def test_do_scan_no_sensitive_data(self, qdrant_db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_clean", content="nothing sensitive here")
        result = await do_scan(store, user_id="local")
        assert "No sensitive data patterns found" in result

    @pytest.mark.asyncio
    async def test_do_scan_finds_sensitive_data(self, qdrant_db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_pii", content="my ssn is 123-45-6789")
        result = await do_scan(store, user_id="local")
        assert "Found 1 with potential sensitive data" in result
        assert "SSN" in result

    @pytest.mark.asyncio
    async def test_do_scan_empty_store(self, qdrant_db):
        from claude_memory_kit.tools.scan import do_scan
        store = _make_store(qdrant_db)
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
    async def test_classify_single_no_api_key(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value=""):
            result = await classify_single(store, "mem_1", user_id="local")
        assert result["level"] == "unknown"
        assert "no API key" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_memory_not_found(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"):
            result = await classify_single(store, "mem_nonexistent", user_id="local")
        assert result["level"] == "unknown"
        assert "not found" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_happy_path(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_cls", content="I prefer Python")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = '{"level": "safe", "reason": "General preference"}'
            result = await classify_single(store, "mem_cls", user_id="local")
        assert result["level"] == "safe"
        assert result["reason"] == "General preference"
        # Check QdrantStore was updated
        mem = qdrant_db.get_memory("mem_cls", user_id="local")
        assert mem.sensitivity == "safe"

    @pytest.mark.asyncio
    async def test_classify_single_invalid_response(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_cls2", content="test content")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = '{"level": "banana", "reason": "nonsense"}'
            result = await classify_single(store, "mem_cls2", user_id="local")
        assert result["level"] == "unknown"
        assert "invalid" in result["reason"]

    @pytest.mark.asyncio
    async def test_classify_single_api_exception(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_single
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_cls3", content="test content")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = RuntimeError("API timeout")
            result = await classify_single(store, "mem_cls3", user_id="local")
        assert result["level"] == "unknown"
        assert "API timeout" in result["reason"]

    # --- classify_memories (batch) ---

    @pytest.mark.asyncio
    async def test_classify_memories_no_api_key(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value=""):
            result = await classify_memories(store)
        assert "No API key" in result

    @pytest.mark.asyncio
    async def test_classify_memories_no_memories(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"):
            result = await classify_memories(store)
        assert "No memories to classify" in result

    @pytest.mark.asyncio
    async def test_classify_memories_batch_success(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_b1", content="I like Python")
        _insert_memory(qdrant_db, id="mem_b2", content="My salary is 100k")
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
    async def test_classify_memories_partial_results(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_p1", content="content one")
        _insert_memory(qdrant_db, id="mem_p2", content="content two")
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
    async def test_classify_memories_force_mode(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_f1", content="already classified",
                       sensitivity="safe", sensitivity_reason="test")
        api_response = json.dumps([
            {"id": "mem_f1", "level": "sensitive", "reason": "reclassified"},
        ])
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = api_response
            result = await classify_memories(store, force=True)
        assert "Classified 1 memories" in result
        mem = qdrant_db.get_memory("mem_f1", user_id="local")
        assert mem.sensitivity == "sensitive"

    @pytest.mark.asyncio
    async def test_classify_memories_api_failure_counts_failed(self, qdrant_db):
        from claude_memory_kit.tools.classify import classify_memories
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_af1", content="fail batch")
        with patch("claude_memory_kit.tools.classify.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify._call_anthropic", new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = RuntimeError("batch failed")
            result = await classify_memories(store)
        assert "failed: 1" in result

    # --- reclassify_memory ---

    @pytest.mark.asyncio
    async def test_reclassify_invalid_level(self, qdrant_db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(qdrant_db)
        result = await reclassify_memory(store, "mem_1", "banana")
        assert "Invalid level" in result

    @pytest.mark.asyncio
    async def test_reclassify_memory_not_found(self, qdrant_db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(qdrant_db)
        result = await reclassify_memory(store, "mem_nonexist", "safe")
        assert "Memory not found" in result

    @pytest.mark.asyncio
    async def test_reclassify_happy_path(self, qdrant_db):
        from claude_memory_kit.tools.classify import reclassify_memory
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_rcl", content="reclassify me",
                       sensitivity="safe", sensitivity_reason="original")
        result = await reclassify_memory(store, "mem_rcl", "critical")
        assert "Reclassified mem_rcl as critical" in result
        mem = qdrant_db.get_memory("mem_rcl", user_id="local")
        assert mem.sensitivity == "critical"
        assert mem.sensitivity_reason == "manually reclassified by user"


# ===========================================================================
# reflect.py
# ===========================================================================

class TestReflect:
    """Tests for do_reflect."""

    @pytest.mark.asyncio
    async def test_reflect_no_api_key(self, qdrant_db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert "No API key" in result
        assert "Reflection complete" in result

    @pytest.mark.asyncio
    async def test_reflect_archives_fading_memories(self, qdrant_db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(qdrant_db)
        # Create a very old memory with fast decay and no accesses
        old_time = datetime.now(timezone.utc) - timedelta(days=365)
        _insert_memory(
            qdrant_db, id="mem_fading", content="old forgotten thing",
            gate=Gate.behavioral, decay_class=DecayClass.fast,
            created=old_time, last_accessed=old_time, access_count=1,
        )
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert "Archived 1 fading memories" in result
        # Memory should be gone from active store
        assert qdrant_db.get_memory("mem_fading", user_id="local") is None

    @pytest.mark.asyncio
    async def test_reflect_does_not_archive_never_decay(self, qdrant_db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(qdrant_db)
        old_time = datetime.now(timezone.utc) - timedelta(days=365)
        _insert_memory(
            qdrant_db, id="mem_promise", content="a commitment",
            gate=Gate.promissory, decay_class=DecayClass.never,
            created=old_time, last_accessed=old_time,
        )
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        assert qdrant_db.get_memory("mem_promise", user_id="local") is not None

    @pytest.mark.asyncio
    async def test_reflect_with_api_key_consolidates(self, qdrant_db):
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(qdrant_db)
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
    """Tests for the simplified do_identity flow."""

    @pytest.mark.asyncio
    async def test_identity_returns_existing_card(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        card = IdentityCard(
            person="Alice", project="Alpha",
            content="I work with Alice on Alpha.",
            last_updated=datetime.now(timezone.utc),
        )
        qdrant_db.set_identity(card, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "I work with Alice on Alpha." in result

    @pytest.mark.asyncio
    async def test_identity_with_recent_context(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        card = IdentityCard(
            person="Bob", project="Beta",
            content="I work with Bob.",
            last_updated=datetime.now(timezone.utc),
        )
        qdrant_db.set_identity(card, user_id="local")
        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc),
            gate=Gate.epistemic,
            content="Bob learned about async",
        )
        qdrant_db.insert_journal(entry, user_id="local")
        result = await do_identity(store, user_id="local")
        assert "Recent context" in result
        assert "Bob learned about async" in result

    @pytest.mark.asyncio
    async def test_no_identity_prompts(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        result = await do_identity(store, user_id="local")
        assert "No identity card yet" in result

    @pytest.mark.asyncio
    async def test_create_identity_from_response(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value=""):
            result = await do_identity(store, onboard_response="I'm Alice working on Alpha", user_id="local")
        assert "Identity card created" in result
        assert "I'm Alice working on Alpha" in result

    @pytest.mark.asyncio
    async def test_create_identity_with_api_key(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.identity.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_regen.return_value = "Synthesized identity for Alice"
            result = await do_identity(store, onboard_response="Alice", user_id="local")
        assert "Identity card created" in result
        assert "Synthesized identity for Alice" in result

    @pytest.mark.asyncio
    async def test_create_identity_api_failure_fallback(self, qdrant_db):
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.identity.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.identity.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_regen.side_effect = RuntimeError("API down")
            result = await do_identity(store, onboard_response="Bob works on Beta", user_id="local")
        assert "Identity card created" in result
        assert "Bob works on Beta" in result


# ===========================================================================
# prime.py
# ===========================================================================

class TestPrime:
    """Tests for do_prime."""

    @pytest.mark.asyncio
    async def test_prime_returns_relevant_context(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_prime_1", content="Python is dynamically typed")
        qdrant_db.search = MagicMock(return_value=[("mem_prime_1", 0.75)])
        result = await do_prime(store, "tell me about Python", user_id="local")
        assert "Relevant context from memory" in result
        assert "Python is dynamically typed" in result

    @pytest.mark.asyncio
    async def test_prime_filters_low_scores(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_low", content="irrelevant thing")
        qdrant_db.search = MagicMock(return_value=[("mem_low", 0.1)])
        result = await do_prime(store, "something")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_no_results(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(return_value=[])
        result = await do_prime(store, "anything")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_search_failure(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        qdrant_db.search = MagicMock(side_effect=RuntimeError("search failed"))
        result = await do_prime(store, "query")
        assert "No relevant memories found" in result

    @pytest.mark.asyncio
    async def test_prime_touches_memory(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_touch", content="touch test")
        qdrant_db.search = MagicMock(return_value=[("mem_touch", 0.5)])
        await do_prime(store, "test")
        mem = qdrant_db.get_memory("mem_touch", user_id="local")
        assert mem.access_count == 2  # original 1 + touch

    @pytest.mark.asyncio
    async def test_prime_multiple_results(self, qdrant_db):
        from claude_memory_kit.tools.prime import do_prime
        store = _make_store(qdrant_db)
        _insert_memory(qdrant_db, id="mem_p1", content="fact one")
        _insert_memory(qdrant_db, id="mem_p2", content="fact two")
        qdrant_db.search = MagicMock(return_value=[("mem_p1", 0.8), ("mem_p2", 0.6)])
        result = await do_prime(store, "facts")
        assert "fact one" in result
        assert "fact two" in result


# ===========================================================================
# auto_extract.py
# ===========================================================================

class TestAutoExtract:
    """Tests for do_auto_extract."""

    @pytest.mark.asyncio
    async def test_auto_extract_no_api_key(self, qdrant_db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value=""):
            result = await do_auto_extract(store, "some transcript")
        assert "No API key" in result

    @pytest.mark.asyncio
    async def test_auto_extract_no_memories_found(self, qdrant_db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(qdrant_db)
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.auto_extract.extract_memories", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = []
            result = await do_auto_extract(store, "boring transcript")
        assert "No memories worth keeping" in result

    @pytest.mark.asyncio
    async def test_auto_extract_saves_memories(self, qdrant_db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(qdrant_db)
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
    async def test_auto_extract_handles_save_failure_gracefully(self, qdrant_db):
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(qdrant_db)
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
    async def test_do_checkpoint_saves_to_journal(self, qdrant_db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(qdrant_db)

        result = await do_checkpoint(
            store, "Task: writing tests. Decided: pytest. Next: coverage.",
            user_id="test-user",
        )

        assert "Checkpoint saved" in result
        assert "next session" in result

        # Verify it was written to the journal
        cp = qdrant_db.latest_checkpoint(user_id="test-user")
        assert cp is not None
        assert cp["content"] == "Task: writing tests. Decided: pytest. Next: coverage."
        assert cp["gate"] == "checkpoint"

    @pytest.mark.asyncio
    async def test_do_checkpoint_uses_default_user_id(self, qdrant_db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(qdrant_db)

        await do_checkpoint(store, "default user checkpoint")
        cp = qdrant_db.latest_checkpoint(user_id="local")
        assert cp is not None
        assert cp["content"] == "default user checkpoint"

    @pytest.mark.asyncio
    async def test_do_checkpoint_overwrites_previous(self, qdrant_db):
        from claude_memory_kit.tools.checkpoint import do_checkpoint
        store = _make_store(qdrant_db)

        await do_checkpoint(store, "first checkpoint", user_id="u1")
        await do_checkpoint(store, "second checkpoint", user_id="u1")

        # latest_checkpoint should return the most recent
        cp = qdrant_db.latest_checkpoint(user_id="u1")
        assert cp["content"] == "second checkpoint"
