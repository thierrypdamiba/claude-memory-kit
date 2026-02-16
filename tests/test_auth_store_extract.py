"""Tests covering missing lines in auth.py, store/__init__.py, and extract.py."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from claude_memory_kit import auth as auth_module
from claude_memory_kit import extract as extract_module


# ===========================================================================
# auth.py -- missing lines: 39, 54, 58, 64-78, 83-105, 129-163, 171-178
# ===========================================================================


class TestIsAuthEnabledTrue:
    """Cover line 39: is_auth_enabled returns True."""

    def test_auth_enabled_with_frontend_api(self, monkeypatch):
        monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_realkey123")
        monkeypatch.setenv("CLERK_FRONTEND_API", "my-app.clerk.accounts.dev")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        assert auth_module.is_auth_enabled() is True

    def test_auth_enabled_with_instance_id(self, monkeypatch):
        monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_realkey123")
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "ins_abc123")
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        assert auth_module.is_auth_enabled() is True


class TestGetJwksUrl:
    """Cover lines 54 and 58: _get_jwks_url returns URL from CLERK_FRONTEND_API or CLERK_INSTANCE_ID."""

    def test_jwks_url_from_frontend_api(self, monkeypatch):
        monkeypatch.setenv("CLERK_FRONTEND_API", "my-app.clerk.accounts.dev")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "")
        url = auth_module._get_jwks_url()
        assert url == "https://my-app.clerk.accounts.dev/.well-known/jwks.json"

    def test_jwks_url_from_instance_id(self, monkeypatch):
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "ins_abc123")
        monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "")
        url = auth_module._get_jwks_url()
        assert url == "https://ins_abc123.clerk.accounts.dev/.well-known/jwks.json"

    def test_jwks_url_empty(self, monkeypatch):
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "")
        url = auth_module._get_jwks_url()
        assert url == ""


class TestGetJwkClient:
    """Cover lines 64-78: _get_jwk_client caching, creation, and error handling."""

    def test_returns_cached_client(self, monkeypatch):
        mock_client = MagicMock()
        monkeypatch.setattr(auth_module, "_jwk_client", mock_client)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", time.time())
        result = auth_module._get_jwk_client()
        assert result is mock_client

    def test_returns_none_when_no_url(self, monkeypatch):
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        result = auth_module._get_jwk_client()
        assert result is None

    @patch("claude_memory_kit.auth.PyJWKClient")
    def test_creates_new_client(self, mock_pyjwk_cls, monkeypatch):
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        monkeypatch.setenv("CLERK_FRONTEND_API", "my-app.clerk.accounts.dev")
        mock_pyjwk_cls.return_value = MagicMock()
        result = auth_module._get_jwk_client()
        assert result is not None
        mock_pyjwk_cls.assert_called_once_with(
            "https://my-app.clerk.accounts.dev/.well-known/jwks.json",
            cache_keys=True,
        )

    @patch("claude_memory_kit.auth.PyJWKClient")
    def test_returns_none_on_exception(self, mock_pyjwk_cls, monkeypatch):
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        monkeypatch.setenv("CLERK_FRONTEND_API", "my-app.clerk.accounts.dev")
        mock_pyjwk_cls.side_effect = Exception("network error")
        result = auth_module._get_jwk_client()
        assert result is None

    def test_cache_expired_refetches(self, monkeypatch):
        """When cache TTL has expired, _get_jwk_client should refetch."""
        monkeypatch.setattr(auth_module, "_jwk_client", MagicMock())
        # Set cache time far in the past so it's expired
        monkeypatch.setattr(auth_module, "_jwk_cache_time", time.time() - 7200)
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        # No URL available, so it should return None after expiry
        result = auth_module._get_jwk_client()
        assert result is None

    def test_lock_double_check_returns_cached(self, monkeypatch):
        """Double-check inside lock returns cached client if refreshed by another thread."""
        mock_client = MagicMock()
        # Set expired cache so the outer check passes
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        monkeypatch.setenv("CLERK_FRONTEND_API", "my-app.clerk.accounts.dev")
        # Simulate another thread refreshing the client between outer check and lock acquisition
        original_lock = auth_module._jwk_lock

        class FakeContext:
            def __enter__(self_inner):
                original_lock.__enter__()
                # Simulate another thread having refreshed the client
                auth_module._jwk_client = mock_client
                auth_module._jwk_cache_time = time.time()
                return self_inner

            def __exit__(self_inner, *args):
                return original_lock.__exit__(*args)

        monkeypatch.setattr(auth_module, "_jwk_lock", FakeContext())
        result = auth_module._get_jwk_client()
        assert result is mock_client


class TestVerifyClerkToken:
    """Cover lines 83-105: verify_clerk_token success, expired, invalid, and no client."""

    def test_returns_none_when_no_client(self, monkeypatch):
        monkeypatch.setattr(auth_module, "_jwk_client", None)
        monkeypatch.setattr(auth_module, "_jwk_cache_time", 0)
        monkeypatch.setenv("CLERK_FRONTEND_API", "")
        monkeypatch.setenv("CLERK_INSTANCE_ID", "")
        result = auth_module.verify_clerk_token("some-token")
        assert result is None

    @patch("claude_memory_kit.auth._get_jwk_client")
    @patch("claude_memory_kit.auth.jwt.decode")
    def test_returns_claims_on_success(self, mock_decode, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_signing_key = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_decode.return_value = {
            "sub": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        result = auth_module.verify_clerk_token("valid-token")
        assert result == {
            "id": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_decode.assert_called_once_with(
            "valid-token",
            mock_signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

    @patch("claude_memory_kit.auth._get_jwk_client")
    @patch("claude_memory_kit.auth.jwt.decode")
    def test_returns_none_on_expired(self, mock_decode, mock_get_client):
        import jwt as jwt_lib

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
        mock_decode.side_effect = jwt_lib.ExpiredSignatureError("expired")
        result = auth_module.verify_clerk_token("expired-token")
        assert result is None

    @patch("claude_memory_kit.auth._get_jwk_client")
    @patch("claude_memory_kit.auth.jwt.decode")
    def test_returns_none_on_invalid_token(self, mock_decode, mock_get_client):
        import jwt as jwt_lib

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
        mock_decode.side_effect = jwt_lib.InvalidTokenError("bad token")
        result = auth_module.verify_clerk_token("invalid-token")
        assert result is None


class TestGetCurrentUserAuthEnabled:
    """Cover lines 129-163: get_current_user when auth IS enabled."""

    @pytest.mark.asyncio
    async def test_raises_401_no_token(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {}
        with pytest.raises(HTTPException) as exc_info:
            await auth_module.get_current_user(request)
        assert exc_info.value.status_code == 401
        assert "authorization required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_api_key_valid(self, monkeypatch, db):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer cmk-sk-fakekey123"}

        mock_validate = MagicMock(return_value={
            "id": "user_api",
            "email": "api@test.com",
            "name": "API User",
            "plan": "pro",
        })
        with patch("claude_memory_kit.auth_keys.validate_api_key", mock_validate):
            result = await auth_module.get_current_user(request, db)
        assert result["id"] == "user_api"

    @pytest.mark.asyncio
    async def test_api_key_invalid_raises_401(self, monkeypatch, db):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer cmk-sk-badkey"}

        mock_validate = MagicMock(return_value=None)
        with patch("claude_memory_kit.auth_keys.validate_api_key", mock_validate):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module.get_current_user(request, db)
            assert exc_info.value.status_code == 401
            assert "invalid API key" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_clerk_jwt_valid_with_db(self, monkeypatch, db):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer jwt-token-abc"}

        mock_verify = MagicMock(return_value={
            "id": "clerk_user_1",
            "email": "clerk@test.com",
            "name": "Clerk User",
        })
        monkeypatch.setattr(auth_module, "verify_clerk_token", mock_verify)
        result = await auth_module.get_current_user(request, db)
        assert result["id"] == "clerk_user_1"
        assert result["email"] == "clerk@test.com"
        assert result["plan"] == "free"

    @pytest.mark.asyncio
    async def test_clerk_jwt_valid_with_stored_plan(self, monkeypatch, db):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer jwt-token-abc"}

        # Pre-create user with a plan in the db
        db.upsert_user("clerk_user_2", "clerk2@test.com", "Clerk User 2")
        # Manually update the plan
        db.conn.execute(
            "UPDATE users SET plan = ? WHERE id = ?", ("pro", "clerk_user_2")
        )
        db.conn.commit()

        mock_verify = MagicMock(return_value={
            "id": "clerk_user_2",
            "email": "clerk2@test.com",
            "name": "Clerk User 2",
        })
        monkeypatch.setattr(auth_module, "verify_clerk_token", mock_verify)
        result = await auth_module.get_current_user(request, db)
        assert result["id"] == "clerk_user_2"
        assert result["plan"] == "pro"

    @pytest.mark.asyncio
    async def test_clerk_jwt_valid_no_db(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer jwt-token-no-db"}

        mock_verify = MagicMock(return_value={
            "id": "clerk_user_3",
            "email": "clerk3@test.com",
            "name": "No DB User",
        })
        monkeypatch.setattr(auth_module, "verify_clerk_token", mock_verify)
        result = await auth_module.get_current_user(request, db=None)
        assert result["id"] == "clerk_user_3"
        assert result["plan"] == "free"

    @pytest.mark.asyncio
    async def test_clerk_jwt_invalid_raises_401(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer bad-jwt-token"}

        mock_verify = MagicMock(return_value=None)
        monkeypatch.setattr(auth_module, "verify_clerk_token", mock_verify)
        with pytest.raises(HTTPException) as exc_info:
            await auth_module.get_current_user(request)
        assert exc_info.value.status_code == 401
        assert "invalid token" in str(exc_info.value.detail)


class TestOptionalAuthEnabled:
    """Cover lines 171-178: optional_auth when auth IS enabled."""

    @pytest.mark.asyncio
    async def test_returns_none_no_token(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {}
        result = await auth_module.optional_auth(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_on_valid_token(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer valid-jwt"}

        expected_user = {
            "id": "opt_user",
            "email": "opt@test.com",
            "name": "Opt User",
            "plan": "free",
        }
        mock_get_user = AsyncMock(return_value=expected_user)
        monkeypatch.setattr(auth_module, "get_current_user", mock_get_user)
        result = await auth_module.optional_auth(request)
        assert result == expected_user

    @pytest.mark.asyncio
    async def test_returns_none_on_http_exception(self, monkeypatch):
        monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
        request = MagicMock()
        request.headers = {"authorization": "Bearer bad-jwt"}

        mock_get_user = AsyncMock(side_effect=HTTPException(401, "invalid"))
        monkeypatch.setattr(auth_module, "get_current_user", mock_get_user)
        result = await auth_module.optional_auth(request)
        assert result is None


# ===========================================================================
# store/__init__.py -- missing lines: 9-11, 14-15, 19-23, 27-29
# ===========================================================================


class TestStoreInit:
    """Cover Store class: __init__, init, count_user_data, migrate_user_data."""

    @patch("claude_memory_kit.store.QdrantStore")
    @patch("claude_memory_kit.store.SqliteStore")
    def test_store_constructor(self, mock_sqlite_cls, mock_qdrant_cls):
        from claude_memory_kit.store import Store

        store = Store("/tmp/test-store")
        assert store.path == "/tmp/test-store"
        mock_sqlite_cls.assert_called_once_with("/tmp/test-store")
        mock_qdrant_cls.assert_called_once_with("/tmp/test-store")
        assert store.auth_db is mock_sqlite_cls.return_value
        assert store.qdrant is mock_qdrant_cls.return_value

    @pytest.mark.asyncio
    @patch("claude_memory_kit.store.QdrantStore")
    @patch("claude_memory_kit.store.SqliteStore")
    async def test_store_init(self, mock_sqlite_cls, mock_qdrant_cls):
        from claude_memory_kit.store import Store

        store = Store("/tmp/test-store")
        await store.init()
        store.auth_db.migrate.assert_called_once()
        store.qdrant.ensure_collection.assert_called_once()

    @patch("claude_memory_kit.store.QdrantStore")
    @patch("claude_memory_kit.store.SqliteStore")
    def test_count_user_data(self, mock_sqlite_cls, mock_qdrant_cls):
        from claude_memory_kit.store import Store

        store = Store("/tmp/test-store")
        store.qdrant.count_memories.return_value = 5
        counts = store.count_user_data("user_1")
        store.qdrant.count_memories.assert_called_once_with(user_id="user_1")
        assert counts["memories"] == 5
        assert counts["total"] == 5

    @patch("claude_memory_kit.store.QdrantStore")
    @patch("claude_memory_kit.store.SqliteStore")
    def test_migrate_user_data(self, mock_sqlite_cls, mock_qdrant_cls):
        from claude_memory_kit.store import Store

        store = Store("/tmp/test-store")
        store.qdrant.migrate_user_id.return_value = 5

        result = store.migrate_user_data("old_user", "new_user")
        store.qdrant.migrate_user_id.assert_called_once_with("old_user", "new_user")
        assert result["memories"] == 5
        assert result["total"] == 5


# ===========================================================================
# extract.py -- missing lines: 39-59, 65-82, 97
# ===========================================================================


class TestCallAnthropic:
    """Cover lines 39-59: _call_anthropic success and failure paths."""

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract.get_model", return_value="claude-opus-4-6")
    @patch("claude_memory_kit.extract.httpx.AsyncClient")
    async def test_call_anthropic_success(self, mock_client_cls, mock_get_model):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "extracted result"}]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await extract_module._call_anthropic(
            "system prompt", "user message", "sk-ant-test-key"
        )
        assert result == "extracted result"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["headers"]["x-api-key"] == "sk-ant-test-key"
        assert call_kwargs[1]["json"]["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract.get_model", return_value="claude-opus-4-6")
    @patch("claude_memory_kit.extract.httpx.AsyncClient")
    async def test_call_anthropic_failure(self, mock_client_cls, mock_get_model):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="anthropic api failed"):
            await extract_module._call_anthropic(
                "system prompt", "user message", "sk-ant-test-key"
            )

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract.get_model", return_value="claude-opus-4-6")
    @patch("claude_memory_kit.extract.httpx.AsyncClient")
    async def test_call_anthropic_custom_max_tokens(self, mock_client_cls, mock_get_model):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "result"}]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await extract_module._call_anthropic(
            "sys", "user", "key", max_tokens=512
        )
        assert result == "result"
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["json"]["max_tokens"] == 512


class TestExtractMemories:
    """Cover lines 65-82: extract_memories JSON parsing including fallback."""

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_extract_memories_valid_json(self, mock_call):
        mock_call.return_value = json.dumps([
            {"gate": "relational", "content": "likes coffee", "person": "Alice", "project": None}
        ])
        result = await extract_module.extract_memories("some transcript", "key")
        assert len(result) == 1
        assert result[0]["gate"] == "relational"
        assert result[0]["content"] == "likes coffee"

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_extract_memories_empty_array(self, mock_call):
        mock_call.return_value = "[]"
        result = await extract_module.extract_memories("boring transcript", "key")
        assert result == []

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_extract_memories_json_with_surrounding_text(self, mock_call):
        mock_call.return_value = 'Here are the memories:\n[{"gate": "epistemic", "content": "learned something"}]\nEnd.'
        result = await extract_module.extract_memories("transcript", "key")
        assert len(result) == 1
        assert result[0]["gate"] == "epistemic"

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_extract_memories_completely_invalid_json(self, mock_call):
        mock_call.return_value = "No memories found in this conversation."
        result = await extract_module.extract_memories("transcript", "key")
        assert result == []

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_extract_memories_partial_json_still_invalid(self, mock_call):
        mock_call.return_value = 'text [not valid json{ ] more text'
        result = await extract_module.extract_memories("transcript", "key")
        assert result == []


class TestConsolidateEntries:
    """Cover consolidate_entries (calls _call_anthropic)."""

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_consolidate_entries(self, mock_call):
        mock_call.return_value = "Consolidated digest of journal entries."
        result = await extract_module.consolidate_entries("entry1\nentry2", "key")
        assert result == "Consolidated digest of journal entries."
        mock_call.assert_called_once_with(
            extract_module.CONSOLIDATION_PROMPT,
            "Journal entries:\nentry1\nentry2",
            "key",
            max_tokens=1024,
        )


class TestRegenerateIdentity:
    """Cover line 97: regenerate_identity calls _call_anthropic."""

    @pytest.mark.asyncio
    @patch("claude_memory_kit.extract._call_anthropic")
    async def test_regenerate_identity(self, mock_call):
        mock_call.return_value = "I am Claude, working with Alice on project X."
        result = await extract_module.regenerate_identity("memory1\nmemory2", "key")
        assert result == "I am Claude, working with Alice on project X."
        mock_call.assert_called_once_with(
            extract_module.IDENTITY_PROMPT,
            "Memories:\nmemory1\nmemory2",
            "key",
            max_tokens=512,
        )
