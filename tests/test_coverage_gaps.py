"""Tests to cover missing lines in reflect.py, remember.py, and cli_auth.py."""

import io
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from claude_memory_kit.types import (
    DecayClass,
    Gate,
    IdentityCard,
    Memory,
)
from claude_memory_kit import cli_auth


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_tools.py)
# ---------------------------------------------------------------------------


def _make_store(db):
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
# reflect.py - coverage gaps
# ===========================================================================


class TestReflectCoverageGaps:
    """Cover missing lines: 26, 43-44, 53-74, 77."""

    @pytest.mark.asyncio
    async def test_consolidation_returns_none_reports_no_journals(self, db):
        """Line 26: consolidate_journals returns falsy (None/empty string)."""
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock):
            mock_cons.return_value = None  # no journals old enough
            result = await do_reflect(store, user_id="local")
        assert "No journals old enough to consolidate." in result

    @pytest.mark.asyncio
    async def test_vector_delete_exception_during_archive(self, db):
        """Lines 43-44: vector delete raises during fading memory archival."""
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        old_time = datetime.now(timezone.utc) - timedelta(days=365)
        _insert_memory(
            db, id="mem_fading_vec", content="old fading memory",
            gate=Gate.behavioral, decay_class=DecayClass.fast,
            created=old_time, last_accessed=old_time, access_count=1,
        )
        store.vectors.delete.side_effect = RuntimeError("qdrant unavailable")
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value=""):
            result = await do_reflect(store, user_id="local")
        # Memory should still be archived despite vector delete failure
        assert "Archived 1 fading memories" in result
        assert db.get_memory("mem_fading_vec", user_id="local") is None

    @pytest.mark.asyncio
    async def test_identity_regeneration_with_recent_journal(self, db):
        """Lines 53-72: full identity regeneration path with recent journal entries."""
        from claude_memory_kit.tools.reflect import do_reflect
        from claude_memory_kit.types import JournalEntry
        store = _make_store(db)

        # Insert recent journal entries
        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc),
            gate=Gate.epistemic,
            content="learned about async patterns",
        )
        db.insert_journal(entry, user_id="local")

        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_cons.return_value = None
            mock_regen.return_value = "Updated identity: user loves async patterns"
            result = await do_reflect(store, user_id="local")
        assert "Identity card regenerated." in result
        # Identity should be stored in the DB
        identity = db.get_identity(user_id="local")
        assert identity is not None
        assert identity.content == "Updated identity: user loves async patterns"

    @pytest.mark.asyncio
    async def test_identity_regeneration_with_existing_identity(self, db):
        """Lines 62-67: identity regeneration preserves old person/project fields."""
        from claude_memory_kit.tools.reflect import do_reflect
        from claude_memory_kit.types import JournalEntry
        store = _make_store(db)

        # Set existing identity with person and project
        old_card = IdentityCard(
            person="Alice",
            project="AlphaProject",
            content="Old identity content",
            last_updated=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db.set_identity(old_card, user_id="local")

        # Insert recent journal entry
        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc),
            gate=Gate.relational,
            content="Alice mentioned she prefers TypeScript",
        )
        db.insert_journal(entry, user_id="local")

        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_cons.return_value = "Consolidated 1 weeks"
            mock_regen.return_value = "New synthesized identity"
            result = await do_reflect(store, user_id="local")

        identity = db.get_identity(user_id="local")
        assert identity.person == "Alice"
        assert identity.project == "AlphaProject"
        assert identity.content == "New synthesized identity"
        assert "Identity card regenerated." in result

    @pytest.mark.asyncio
    async def test_identity_regeneration_failure(self, db):
        """Lines 73-74: regenerate_identity raises exception."""
        from claude_memory_kit.tools.reflect import do_reflect
        from claude_memory_kit.types import JournalEntry
        store = _make_store(db)

        entry = JournalEntry(
            timestamp=datetime.now(timezone.utc),
            gate=Gate.epistemic,
            content="some recent journal content",
        )
        db.insert_journal(entry, user_id="local")

        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_cons.return_value = None
            mock_regen.side_effect = RuntimeError("Anthropic API down")
            result = await do_reflect(store, user_id="local")
        assert "Identity regeneration failed: Anthropic API down" in result

    @pytest.mark.asyncio
    async def test_identity_regen_no_recent_journal_skips(self, db):
        """Lines 52 (branch): recent_journal returns empty, identity regen skipped."""
        from claude_memory_kit.tools.reflect import do_reflect
        store = _make_store(db)
        # No journal entries, so recent_journal returns empty list
        with patch("claude_memory_kit.tools.reflect.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.reflect.consolidate_journals", new_callable=AsyncMock) as mock_cons, \
             patch("claude_memory_kit.tools.reflect.regenerate_identity", new_callable=AsyncMock) as mock_regen:
            mock_cons.return_value = "Consolidated 1 weeks"
            result = await do_reflect(store, user_id="local")
        # regenerate_identity should not be called since no recent journal
        mock_regen.assert_not_called()
        assert "Identity card regenerated." not in result


