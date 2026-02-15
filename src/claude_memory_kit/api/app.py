"""FastAPI server for the dashboard."""

import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..auth import get_current_user, is_auth_enabled, LOCAL_USER
from ..auth_keys import create_api_key, list_keys, revoke_key
from ..config import get_store_path, is_cloud_mode
from ..store import Store
from ..types import IdentityCard
from ..tools import (
    do_remember, do_recall, do_reflect,
    do_identity, do_forget, do_prime,
)

app = FastAPI(title="claude-memory-kit")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5555,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_store: Store | None = None


def _get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(get_store_path())
        _store.db.migrate()
        _store.vectors.ensure_collection()
    return _store


async def _auth(request: Request) -> dict:
    """Resolve current user. Local mode returns local user."""
    store = _get_store()
    return await get_current_user(request, db=store.db)


class CreateMemoryRequest(BaseModel):
    content: str = Field(..., max_length=100_000)
    gate: str = Field(..., max_length=50)
    person: str | None = Field(None, max_length=500)
    project: str | None = Field(None, max_length=500)


class UpdateMemoryRequest(BaseModel):
    content: str | None = Field(None, max_length=100_000)
    gate: str | None = Field(None, max_length=50)
    person: str | None = Field(None, max_length=500)
    project: str | None = Field(None, max_length=500)


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=10_000)


class CreateKeyRequest(BaseModel):
    name: str = ""


class UpdateIdentityRequest(BaseModel):
    content: str


class CreateRuleRequest(BaseModel):
    scope: str = Field("global", max_length=100)
    condition: str = Field(..., max_length=10_000)
    enforcement: str = Field("suggest", max_length=50)


class UpdateRuleRequest(BaseModel):
    scope: str | None = None
    condition: str | None = None
    enforcement: str | None = None


# ---- Public ----

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ---- Auth ----

@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(_auth)):
    return {"user": user}


