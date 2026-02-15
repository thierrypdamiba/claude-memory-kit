"""Shared fixtures for CMK test suite."""

import os
import tempfile

import pytest

# Force local mode, no real API keys
os.environ["QDRANT_URL"] = ""
os.environ["QDRANT_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["CLERK_SECRET_KEY"] = ""
os.environ["CLERK_PUBLISHABLE_KEY"] = ""
os.environ["CLERK_FRONTEND_API"] = ""
os.environ["CLERK_INSTANCE_ID"] = ""


@pytest.fixture
def tmp_store_path(tmp_path):
    """Return a fresh temp directory for store data."""
    return str(tmp_path / "cmk-test-store")


@pytest.fixture
def db(tmp_store_path):
    """Return a fresh migrated SqliteStore."""
    from claude_memory_kit.store.sqlite import SqliteStore
    store = SqliteStore(tmp_store_path)
    store.migrate()
    return store


@pytest.fixture
def make_memory():
    """Factory for creating Memory objects."""
    from datetime import datetime, timezone
    from claude_memory_kit.types import Memory, Gate, DecayClass

    def _make(
        id="mem_test_001",
        gate=Gate.epistemic,
        content="test memory content",
        person=None,
        project=None,
        confidence=0.9,
        access_count=1,
        sensitivity=None,
        sensitivity_reason=None,
    ):
        now = datetime.now(timezone.utc)
        return Memory(
            id=id,
            created=now,
            gate=gate,
            person=person,
            project=project,
            confidence=confidence,
            last_accessed=now,
            access_count=access_count,
            decay_class=DecayClass.from_gate(gate),
            content=content,
            sensitivity=sensitivity,
            sensitivity_reason=sensitivity_reason,
        )
    return _make