# ===========================================================================
# remember.py - coverage gaps
# ===========================================================================


class TestRememberCoverageGaps:
    """Cover missing lines: 103, 120, 138, 151-159."""

    @pytest.mark.asyncio
    async def test_contradiction_check_exception_handled(self, db):
        """Line 103: vector search raises during contradiction check."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        store.vectors.search.side_effect = RuntimeError("contradiction search down")
        result = await do_remember(store, "normal content", "epistemic")
        # Should succeed despite the failure
        assert "Remembered [epistemic]" in result
        assert "high similarity" not in result

    @pytest.mark.asyncio
    async def test_correction_handling_exception(self, db):
        """Line 120: correction gate handling raises exception."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        # First search call (contradiction check) succeeds, second (correction) fails
        call_count = [0]
        def search_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return []  # contradiction check returns empty
            raise RuntimeError("correction search failed")
        store.vectors.search.side_effect = search_side_effect
        result = await do_remember(store, "corrected fact", "correction")
        assert "Remembered [correction]" in result

    @pytest.mark.asyncio
    async def test_memory_chain_exception(self, db):
        """Line 138: memory chain (FOLLOWS edge) creation fails."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)
        # The chain query (lines 127-133) specifically matches
        # "SELECT id FROM memories WHERE id != ? AND created > ?"
        # We need to fail only that query, not auto_link's similar query.
        original_conn = db.conn

        class FailingConn:
            """Proxy that fails only on the chain SELECT query (has 'created >')."""
            def __getattr__(self, name):
                return getattr(original_conn, name)

            def execute(self, sql, params=None):
                if "SELECT id FROM memories" in sql and "created >" in sql:
                    raise RuntimeError("chain query failed")
                if params is not None:
                    return original_conn.execute(sql, params)
                return original_conn.execute(sql)

        # Insert a first memory so there's something to chain to
        result = await do_remember(store, "chain test first", "relational", person="Bob")
        assert "Remembered" in result

        # Now install the failing proxy and try again
        db.conn = FailingConn()
        try:
            result2 = await do_remember(store, "chain test second", "relational", person="Bob")
        finally:
            db.conn = original_conn
        assert "Remembered [relational]" in result2

    @pytest.mark.asyncio
    async def test_sensitivity_classification_non_safe(self, db):
        """Lines 151-159: classify_single returns non-safe/non-unknown level."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        mock_classification = {"level": "sensitive", "reason": "contains salary info"}
        # The imports inside remember.py are:
        #   from ..config import get_api_key  => claude_memory_kit.config.get_api_key
        #   from .classify import classify_single => claude_memory_kit.tools.classify.classify_single
        with patch("claude_memory_kit.config.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify.classify_single", new_callable=AsyncMock) as mock_cls:
            mock_cls.return_value = mock_classification
            result = await do_remember(store, "my salary is 150k", "epistemic")

        assert "SENSITIVITY: sensitive" in result
        assert "contains salary info" in result

    @pytest.mark.asyncio
    async def test_sensitivity_classification_safe_no_warning(self, db):
        """Lines 154: classify_single returns safe level, no warning added."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        mock_classification = {"level": "safe", "reason": "general preference"}
        with patch("claude_memory_kit.config.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify.classify_single", new_callable=AsyncMock) as mock_cls:
            mock_cls.return_value = mock_classification
            result = await do_remember(store, "I prefer Python", "epistemic")

        assert "SENSITIVITY" not in result

    @pytest.mark.asyncio
    async def test_sensitivity_classification_unknown_no_warning(self, db):
        """Lines 154: classify_single returns unknown level, no warning added."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        mock_classification = {"level": "unknown", "reason": "could not determine"}
        with patch("claude_memory_kit.config.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify.classify_single", new_callable=AsyncMock) as mock_cls:
            mock_cls.return_value = mock_classification
            result = await do_remember(store, "something vague", "epistemic")

        assert "SENSITIVITY" not in result

    @pytest.mark.asyncio
    async def test_sensitivity_classification_critical(self, db):
        """Lines 155-158: classify_single returns critical level."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        mock_classification = {"level": "critical", "reason": "contains API key"}
        with patch("claude_memory_kit.config.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify.classify_single", new_callable=AsyncMock) as mock_cls:
            mock_cls.return_value = mock_classification
            result = await do_remember(store, "key is sk-abc123xyz", "epistemic")

        assert "SENSITIVITY: critical" in result
        assert "contains API key" in result

    @pytest.mark.asyncio
    async def test_sensitivity_classification_exception(self, db):
        """Lines 159-160: sensitivity classification raises exception."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        with patch("claude_memory_kit.config.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.classify.classify_single", new_callable=AsyncMock) as mock_cls:
            mock_cls.side_effect = RuntimeError("classify module broken")
            result = await do_remember(store, "some content", "epistemic")

        # Should succeed despite classification failure
        assert "Remembered [epistemic]" in result
        assert "SENSITIVITY" not in result

    @pytest.mark.asyncio
    async def test_sensitivity_no_api_key_skips(self, db):
        """Line 150: api_key is falsy, skips classification."""
        from claude_memory_kit.tools.remember import do_remember
        store = _make_store(db)

        # get_api_key returns empty string (conftest sets ANTHROPIC_API_KEY="")
        result = await do_remember(store, "no key content", "epistemic")
        assert "Remembered [epistemic]" in result
        assert "SENSITIVITY" not in result