@app.post("/api/keys")
async def create_key(
    req: CreateKeyRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    result = create_api_key(store.db, user["id"], req.name)
    return {"key": result}


@app.get("/api/keys")
async def get_keys(user: dict = Depends(_auth)):
    store = _get_store()
    keys = list_keys(store.db, user["id"])
    return {"keys": keys}


@app.delete("/api/keys/{key_id}")
async def delete_key(key_id: str, user: dict = Depends(_auth)):
    store = _get_store()
    ok = revoke_key(store.db, key_id, user["id"])
    if not ok:
        raise HTTPException(404, "key not found")
    return {"revoked": True}


# ---- Memories ----

@app.get("/api/memories")
async def list_memories(
    limit: int = 50, offset: int = 0,
    gate: str | None = None,
    person: str | None = None,
    project: str | None = None,
    user: dict = Depends(_auth),
):
    store = _get_store()
    memories = store.db.list_memories(
        limit, offset, user_id=user["id"],
        gate=gate, person=person, project=project,
    )
    return {"memories": [m.model_dump() for m in memories]}


@app.post("/api/memories")
async def create_memory(
    req: CreateMemoryRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    result = await do_remember(
        store, req.content, req.gate, req.person, req.project,
        user_id=user["id"],
    )
    return {"result": result}


@app.get("/api/memories/{id}")
async def get_memory(id: str, user: dict = Depends(_auth)):
    store = _get_store()
    mem = store.db.get_memory(id, user_id=user["id"])
    if not mem:
        raise HTTPException(404, "memory not found")
    return mem.model_dump()


@app.patch("/api/memories/{id}")
async def update_memory(
    id: str, req: UpdateMemoryRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    mem = store.db.get_memory(id, user_id=user["id"])
    if not mem:
        raise HTTPException(404, "memory not found")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return {"result": "no changes"}

    store.db.update_memory(id, user_id=user["id"], **updates)

    # Re-embed if content changed
    if "content" in updates:
        updated_mem = store.db.get_memory(id, user_id=user["id"])
        if updated_mem:
            store.vectors.upsert(
                updated_mem.id, updated_mem.content,
                updated_mem.person, updated_mem.project,
                user_id=user["id"],
            )

    return {"result": "updated"}


@app.delete("/api/memories/{id}")
async def delete_memory(
    id: str, reason: str = "", user: dict = Depends(_auth)
):
    store = _get_store()
    result = await do_forget(
        store, id, reason or "deleted via API", user_id=user["id"]
    )
    return {"result": result}


# ---- Pin ----

@app.post("/api/memories/{id}/pin")
async def pin_memory(id: str, user: dict = Depends(_auth)):
    store = _get_store()
    mem = store.db.get_memory(id, user_id=user["id"])
    if not mem:
        raise HTTPException(404, "memory not found")
    store.db.set_pinned(id, True, user_id=user["id"])
    return {"result": "pinned"}


@app.delete("/api/memories/{id}/pin")
async def unpin_memory(id: str, user: dict = Depends(_auth)):
    store = _get_store()
    mem = store.db.get_memory(id, user_id=user["id"])
    if not mem:
        raise HTTPException(404, "memory not found")
    store.db.set_pinned(id, False, user_id=user["id"])
    return {"result": "unpinned"}


# ---- Search ----

@app.post("/api/search")
async def search(
    req: SearchRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    result = await do_recall(store, req.query, user_id=user["id"])
    return {"result": result}


# ---- Identity ----

@app.get("/api/identity")
async def get_identity(user: dict = Depends(_auth)):
    store = _get_store()
    result = await do_identity(store, user_id=user["id"])
    return {"identity": result}


@app.put("/api/identity")
async def update_identity(
    req: UpdateIdentityRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    card = IdentityCard(
        person=None,
        project=None,
        content=req.content,
        last_updated=datetime.now(timezone.utc),
    )
    store.db.set_identity(card, user_id=user["id"])
    return {"result": "updated"}


@app.get("/api/graph/{id}")
async def get_graph(id: str, user: dict = Depends(_auth)):
    store = _get_store()
    related = store.db.find_related(
        id, depth=2, user_id=user["id"]
    )
    return {"related": related}


@app.post("/api/reflect")
async def trigger_reflect(user: dict = Depends(_auth)):
    store = _get_store()
    result = await do_reflect(store, user_id=user["id"])
    return {"result": result}


@app.get("/api/stats")
async def get_stats(user: dict = Depends(_auth)):
    store = _get_store()
    uid = user["id"]
    return {
        "total": store.db.count_memories(user_id=uid),
        "by_gate": store.db.count_by_gate(user_id=uid),
        "has_identity": store.db.get_identity(user_id=uid) is not None,
    }


# ---- Rules ----

@app.get("/api/rules")
async def list_rules(user: dict = Depends(_auth)):
    store = _get_store()
    rules = store.db.list_rules(user_id=user["id"])
    return {"rules": rules}


@app.post("/api/rules")
async def create_rule(
    req: CreateRuleRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    rule_id = str(uuid.uuid4())[:12]
    store.db.insert_rule(
        rule_id, user["id"], req.scope,
        req.condition, req.enforcement,
    )
    rule = store.db.get_rule(rule_id, user_id=user["id"])
    return {"rule": rule}


@app.put("/api/rules/{rule_id}")
async def update_rule(
    rule_id: str, req: UpdateRuleRequest, user: dict = Depends(_auth)
):
    store = _get_store()
    existing = store.db.get_rule(rule_id, user_id=user["id"])
    if not existing:
        raise HTTPException(404, "rule not found")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        return {"result": "no changes"}

    store.db.update_rule(rule_id, user_id=user["id"], **updates)
    return {"result": "updated"}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: str, user: dict = Depends(_auth)):
    store = _get_store()
    ok = store.db.delete_rule(rule_id, user_id=user["id"])
    if not ok:
        raise HTTPException(404, "rule not found")
    return {"result": "deleted"}


# ---- Mode ----

@app.get("/api/mode")
async def get_mode():
    cloud = is_cloud_mode()
    return {
        "mode": "cloud" if cloud else "local",
        "vector_store": "qdrant" if cloud else "local",
    }


# ---- Setup ----

@app.post("/api/setup/init-key")
async def setup_init_key(user: dict = Depends(_auth)):
    """Generate an API key and return the cmk init command."""
    store = _get_store()
    uid = user["id"]

    if uid == "local":
        raise HTTPException(400, "must be authenticated")

    result = create_api_key(store.db, uid, "cmk-init")
    raw_key = result["key"]
    return {
        "key": raw_key,
        "user_id": uid,
        "command": f"cmk init {raw_key}",
        "mcp_config": {
            "memory": {
                "command": "cmk",
                "env": {"CMK_USER_ID": uid},
            },
        },
    }


# ---- Data Migration ----

@app.get("/api/local-data-check")
async def local_data_check(user: dict = Depends(_auth)):
    """Check if unclaimed local data exists."""
    store = _get_store()
    counts = store.count_user_data("local")
    total = counts.get("total", 0)
    return {
        "has_local_data": total > 0,
        "counts": counts,
    }


@app.post("/api/claim-local")
async def claim_local(user: dict = Depends(_auth)):
    """Claim local data for the authenticated user."""
    store = _get_store()
    uid = user["id"]

    if uid == "local":
        raise HTTPException(400, "cannot claim data as local user")

    counts = store.count_user_data("local")
    if counts.get("total", 0) == 0:
        return {"migrated": {}, "message": "no local data to claim"}

    result = store.migrate_user_data("local", uid)
    return {"migrated": result, "message": "local data claimed"}
