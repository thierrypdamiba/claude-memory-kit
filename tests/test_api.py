"""Tests for the FastAPI app at /api endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from claude_memory_kit.api.app import app, _auth, _get_store
from claude_memory_kit.auth import LOCAL_USER
from claude_memory_kit.types import (
    Memory, Gate, DecayClass, IdentityCard,
)
import claude_memory_kit.api.app as app_module

# Override auth dependency to skip real auth
app.dependency_overrides[_auth] = lambda: LOCAL_USER


@pytest.fixture
def client():
    return TestClient(app)


def _make_memory(
    id="mem_test_001",
    gate=Gate.epistemic,
    content="test memory content",
    person=None,
    project=None,
):
    now = datetime.now(timezone.utc)
    return Memory(
        id=id,
        created=now,
        gate=gate,
        person=person,
        project=project,
        confidence=0.9,
        last_accessed=now,
        access_count=1,
        decay_class=DecayClass.from_gate(gate),
        content=content,
    )


@pytest.fixture(autouse=True)
def setup_store(db, monkeypatch):
    store = MagicMock()
    store.db = db
    store.vectors = MagicMock()
    store.vectors.search.return_value = []
    store.vectors.upsert.return_value = None
    store.vectors.delete.return_value = None
    store.count_user_data.return_value = {"total": 0, "memories": 0}
    store.migrate_user_data.return_value = {"memories": 0}
    monkeypatch.setattr(app_module, "_store", store)
    monkeypatch.setattr(app_module, "_get_store", lambda: store)
    return store


# ---- Health ----

def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---- Auth ----

def test_auth_me(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["id"] == "local"


# ---- API Keys ----

def test_create_key(client, setup_store):
    resp = client.post("/api/keys", json={"name": "test-key"})
    assert resp.status_code == 200
    key_data = resp.json()["key"]
    assert "id" in key_data
    assert key_data["key"].startswith("cmk-sk-")


def test_list_keys(client, setup_store):
    # Create a key first
    client.post("/api/keys", json={"name": "k1"})
    resp = client.get("/api/keys")
    assert resp.status_code == 200
    assert "keys" in resp.json()


def test_delete_key(client, setup_store):
    # Create then delete
    create_resp = client.post("/api/keys", json={"name": "to-delete"})
    key_id = create_resp.json()["key"]["id"]
    resp = client.delete(f"/api/keys/{key_id}")
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True


def test_delete_key_not_found(client, setup_store):
    resp = client.delete("/api/keys/nonexistent-key-id")
    assert resp.status_code == 404


# ---- Memories ----

def test_list_memories_empty(client):
    resp = client.get("/api/memories")
    assert resp.status_code == 200
    assert resp.json()["memories"] == []


def test_create_memory(client, setup_store):
    with patch("claude_memory_kit.api.app.do_remember", new_callable=AsyncMock) as mock_rem:
        mock_rem.return_value = "remembered"
        resp = client.post("/api/memories", json={
            "content": "I like coffee",
            "gate": "behavioral",
        })
        assert resp.status_code == 200
        assert resp.json()["result"] == "remembered"
        mock_rem.assert_called_once()


def test_create_memory_bad_gate(client):
    resp = client.post("/api/memories", json={
        "content": "test",
        "gate": "invalid_gate",
    })
    assert resp.status_code == 422


def test_create_memory_missing_content(client):
    resp = client.post("/api/memories", json={
        "gate": "behavioral",
    })
    assert resp.status_code == 422


def test_get_memory(client, db):
    mem = _make_memory(id="mem_get_001")
    db.insert_memory(mem)
    resp = client.get("/api/memories/mem_get_001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "mem_get_001"


def test_get_memory_not_found(client):
    resp = client.get("/api/memories/nonexistent")
    assert resp.status_code == 404


def test_update_memory(client, db, setup_store):
    mem = _make_memory(id="mem_upd_001")
    db.insert_memory(mem)
    resp = client.patch("/api/memories/mem_upd_001", json={
        "content": "updated content",
    })
    assert resp.status_code == 200
    assert resp.json()["result"] == "updated"


def test_update_memory_no_changes(client, db):
    mem = _make_memory(id="mem_upd_002")
    db.insert_memory(mem)
    resp = client.patch("/api/memories/mem_upd_002", json={})
    assert resp.status_code == 200
    assert resp.json()["result"] == "no changes"


def test_update_memory_not_found(client):
    resp = client.patch("/api/memories/nonexistent", json={
        "content": "nope",
    })
    assert resp.status_code == 404


def test_delete_memory(client, db, setup_store):
    mem = _make_memory(id="mem_del_001")
    db.insert_memory(mem)
    with patch("claude_memory_kit.api.app.do_forget", new_callable=AsyncMock) as mock_forget:
        mock_forget.return_value = "forgotten"
        resp = client.delete("/api/memories/mem_del_001")
        assert resp.status_code == 200
        assert resp.json()["result"] == "forgotten"


def test_list_memories_with_filters(client, db):
    db.insert_memory(_make_memory(id="m1", gate=Gate.behavioral, person="Alice"))
    db.insert_memory(_make_memory(id="m2", gate=Gate.epistemic, person="Bob"))
    resp = client.get("/api/memories?gate=behavioral")
    assert resp.status_code == 200
    mems = resp.json()["memories"]
    assert all(m["gate"] == "behavioral" for m in mems)


# ---- Pin ----

def test_pin_memory(client, db):
    mem = _make_memory(id="mem_pin_001")
    db.insert_memory(mem)
    resp = client.post("/api/memories/mem_pin_001/pin")
    assert resp.status_code == 200
    assert resp.json()["result"] == "pinned"


def test_unpin_memory(client, db):
    mem = _make_memory(id="mem_unpin_001")
    db.insert_memory(mem)
    db.set_pinned("mem_unpin_001", True)
    resp = client.delete("/api/memories/mem_unpin_001/pin")
    assert resp.status_code == 200
    assert resp.json()["result"] == "unpinned"


def test_pin_memory_not_found(client):
    resp = client.post("/api/memories/nonexistent/pin")
    assert resp.status_code == 404


def test_unpin_memory_not_found(client):
    resp = client.delete("/api/memories/nonexistent/pin")
    assert resp.status_code == 404


# ---- Search ----

def test_search(client, setup_store):
    with patch("claude_memory_kit.api.app.do_recall", new_callable=AsyncMock) as mock_recall:
        mock_recall.return_value = "found 0 results"
        resp = client.post("/api/search", json={"query": "coffee"})
        assert resp.status_code == 200
        assert "result" in resp.json()


def test_search_empty_query(client):
    resp = client.post("/api/search", json={"query": ""})
    assert resp.status_code == 422


# ---- Identity ----

def test_get_identity(client, setup_store):
    with patch("claude_memory_kit.api.app.do_identity", new_callable=AsyncMock) as mock_id:
        mock_id.return_value = "identity card content"
        resp = client.get("/api/identity")
        assert resp.status_code == 200
        assert resp.json()["identity"] == "identity card content"


def test_put_identity(client, db):
    resp = client.put("/api/identity", json={"content": "I am a developer"})
    assert resp.status_code == 200
    assert resp.json()["result"] == "updated"
    # Verify the identity was saved
    card = db.get_identity(user_id="local")
    assert card is not None
    assert card.content == "I am a developer"


# ---- Graph ----

def test_get_graph(client, db):
    resp = client.get("/api/graph/some-id")
    assert resp.status_code == 200
    assert "related" in resp.json()


# ---- Reflect ----

def test_trigger_reflect(client, setup_store):
    with patch("claude_memory_kit.api.app.do_reflect", new_callable=AsyncMock) as mock_ref:
        mock_ref.return_value = "reflection complete"
        resp = client.post("/api/reflect")
        assert resp.status_code == 200
        assert resp.json()["result"] == "reflection complete"


# ---- Scan ----

def test_scan_memories(client, setup_store):
    with patch("claude_memory_kit.api.app.do_scan", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = "Scanned 0 memories. No sensitive data patterns found."
        resp = client.get("/api/scan")
        assert resp.status_code == 200
        assert "result" in resp.json()


# ---- Privacy / Sensitivity ----

def test_list_private(client, db):
    resp = client.get("/api/private")
    assert resp.status_code == 200
    assert "memories" in resp.json()


def test_list_private_with_level(client, db):
    mem = _make_memory(id="priv_001", content="salary info")
    db.insert_memory(mem)
    db.update_sensitivity("priv_001", "sensitive", "salary info")
    resp = client.get("/api/private?level=sensitive")
    assert resp.status_code == 200


def test_privacy_stats(client, db):
    resp = client.get("/api/privacy-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "safe" in data
    assert "sensitive" in data
    assert "critical" in data
    assert "unclassified" in data


def test_trigger_classify(client, setup_store):
    with patch("claude_memory_kit.api.app.classify_memories", new_callable=AsyncMock) as mock_cls:
        mock_cls.return_value = "Classified 0 memories"
        resp = client.post("/api/classify")
        assert resp.status_code == 200
        assert "result" in resp.json()


def test_update_sensitivity(client, db, setup_store):
    mem = _make_memory(id="sens_001")
    db.insert_memory(mem)
    with patch("claude_memory_kit.api.app.reclassify_memory", new_callable=AsyncMock) as mock_rcl:
        mock_rcl.return_value = "Reclassified sens_001 as critical."
        resp = client.patch("/api/memories/sens_001/sensitivity", json={
            "level": "critical",
        })
        assert resp.status_code == 200


def test_update_sensitivity_bad_level(client):
    resp = client.patch("/api/memories/some-id/sensitivity", json={
        "level": "bogus",
    })
    assert resp.status_code == 422


def test_bulk_private_delete(client, db, setup_store):
    mem = _make_memory(id="bulk_001")
    db.insert_memory(mem)
    with patch("claude_memory_kit.api.app.do_forget", new_callable=AsyncMock) as mock_forget:
        mock_forget.return_value = "forgotten"
        resp = client.post("/api/private/bulk", json={
            "ids": ["bulk_001"],
            "action": "delete",
        })
        assert resp.status_code == 200
        assert "1/1" in resp.json()["result"]


def test_bulk_private_redact(client, db, setup_store):
    mem = _make_memory(id="bulk_002")
    db.insert_memory(mem)
    resp = client.post("/api/private/bulk", json={
        "ids": ["bulk_002"],
        "action": "redact",
    })
    assert resp.status_code == 200
    assert "1/1" in resp.json()["result"]


def test_bulk_private_reclassify(client, db, setup_store):
    mem = _make_memory(id="bulk_003")
    db.insert_memory(mem)
    resp = client.post("/api/private/bulk", json={
        "ids": ["bulk_003"],
        "action": "reclassify",
        "level": "safe",
    })
    assert resp.status_code == 200
    assert "1/1" in resp.json()["result"]


def test_bulk_private_invalid_action(client):
    resp = client.post("/api/private/bulk", json={
        "ids": ["x"],
        "action": "nuke",
    })
    assert resp.status_code == 422


def test_bulk_private_nonexistent_ids(client, db):
    resp = client.post("/api/private/bulk", json={
        "ids": ["ghost_001"],
        "action": "delete",
    })
    assert resp.status_code == 200
    assert "0/1" in resp.json()["result"]


# ---- Stats ----

def test_get_stats(client, db):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_gate" in data
    assert "has_identity" in data


def test_get_stats_with_data(client, db):
    db.insert_memory(_make_memory(id="stat_001", gate=Gate.behavioral))
    db.insert_memory(_make_memory(id="stat_002", gate=Gate.epistemic))
    resp = client.get("/api/stats")
    data = resp.json()
    assert data["total"] == 2
    assert "behavioral" in data["by_gate"]


# ---- Rules ----

def test_list_rules_empty(client, db):
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    assert resp.json()["rules"] == []


def test_create_rule(client, db):
    resp = client.post("/api/rules", json={
        "condition": "always greet the user",
        "enforcement": "suggest",
    })
    assert resp.status_code == 200
    assert resp.json()["rule"] is not None


def test_create_rule_bad_enforcement(client):
    resp = client.post("/api/rules", json={
        "condition": "test",
        "enforcement": "obliterate",
    })
    assert resp.status_code == 422


def test_update_rule(client, db):
    # Create first
    create_resp = client.post("/api/rules", json={
        "condition": "original condition",
        "enforcement": "suggest",
    })
    rule = create_resp.json()["rule"]
    rule_id = rule["id"]

    resp = client.put(f"/api/rules/{rule_id}", json={
        "condition": "updated condition",
    })
    assert resp.status_code == 200
    assert resp.json()["result"] == "updated"


def test_update_rule_no_changes(client, db):
    create_resp = client.post("/api/rules", json={
        "condition": "test condition",
    })
    rule_id = create_resp.json()["rule"]["id"]
    resp = client.put(f"/api/rules/{rule_id}", json={})
    assert resp.status_code == 200
    assert resp.json()["result"] == "no changes"


def test_update_rule_not_found(client):
    resp = client.put("/api/rules/nonexistent", json={
        "condition": "nope",
    })
    assert resp.status_code == 404


def test_delete_rule(client, db):
    create_resp = client.post("/api/rules", json={
        "condition": "to be deleted",
    })
    rule_id = create_resp.json()["rule"]["id"]
    resp = client.delete(f"/api/rules/{rule_id}")
    assert resp.status_code == 200
    assert resp.json()["result"] == "deleted"


def test_delete_rule_not_found(client):
    resp = client.delete("/api/rules/nonexistent")
    assert resp.status_code == 404


# ---- Mode ----

def test_get_mode(client, monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "")
    resp = client.get("/api/mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "local"
    assert data["vector_store"] == "local"


# ---- Setup ----

def test_setup_init_key_local_user(client):
    """Local user should get 400 from init-key."""
    resp = client.post("/api/setup/init-key")
    assert resp.status_code == 400
    assert "authenticated" in resp.json()["detail"].lower()


def test_setup_init_key_authenticated_user(client, setup_store):
    """Authenticated (non-local) user should get a key."""
    app.dependency_overrides[_auth] = lambda: {
        "id": "user_abc123", "email": "test@example.com",
        "name": "Test", "plan": "free",
    }
    try:
        resp = client.post("/api/setup/init-key")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"].startswith("cmk-sk-")
        assert data["user_id"] == "user_abc123"
        assert "cmk init" in data["command"]
    finally:
        app.dependency_overrides[_auth] = lambda: LOCAL_USER


# ---- Data Migration ----

def test_local_data_check(client, setup_store):
    resp = client.get("/api/local-data-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "has_local_data" in data
    assert "counts" in data


def test_claim_local_as_local_user(client, setup_store):
    """Local user cannot claim data."""
    resp = client.post("/api/claim-local")
    assert resp.status_code == 400


def test_claim_local_as_authenticated_user(client, setup_store):
    """Authenticated user can claim local data."""
    app.dependency_overrides[_auth] = lambda: {
        "id": "user_claim_001", "email": "claimer@example.com",
        "name": "Claimer", "plan": "free",
    }
    setup_store.count_user_data.return_value = {"total": 0}
    try:
        resp = client.post("/api/claim-local")
        assert resp.status_code == 200
        assert "no local data" in resp.json()["message"]
    finally:
        app.dependency_overrides[_auth] = lambda: LOCAL_USER


def test_claim_local_with_data(client, setup_store):
    """Authenticated user claims existing local data."""
    app.dependency_overrides[_auth] = lambda: {
        "id": "user_claim_002", "email": "c2@example.com",
        "name": "C2", "plan": "free",
    }
    setup_store.count_user_data.return_value = {"total": 5, "memories": 5}
    setup_store.migrate_user_data.return_value = {"memories": 5}
    try:
        resp = client.post("/api/claim-local")
        assert resp.status_code == 200
        assert "claimed" in resp.json()["message"]
        assert resp.json()["migrated"]["memories"] == 5
    finally:
        app.dependency_overrides[_auth] = lambda: LOCAL_USER


# ---- Security Headers ----

def test_security_headers(client):
    resp = client.get("/healthz")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


# ---- Lifespan ----

def test_lifespan_runs(monkeypatch):
    """Lifespan context manager runs without error."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "")
    from claude_memory_kit.api.app import lifespan
    import asyncio

    async def _run():
        async with lifespan(app):
            pass  # just verify it enters and exits

    asyncio.run(_run())