# ===========================================================================
# cli_auth.py - coverage gaps
# ===========================================================================


class TestCliAuthCoverageGaps:
    """Cover missing lines in cli_auth.py."""

    # --- _get_login_url (lines 19-20) ---

    def test_get_login_url_default(self, monkeypatch):
        """Lines 19-20: default login URL construction."""
        monkeypatch.delenv("CMK_LOGIN_URL", raising=False)
        url = cli_auth._get_login_url()
        assert "https://cmk.dev/login" in url
        assert f"redirect_uri=http://localhost:{cli_auth.CALLBACK_PORT}/callback" in url

    def test_get_login_url_custom(self, monkeypatch):
        """Lines 19-20: custom login URL via env."""
        monkeypatch.setenv("CMK_LOGIN_URL", "https://custom.dev/auth")
        url = cli_auth._get_login_url()
        assert "https://custom.dev/auth" in url
        assert "redirect_uri=" in url

    # --- get_api_key (lines 52-55) ---

    def test_get_api_key_from_credentials(self, monkeypatch, tmp_path):
        """Lines 52-54: api_key from credentials file."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"api_key": "cmk-sk-test-key-abc", "user_id": "u1"}))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))
        result = cli_auth.get_api_key()
        assert result == "cmk-sk-test-key-abc"

    def test_get_api_key_from_env_fallback(self, monkeypatch, tmp_path):
        """Line 55: no credentials file, falls back to env."""
        creds_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))
        monkeypatch.setenv("CMK_API_KEY", "env-api-key-xyz")
        result = cli_auth.get_api_key()
        assert result == "env-api-key-xyz"

    def test_get_api_key_no_credentials_no_env(self, monkeypatch, tmp_path):
        """Line 55: no credentials and no env var."""
        creds_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))
        monkeypatch.delenv("CMK_API_KEY", raising=False)
        result = cli_auth.get_api_key()
        assert result is None

    def test_get_api_key_creds_without_api_key(self, monkeypatch, tmp_path):
        """Lines 53-55: credentials file exists but has no api_key field."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"user_id": "u1"}))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))
        monkeypatch.setenv("CMK_API_KEY", "fallback-key")
        # creds is truthy (dict with user_id), so creds.get("api_key") returns None
        result = cli_auth.get_api_key()
        assert result is None

    # --- _CallbackHandler.do_GET (lines 64-95) ---

    def test_callback_handler_success(self):
        """Lines 64-90: successful OAuth callback with api_key."""
        handler = cli_auth._CallbackHandler.__new__(cli_auth._CallbackHandler)
        handler.path = "/callback?api_key=cmk-sk-test123&user_id=u1&email=test@test.com"
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        cli_auth._CallbackHandler.result = None
        handler.do_GET()

        assert cli_auth._CallbackHandler.result is not None
        assert cli_auth._CallbackHandler.result["api_key"] == "cmk-sk-test123"
        assert cli_auth._CallbackHandler.result["user_id"] == "u1"
        assert cli_auth._CallbackHandler.result["email"] == "test@test.com"
        handler.send_response.assert_called_with(200)

    def test_callback_handler_missing_api_key(self):
        """Lines 91-95: callback without api_key returns 400."""
        handler = cli_auth._CallbackHandler.__new__(cli_auth._CallbackHandler)
        handler.path = "/callback?user_id=u1"
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        cli_auth._CallbackHandler.result = None
        handler.do_GET()

        assert cli_auth._CallbackHandler.result is None
        handler.send_response.assert_called_with(400)

    def test_callback_handler_wrong_path(self):
        """Lines 65-68: non-callback path returns 404."""
        handler = cli_auth._CallbackHandler.__new__(cli_auth._CallbackHandler)
        handler.path = "/wrong-path"
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        cli_auth._CallbackHandler.result = None
        handler.do_GET()

        handler.send_response.assert_called_with(404)

    def test_callback_handler_partial_params(self):
        """Lines 71-79: callback with api_key but missing user_id and email."""
        handler = cli_auth._CallbackHandler.__new__(cli_auth._CallbackHandler)
        handler.path = "/callback?api_key=cmk-sk-onlythis"
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        cli_auth._CallbackHandler.result = None
        handler.do_GET()

        assert cli_auth._CallbackHandler.result is not None
        assert cli_auth._CallbackHandler.result["api_key"] == "cmk-sk-onlythis"
        assert cli_auth._CallbackHandler.result["user_id"] == ""
        assert cli_auth._CallbackHandler.result["email"] == ""

    # --- log_message suppression (line 98) ---

    def test_callback_handler_log_message_suppressed(self):
        """Line 98: log_message does nothing."""
        handler = cli_auth._CallbackHandler.__new__(cli_auth._CallbackHandler)
        # Should not raise
        handler.log_message("GET /callback 200")

    # --- do_login (lines 103-137) ---

    def test_do_login_already_logged_in(self, monkeypatch, tmp_path, capsys):
        """Lines 103-107: already logged in, shows message and returns."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({
            "api_key": "cmk-sk-existing",
            "user_id": "u1",
            "email": "existing@test.com",
        }))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_login()
        captured = capsys.readouterr()
        assert "Already logged in" in captured.out
        assert "existing@test.com" in captured.out

    def test_do_login_successful_callback(self, monkeypatch, tmp_path, capsys):
        """Lines 109-135: full login flow with successful callback."""
        creds_dir = tmp_path / "creds"
        creds_file = creds_dir / "credentials.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_DIR", str(creds_dir))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth._CallbackHandler.result = None

        mock_server = MagicMock()
        mock_server.handle_request.side_effect = lambda: setattr(
            cli_auth._CallbackHandler, "result",
            {"api_key": "cmk-sk-new-key", "user_id": "new-user", "email": "new@test.com"}
        )

        with patch("claude_memory_kit.cli_auth.HTTPServer", return_value=mock_server), \
             patch("webbrowser.open"), \
             patch.object(cli_auth, "_check_local_data_hint"):
            cli_auth.do_login()

        captured = capsys.readouterr()
        assert "Logged in as new@test.com" in captured.out

    def test_do_login_timeout(self, monkeypatch, tmp_path, capsys):
        """Lines 136-137: login times out (callback result stays falsy)."""
        creds_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth._CallbackHandler.result = None

        call_count = [0]
        def handle_once():
            call_count[0] += 1
            if call_count[0] > 1:
                # Set result to a falsy non-None value to break the while loop
                # while _CallbackHandler.result is None => exits when not None
                # if _CallbackHandler.result => False is falsy, so goes to else
                cli_auth._CallbackHandler.result = False

        mock_server = MagicMock()
        mock_server.handle_request.side_effect = handle_once

        with patch("claude_memory_kit.cli_auth.HTTPServer", return_value=mock_server), \
             patch("webbrowser.open"):
            cli_auth.do_login()

        captured = capsys.readouterr()
        assert "timed out" in captured.out or "cancelled" in captured.out

    # --- _check_local_data_hint (lines 142-153) ---

    def test_check_local_data_hint_with_data(self, monkeypatch, tmp_path, capsys):
        """Lines 142-151: local data exists, shows hint."""
        mock_db = MagicMock()
        mock_db.count_memories.return_value = 5

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db):
            cli_auth._check_local_data_hint()

        captured = capsys.readouterr()
        assert "5 local memories" in captured.out
        assert "cmk claim" in captured.out

    def test_check_local_data_hint_no_data(self, monkeypatch, tmp_path, capsys):
        """Lines 148: count is 0, no hint shown."""
        mock_db = MagicMock()
        mock_db.count_memories.return_value = 0

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db):
            cli_auth._check_local_data_hint()

        captured = capsys.readouterr()
        assert "local memories" not in captured.out

    def test_check_local_data_hint_exception(self, monkeypatch, capsys):
        """Lines 152-153: exception silently caught."""
        with patch("claude_memory_kit.config.get_store_path", side_effect=RuntimeError("boom")):
            cli_auth._check_local_data_hint()
        # Should not raise, should produce no output
        captured = capsys.readouterr()
        assert "local memories" not in captured.out

    # --- _find_claude_config_path (lines 158-166) ---

    def test_find_claude_config_path_found(self, tmp_path):
        """Lines 158-165: config file found at first candidate."""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("{}")

        def fake_expanduser(path):
            if "Library" in path:
                return str(config_file)
            return str(tmp_path / "nonexistent")

        with patch("os.path.expanduser", side_effect=fake_expanduser):
            result = cli_auth._find_claude_config_path()
        assert result == str(config_file)

    def test_find_claude_config_path_not_found(self, tmp_path):
        """Line 166: no config file found, returns None."""
        def fake_expanduser(path):
            return str(tmp_path / "nonexistent" / os.path.basename(path))

        with patch("os.path.expanduser", side_effect=fake_expanduser):
            result = cli_auth._find_claude_config_path()
        assert result is None

    # --- _write_mcp_config (lines 175-212) ---

    def test_write_mcp_config_desktop_config_found(self, tmp_path):
        """Lines 175-196: writes to Claude Desktop config."""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=str(config_file)):
            result = cli_auth._write_mcp_config("user-123")

        assert result == str(config_file)
        data = json.loads(config_file.read_text())
        assert "memory" in data["mcpServers"]
        assert data["mcpServers"]["memory"]["env"]["CMK_USER_ID"] == "user-123"

    def test_write_mcp_config_desktop_config_corrupt(self, tmp_path):
        """Lines 189-190: corrupt desktop config gets overwritten."""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text("this is not json{{{")

        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=str(config_file)):
            result = cli_auth._write_mcp_config("user-456")

        assert result == str(config_file)
        data = json.loads(config_file.read_text())
        assert "memory" in data["mcpServers"]

    def test_write_mcp_config_desktop_no_mcp_servers(self, tmp_path):
        """Lines 191-193: desktop config exists but has no mcpServers key."""
        config_file = tmp_path / "claude_desktop_config.json"
        config_file.write_text(json.dumps({"theme": "dark"}))

        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=str(config_file)):
            result = cli_auth._write_mcp_config("user-789")

        data = json.loads(config_file.read_text())
        assert "mcpServers" in data
        assert "memory" in data["mcpServers"]
        assert data["theme"] == "dark"

    def test_write_mcp_config_fallback_local(self, tmp_path, monkeypatch):
        """Lines 198-212: no desktop config, writes .mcp.json locally."""
        monkeypatch.chdir(tmp_path)
        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=None):
            result = cli_auth._write_mcp_config("user-local")

        assert result == str(tmp_path / ".mcp.json")
        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert "memory" in data["mcpServers"]

    def test_write_mcp_config_fallback_local_existing(self, tmp_path, monkeypatch):
        """Lines 201-206: existing .mcp.json gets updated."""
        monkeypatch.chdir(tmp_path)
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        (tmp_path / ".mcp.json").write_text(json.dumps(existing))

        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=None):
            result = cli_auth._write_mcp_config("user-merge")

        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert "other-tool" in data["mcpServers"]
        assert "memory" in data["mcpServers"]

    def test_write_mcp_config_fallback_local_corrupt(self, tmp_path, monkeypatch):
        """Lines 205-206: corrupt .mcp.json gets overwritten."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mcp.json").write_text("broken{{{json")

        with patch("claude_memory_kit.cli_auth._find_claude_config_path", return_value=None):
            result = cli_auth._write_mcp_config("user-fix")

        data = json.loads((tmp_path / ".mcp.json").read_text())
        assert "memory" in data["mcpServers"]

    # --- do_init (lines 217-278) ---

    def test_do_init_invalid_key_prefix(self, capsys):
        """Lines 217-219: API key with wrong prefix."""
        cli_auth.do_init("wrong-prefix-key")
        captured = capsys.readouterr()
        assert "Invalid API key" in captured.out
        assert "cmk-sk-" in captured.out

    def test_do_init_valid_key_local_validation(self, tmp_path, monkeypatch, capsys):
        """Lines 220-278: key validated locally, credentials saved, MCP written."""
        creds_dir = tmp_path / "creds"
        creds_file = creds_dir / "credentials.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_DIR", str(creds_dir))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        fake_user = {"id": "validated-user", "email": "v@test.com", "name": "Val"}

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=fake_user), \
             patch("claude_memory_kit.cli_auth._write_mcp_config", return_value=str(tmp_path / "config.json")), \
             patch("claude_memory_kit.cli_auth._check_local_data_hint"):

            cli_auth.do_init("cmk-sk-valid-key-1234567890abcdef")

        captured = capsys.readouterr()
        assert "Authenticated as v@test.com" in captured.out
        assert "MCP config written" in captured.out
        assert "Ready" in captured.out

    def test_do_init_key_not_in_local_db_fetch_from_api(self, tmp_path, monkeypatch, capsys):
        """Lines 231-244: key not in local DB, fetches from API."""
        creds_dir = tmp_path / "creds"
        creds_file = creds_dir / "credentials.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_DIR", str(creds_dir))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        fake_user_from_api = {"id": "api-user", "email": "api@test.com"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": fake_user_from_api}

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=None), \
             patch("httpx.get", return_value=mock_response), \
             patch("claude_memory_kit.cli_auth._write_mcp_config", return_value=str(tmp_path / "config.json")), \
             patch("claude_memory_kit.cli_auth._check_local_data_hint"):

            cli_auth.do_init("cmk-sk-remote-key-1234567890abcdef")

        captured = capsys.readouterr()
        assert "Authenticated as api@test.com" in captured.out

    def test_do_init_key_not_validated_anywhere(self, tmp_path, monkeypatch, capsys):
        """Lines 246-249: key cannot be validated locally or remotely."""
        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=None), \
             patch("httpx.get", side_effect=RuntimeError("connection refused")):

            cli_auth.do_init("cmk-sk-bad-key-1234567890abcdef12")

        captured = capsys.readouterr()
        assert "Could not validate API key" in captured.out

    def test_do_init_api_returns_no_user(self, tmp_path, monkeypatch, capsys):
        """Lines 240-244, 246: API returns 200 but no user data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": None}

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=None), \
             patch("httpx.get", return_value=mock_response):

            cli_auth.do_init("cmk-sk-nouser-key-12345678901234")

        captured = capsys.readouterr()
        assert "Could not validate API key" in captured.out

    def test_do_init_api_returns_non_200(self, tmp_path, monkeypatch, capsys):
        """Lines 240: API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=None), \
             patch("httpx.get", return_value=mock_response):

            cli_auth.do_init("cmk-sk-unauthorized-1234567890ab")

        captured = capsys.readouterr()
        assert "Could not validate API key" in captured.out

    def test_do_init_no_mcp_config_written(self, tmp_path, monkeypatch, capsys):
        """Lines 264-272: _write_mcp_config returns None, shows manual instructions."""
        creds_dir = tmp_path / "creds"
        creds_file = creds_dir / "credentials.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_DIR", str(creds_dir))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        fake_user = {"id": "manual-user", "email": "m@test.com"}

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=fake_user), \
             patch("claude_memory_kit.cli_auth._write_mcp_config", return_value=None), \
             patch("claude_memory_kit.cli_auth._check_local_data_hint"):

            cli_auth.do_init("cmk-sk-manual-key-1234567890abcd")

        captured = capsys.readouterr()
        assert "Add this to your Claude MCP config manually" in captured.out
        assert "manual-user" in captured.out

    def test_do_init_user_without_email(self, tmp_path, monkeypatch, capsys):
        """Line 258: user has id but no email."""
        creds_dir = tmp_path / "creds"
        creds_file = creds_dir / "credentials.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_DIR", str(creds_dir))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        fake_user = {"id": "no-email-user"}

        mock_db = MagicMock()

        with patch("claude_memory_kit.config.get_store_path", return_value=str(tmp_path / "store")), \
             patch("claude_memory_kit.store.sqlite.SqliteStore", return_value=mock_db), \
             patch("claude_memory_kit.auth_keys.validate_api_key", return_value=fake_user), \
             patch("claude_memory_kit.cli_auth._write_mcp_config", return_value=str(tmp_path / "config.json")), \
             patch("claude_memory_kit.cli_auth._check_local_data_hint"):

            cli_auth.do_init("cmk-sk-noemail-key-123456789012")

        captured = capsys.readouterr()
        assert "Authenticated as no-email-user" in captured.out

    # --- do_logout (lines 283-287) ---

    def test_do_logout_with_credentials(self, tmp_path, monkeypatch, capsys):
        """Lines 283-285: credentials file exists, remove it."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"api_key": "cmk-sk-logout"}))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_logout()

        assert not creds_file.exists()
        captured = capsys.readouterr()
        assert "Logged out" in captured.out
        assert "local mode" in captured.out

    def test_do_logout_no_credentials(self, tmp_path, monkeypatch, capsys):
        """Lines 286-287: no credentials file."""
        creds_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_logout()

        captured = capsys.readouterr()
        assert "Not logged in" in captured.out

    # --- do_whoami (lines 292-302) ---

    def test_do_whoami_logged_in(self, tmp_path, monkeypatch, capsys):
        """Lines 292-298: user is logged in."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({
            "api_key": "cmk-sk-whoami-key-123456",
            "user_id": "u1",
            "email": "who@test.com",
        }))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_whoami()

        captured = capsys.readouterr()
        assert "Logged in as: who@test.com" in captured.out
        # key_preview is first 12 chars + "..." => "cmk-sk-whoam..."
        assert "cmk-sk-whoam" in captured.out
        assert "Mode: cloud" in captured.out

    def test_do_whoami_not_logged_in(self, tmp_path, monkeypatch, capsys):
        """Lines 299-302: user is not logged in."""
        creds_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_whoami()

        captured = capsys.readouterr()
        assert "Not logged in" in captured.out
        assert "Mode: local" in captured.out
        assert "cmk login" in captured.out

    def test_do_whoami_credentials_no_api_key(self, tmp_path, monkeypatch, capsys):
        """Lines 293: credentials exist but no api_key field."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps({"user_id": "u1"}))
        monkeypatch.setattr(cli_auth, "CREDENTIALS_FILE", str(creds_file))

        cli_auth.do_whoami()

        captured = capsys.readouterr()
        assert "Not logged in" in captured.out
        assert "Mode: local" in captured.out


# ===========================================================================
# identity.py - lines 51, 55, 60, 112
# ===========================================================================


class TestIdentityCoverageGaps:
    """Cover onboarding resume paths where state exists but onboard_response is None."""

    @pytest.mark.asyncio
    async def test_state_exists_no_response_step0(self, db):
        """Line 55: onboarding at step 0, no response returns COLD_START."""
        from claude_memory_kit.tools.identity import do_identity, COLD_START
        from claude_memory_kit.types import OnboardingState
        store = _make_store(db)
        db.set_onboarding(OnboardingState(step=0), user_id="local")
        result = await do_identity(store, onboard_response=None, user_id="local")
        assert result == COLD_START

    @pytest.mark.asyncio
    async def test_state_none_response_given_creates_state(self, db):
        """Line 51: state is None but onboard_response provided, creates default state."""
        from claude_memory_kit.tools.identity import do_identity
        store = _make_store(db)
        # No onboarding state exists, but user gives a response
        result = await do_identity(store, onboard_response="Alice", user_id="local")
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_state_exists_no_response_step1(self, db):
        """Line 55: onboarding at step 1, no response returns step 2 prompt."""
        from claude_memory_kit.tools.identity import do_identity
        from claude_memory_kit.types import OnboardingState
        store = _make_store(db)
        db.set_onboarding(OnboardingState(step=1, person="Bob"), user_id="local")
        result = await do_identity(store, onboard_response=None, user_id="local")
        assert "Bob" in result

    @pytest.mark.asyncio
    async def test_state_exists_no_response_step2(self, db):
        """Line 60 (via 59): onboarding at step 2, no response returns step 3 prompt."""
        from claude_memory_kit.tools.identity import do_identity, STEP_3_TEMPLATE
        from claude_memory_kit.types import OnboardingState
        store = _make_store(db)
        db.set_onboarding(OnboardingState(step=2, person="Carol", project="foo"), user_id="local")
        result = await do_identity(store, onboard_response=None, user_id="local")
        assert result == STEP_3_TEMPLATE

    @pytest.mark.asyncio
    async def test_state_exists_no_response_step_invalid(self, db):
        """Line 60: onboarding at step >= 3, no response returns cold start."""
        from claude_memory_kit.tools.identity import do_identity, COLD_START
        from claude_memory_kit.types import OnboardingState
        store = _make_store(db)
        db.set_onboarding(OnboardingState(step=99), user_id="local")
        result = await do_identity(store, onboard_response=None, user_id="local")
        assert result == COLD_START

    @pytest.mark.asyncio
    async def test_step3_response_falls_through(self, db):
        """Line 112: step >= 3 with onboard_response falls through to COLD_START."""
        from claude_memory_kit.tools.identity import do_identity, COLD_START
        from claude_memory_kit.types import OnboardingState
        store = _make_store(db)
        db.set_onboarding(OnboardingState(step=3, person="Dave", project="proj", style="fast"), user_id="local")
        result = await do_identity(store, onboard_response="extra response", user_id="local")
        assert result == COLD_START


# ===========================================================================
# recall.py - fallback exception paths
# ===========================================================================


class TestRecallCoverageGaps:
    """Cover both cloud and local fallback exception paths."""

    @pytest.mark.asyncio
    async def test_cloud_text_search_exception(self, db):
        """Cloud text search fallback raises exception."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = True
        store.vectors._disabled = False
        store.vectors.search.return_value = []
        store.vectors.search_text = MagicMock(side_effect=RuntimeError("text index broken"))
        result = await do_recall(store, "test query", user_id="local")
        assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_local_fts5_exception(self, db):
        """Local FTS5 fallback raises exception."""
        from claude_memory_kit.tools.recall import do_recall
        store = _make_store(db)
        store.vectors._cloud = False
        store.vectors._disabled = False
        store.vectors.search.return_value = []
        original_search_fts = db.search_fts
        db.search_fts = MagicMock(side_effect=RuntimeError("FTS broken"))
        try:
            result = await do_recall(store, "test query", user_id="local")
        finally:
            db.search_fts = original_search_fts
        assert "No memories found" in result


# ===========================================================================
# reflect.py - line 77 (empty report - dead code, mark pragma)
# ===========================================================================

# Line 77 in reflect.py ("if not report: return ...") is unreachable:
# The consolidation block (lines 19-28) always appends at least one item.
# This will be marked with pragma: no cover in the source.


# ===========================================================================
# digest.py - lines 36, 56 (empty combined, no digests written)
# ===========================================================================


class TestDigestCoverageGaps:
    """Cover empty combined entries and no digests written paths."""

    @pytest.mark.asyncio
    async def test_empty_combined_entries_skips_week(self, db):
        """Line 36: combined list is empty for a week (journal_by_date returns empty)."""
        from claude_memory_kit.consolidation.digest import consolidate_journals
        db.stale_journal_dates = MagicMock(return_value=["2025-01-01"])
        db.journal_by_date = MagicMock(return_value=[])
        result = await consolidate_journals(db, api_key="test-key", user_id="local")
        assert result is None

    @pytest.mark.asyncio
    async def test_all_weeks_empty_returns_none(self, db):
        """Line 56: digests_written is empty after processing all weeks."""
        from claude_memory_kit.consolidation.digest import consolidate_journals
        db.stale_journal_dates = MagicMock(return_value=["2025-01-06", "2025-01-07"])
        db.journal_by_date = MagicMock(return_value=[])
        result = await consolidate_journals(db, api_key="test-key", user_id="local")
        assert result is None