def test_lifespan_auth_warning(monkeypatch):
    """Lifespan warns when CLERK_SECRET_KEY is set but no frontend."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_real_key")
    monkeypatch.setenv("CLERK_FRONTEND_API", "")
    monkeypatch.setenv("CLERK_INSTANCE_ID", "")
    from claude_memory_kit.api.app import lifespan
    import asyncio

    async def _run():
        async with lifespan(app):
            pass

    asyncio.run(_run())


def test_lifespan_auth_enabled(monkeypatch):
    """Lifespan logs auth enabled when both keys are set."""
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_real_key")
    monkeypatch.setenv("CLERK_FRONTEND_API", "https://clerk.example.com")
    from claude_memory_kit.api.app import lifespan
    import asyncio

    async def _run():
        async with lifespan(app):
            pass

    asyncio.run(_run())


# ---- _get_store lazy init ----

def test_get_store_lazy_init(monkeypatch):
    """_get_store creates store on first call."""
    monkeypatch.setattr(app_module, "_store", None)
    mock_store = MagicMock()
    with patch("claude_memory_kit.api.app.Store", return_value=mock_store), \
         patch("claude_memory_kit.api.app.get_store_path", return_value="/tmp/test"):
        result = _get_store()
    assert result is mock_store
    mock_store.db.migrate.assert_called_once()
    mock_store.vectors.ensure_collection.assert_called_once()


# ---- _auth dependency ----

@pytest.mark.asyncio
async def test_auth_dependency_calls_get_current_user(monkeypatch, db):
    """_auth resolves user via get_current_user."""
    mock_store = MagicMock()
    mock_store.db = db
    monkeypatch.setattr(app_module, "_store", mock_store)
    monkeypatch.setattr(app_module, "_get_store", lambda: mock_store)

    from claude_memory_kit.api.app import _auth as real_auth
    mock_request = MagicMock()
    with patch("claude_memory_kit.api.app.get_current_user", new_callable=AsyncMock, return_value=LOCAL_USER):
        result = await real_auth(mock_request)
    assert result == LOCAL_USER


# ---- Redact vector failure ----

def test_bulk_private_redact_vector_failure(client, db, setup_store):
    """Redact continues even if vector upsert fails."""
    mem = _make_memory(id="bulk_redact_fail")
    db.insert_memory(mem)
    setup_store.vectors.upsert.side_effect = RuntimeError("vector service down")
    resp = client.post("/api/private/bulk", json={
        "ids": ["bulk_redact_fail"],
        "action": "redact",
    })
    assert resp.status_code == 200
    assert "1/1" in resp.json()["result"]
    # Memory content should still be redacted in SQLite
    updated = db.get_memory("bulk_redact_fail")
    assert updated.content == "[REDACTED]"