# ===========================================================================
# auto_extract.py - line 34 (log warning on save failure)
# ===========================================================================


class TestAutoExtractCoverageGaps:
    """Cover the exception during individual memory save."""

    @pytest.mark.asyncio
    async def test_save_failure_logs_warning(self, db):
        """Line 34-35: do_remember raises during auto-extract loop."""
        from claude_memory_kit.tools.auto_extract import do_auto_extract
        store = _make_store(db)

        mock_memories = [
            {"content": "good memory", "gate": "epistemic"},
            {"content": "bad memory", "gate": "relational"},
        ]
        with patch("claude_memory_kit.tools.auto_extract.get_api_key", return_value="test-key"), \
             patch("claude_memory_kit.tools.auto_extract.extract_memories", new_callable=AsyncMock) as mock_extract, \
             patch("claude_memory_kit.tools.auto_extract.do_remember", new_callable=AsyncMock) as mock_remember:
            mock_extract.return_value = mock_memories
            mock_remember.side_effect = ["Saved memory 1", RuntimeError("save failed")]
            result = await do_auto_extract(store, "some transcript", user_id="local")
        assert "Auto-extracted 1 memories" in result


# ===========================================================================
# sqlite.py - lines 221-227 (FTS update trigger creation)
# ===========================================================================


class TestSqliteFtsTrigger:
    """Cover the FTS update trigger creation path."""

    def test_fts_trigger_created_when_missing(self, db):
        """Lines 221-227: FTS table exists but update trigger doesn't."""
        db.conn.execute("DROP TRIGGER IF EXISTS memories_au")
        db.conn.commit()
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='memories_au'"
        ).fetchone()
        assert row is None
        db._ensure_fts_update_trigger()
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='memories_au'"
        ).fetchone()
        assert row is not None
        assert row[0] == "memories_au"

    def test_fts_trigger_skipped_when_no_fts_table(self, tmp_path):
        """Lines 225-226: FTS table doesn't exist, trigger creation skipped."""
        from claude_memory_kit.store.sqlite import SqliteStore
        import sqlite3
        store_dir = str(tmp_path / "bare_store")
        os.makedirs(store_dir, exist_ok=True)
        db_path = os.path.join(store_dir, "index.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT)")
        conn.commit()
        conn.close()
        # Create store (init just connects, doesn't migrate)
        store = SqliteStore(store_dir)
        # No FTS table exists, trigger shouldn't be created
        store._ensure_fts_update_trigger()
        row = store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='memories_au'"
        ).fetchone()
        assert row is None
