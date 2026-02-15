"""Tests for VectorStore and helper functions."""

import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from claude_memory_kit.store.vectors import _stable_id, VectorStore, COLLECTION


# ---------------------------------------------------------------------------
# _stable_id pure-function tests
# ---------------------------------------------------------------------------


class TestStableId:
    """Tests for the _stable_id deterministic hash function."""

    def test_deterministic_same_input(self):
        assert _stable_id("mem_001") == _stable_id("mem_001")

    def test_different_inputs_different_outputs(self):
        assert _stable_id("mem_001") != _stable_id("mem_002")

    def test_returns_positive_integer(self):
        result = _stable_id("anything")
        assert isinstance(result, int)
        assert result >= 0

    def test_fits_in_unsigned_63_bits(self):
        """The >> 1 ensures the top bit is 0, so value fits in 63 bits."""
        result = _stable_id("some_memory_id")
        assert result < (1 << 63)

    def test_empty_string_works(self):
        result = _stable_id("")
        assert isinstance(result, int)
        assert result >= 0

    def test_unicode_input(self):
        result = _stable_id("memory_with_unicode_\u00e9\u00e0\u00fc")
        assert isinstance(result, int)
        assert result == _stable_id("memory_with_unicode_\u00e9\u00e0\u00fc")

    def test_long_input(self):
        long_id = "x" * 10000
        result = _stable_id(long_id)
        assert isinstance(result, int)
        assert result >= 0


# ---------------------------------------------------------------------------
# VectorStore disabled-mode tests
# ---------------------------------------------------------------------------


class TestVectorStoreDisabled:
    """Test VectorStore behavior when disabled (no real Qdrant needed)."""

    def _make_disabled_store(self):
        """Create a VectorStore instance with _disabled=True, bypassing __init__."""
        store = object.__new__(VectorStore)
        store._disabled = True
        store._cloud = False
        store._jina_key = ""
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = None
        return store

    def test_upsert_returns_none_when_disabled(self):
        store = self._make_disabled_store()
        result = store.upsert("mem_1", "content", "alice", "proj", "user_1")
        assert result is None

    def test_search_returns_empty_when_disabled(self):
        store = self._make_disabled_store()
        result = store.search("query text", limit=5, user_id="user_1")
        assert result == []

    def test_delete_returns_none_when_disabled(self):
        store = self._make_disabled_store()
        result = store.delete("mem_1", user_id="user_1")
        assert result is None

    def test_ensure_collection_noop_when_disabled(self):
        store = self._make_disabled_store()
        # Should not raise
        store.ensure_collection()

    def test_migrate_user_id_returns_zero_when_disabled(self):
        store = self._make_disabled_store()
        result = store.migrate_user_id("old_user", "new_user")
        assert result == 0


# ---------------------------------------------------------------------------
# VectorStore local-mode init test
# ---------------------------------------------------------------------------


class TestVectorStoreLocalInit:
    """Test VectorStore creation in local mode."""

    def test_creates_qdrant_directory(self, tmp_store_path):
        """In local mode, __init__ creates the qdrant subdirectory."""
        qdrant_dir = os.path.join(tmp_store_path, "qdrant")
        assert not os.path.exists(qdrant_dir)

        store = VectorStore(tmp_store_path)
        assert os.path.isdir(qdrant_dir)
        assert store._disabled is False
        assert store._cloud is False
        # Close the client to release the lock
        if store.client:
            store.client.close()

    def test_locked_qdrant_disables_store(self, tmp_store_path):
        """If Qdrant is already locked, store should disable gracefully."""
        # Open a first client to hold the lock
        first = VectorStore(tmp_store_path)
        assert first._disabled is False

        # Second client on the same path should get locked out
        second = VectorStore(tmp_store_path)
        assert second._disabled is True

        if first.client:
            first.client.close()


# ---------------------------------------------------------------------------
# VectorStore integration tests (local embedded Qdrant)
# ---------------------------------------------------------------------------


class TestVectorStoreIntegration:
    """Full pipeline test with a real embedded Qdrant client.

    These tests use fastembed for local embeddings. If fastembed is not
    installed or too slow, they will be skipped.
    """

    @pytest.fixture
    def vs(self, tmp_path):
        """Create a VectorStore with a fresh temp directory."""
        store_path = str(tmp_path / "vs-integration")
        store = VectorStore(store_path)
        if store._disabled:
            pytest.skip("Qdrant client could not be initialized")
        store.ensure_collection()
        yield store
        if store.client:
            store.client.close()

    def test_ensure_collection_creates_collection(self, vs):
        names = [c.name for c in vs.client.get_collections().collections]
        assert COLLECTION in names

    def test_upsert_and_search(self, vs):
        vs.upsert("mem_alpha", "Python is great for data science", None, None, "u1")
        vs.upsert("mem_beta", "Rust is great for systems programming", None, None, "u1")

        results = vs.search("programming languages", limit=5, user_id="u1")
        assert len(results) >= 1
        memory_ids = [r[0] for r in results]
        # At least one of our memories should come back
        assert "mem_alpha" in memory_ids or "mem_beta" in memory_ids

    def test_search_returns_tuples(self, vs):
        vs.upsert("mem_tuple", "tuple test content", None, None, "u1")
        results = vs.search("tuple test", limit=3, user_id="u1")
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)  # memory_id
            assert isinstance(item[1], (int, float))  # score

    def test_delete_removes_point(self, vs):
        vs.upsert("mem_del", "delete me please", None, None, "u1")
        # Verify it's searchable
        results_before = vs.search("delete me", limit=5, user_id="u1")
        found_before = any(r[0] == "mem_del" for r in results_before)
        assert found_before

        vs.delete("mem_del", user_id="u1")
        results_after = vs.search("delete me", limit=5, user_id="u1")
        found_after = any(r[0] == "mem_del" for r in results_after)
        assert not found_after

    def test_upsert_with_metadata(self, vs):
        vs.upsert("mem_meta", "project related memory", "alice", "cmk", "u1")
        results = vs.search("project related", limit=5, user_id="u1")
        assert any(r[0] == "mem_meta" for r in results)

    def test_user_id_isolation(self, vs):
        vs.upsert("mem_u1", "user one data about cats", None, None, "user_one")
        vs.upsert("mem_u2", "user two data about dogs", None, None, "user_two")

        results_u1 = vs.search("cats", limit=5, user_id="user_one")
        results_u2 = vs.search("dogs", limit=5, user_id="user_two")

        u1_ids = [r[0] for r in results_u1]
        u2_ids = [r[0] for r in results_u2]

        # user_one should not see user_two's data and vice versa
        assert "mem_u2" not in u1_ids
        assert "mem_u1" not in u2_ids

    def test_search_empty_collection(self, vs):
        results = vs.search("nonexistent query", limit=5, user_id="ghost_user")
        assert results == []

    def test_upsert_overwrites_same_id(self, vs):
        vs.upsert("mem_overwrite", "original content", None, None, "u1")
        vs.upsert("mem_overwrite", "updated content about jazz", None, None, "u1")

        results = vs.search("jazz", limit=5, user_id="u1")
        found = any(r[0] == "mem_overwrite" for r in results)
        assert found


# ---------------------------------------------------------------------------
# Cloud-mode tests (mocked QdrantClient, no real cloud needed)
# ---------------------------------------------------------------------------


class TestVectorStoreCloudInit:
    """Test VectorStore creation in cloud mode."""

    def test_cloud_init_success(self):
        """Cloud mode sets _cloud=True and creates a QdrantClient."""
        cfg = {
            "mode": "cloud",
            "url": "https://my-cluster.qdrant.io",
            "api_key": "fake-api-key",
            "jina_api_key": "fake-jina-key",
        }
        with patch("claude_memory_kit.store.vectors.get_qdrant_config", return_value=cfg), \
             patch("claude_memory_kit.store.vectors.QdrantClient") as MockClient:
            MockClient.return_value = MagicMock()
            store = VectorStore("/tmp/unused")

        assert store._cloud is True
        assert store._disabled is False
        assert store._jina_key == "fake-jina-key"
        MockClient.assert_called_once_with(
            url="https://my-cluster.qdrant.io",
            api_key="fake-api-key",
            cloud_inference=True,
            timeout=30,
        )

    def test_cloud_init_connection_failure_disables(self):
        """If QdrantClient raises on cloud connect, store disables gracefully."""
        cfg = {
            "mode": "cloud",
            "url": "https://bad-cluster.qdrant.io",
            "api_key": "fake",
        }
        with patch("claude_memory_kit.store.vectors.get_qdrant_config", return_value=cfg), \
             patch("claude_memory_kit.store.vectors.QdrantClient", side_effect=ConnectionError("timeout")):
            store = VectorStore("/tmp/unused")

        assert store._disabled is True
        assert store.client is None

    def test_local_init_non_lock_runtime_error_raises(self):
        """A RuntimeError that isn't about locking should propagate."""
        cfg = {"mode": "local"}
        with patch("claude_memory_kit.store.vectors.get_qdrant_config", return_value=cfg), \
             patch("claude_memory_kit.store.vectors.QdrantClient", side_effect=RuntimeError("something else")):
            with pytest.raises(RuntimeError, match="something else"):
                VectorStore("/tmp/unused")


class TestCloudEmbeddingHelpers:
    """Test _jina_doc and _sparse_doc helper methods."""

    def _make_cloud_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = True
        store._jina_key = "test-jina-key"
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_jina_doc_returns_document(self):
        store = self._make_cloud_store()
        doc = store._jina_doc("hello world", task="retrieval.query")
        assert doc.text == "hello world"
        assert doc.model == "jinaai/jina-embeddings-v3"
        assert doc.options["jina-api-key"] == "test-jina-key"
        assert doc.options["dimensions"] == 1024
        assert doc.options["task"] == "retrieval.query"

    def test_jina_doc_default_task(self):
        store = self._make_cloud_store()
        doc = store._jina_doc("text")
        assert doc.options["task"] == "retrieval.passage"

    def test_sparse_doc_returns_document(self):
        store = self._make_cloud_store()
        doc = store._sparse_doc("search query")
        assert doc.text == "search query"
        assert doc.model == "Qdrant/bm25"


class TestCloudCollectionManagement:
    """Test collection management in cloud mode."""

    def _make_cloud_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = True
        store._jina_key = "jina-key"
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_is_legacy_collection_false_for_named_vectors(self):
        store = self._make_cloud_store()
        mock_info = MagicMock()
        mock_info.config.params.vectors = {"dense": MagicMock()}
        store.client.get_collection.return_value = mock_info
        assert store._is_legacy_collection() is False

    def test_is_legacy_collection_true_for_single_vector(self):
        store = self._make_cloud_store()
        mock_info = MagicMock()
        mock_info.config.params.vectors = MagicMock(spec=[])  # not a dict
        store.client.get_collection.return_value = mock_info
        assert store._is_legacy_collection() is True

    def test_is_legacy_collection_false_on_exception(self):
        store = self._make_cloud_store()
        store.client.get_collection.side_effect = Exception("not found")
        assert store._is_legacy_collection() is False

    def test_create_hybrid_collection_cloud_uses_jina_dim(self):
        store = self._make_cloud_store()
        store._create_hybrid_collection()

        call_kwargs = store.client.create_collection.call_args
        vectors_config = call_kwargs.kwargs["vectors_config"]
        assert vectors_config["dense"].size == 1024  # JINA_DIM
        # Cloud mode adds hnsw_config
        assert "hnsw_config" in call_kwargs.kwargs
        # Cloud mode creates content text index + user_id tenant index
        assert store.client.create_payload_index.call_count == 2

    def test_create_hybrid_collection_local_uses_local_dim(self):
        store = self._make_cloud_store()
        store._cloud = False
        store._create_hybrid_collection()

        call_kwargs = store.client.create_collection.call_args
        vectors_config = call_kwargs.kwargs["vectors_config"]
        assert vectors_config["dense"].size == 384  # LOCAL_DIM
        assert "hnsw_config" not in call_kwargs.kwargs
        # Local mode creates content text index only (no user_id tenant index)
        store.client.create_payload_index.assert_called_once()

    def test_ensure_collection_triggers_migration_for_legacy(self):
        store = self._make_cloud_store()
        mock_col = MagicMock()
        mock_col.name = COLLECTION
        store.client.get_collections.return_value.collections = [mock_col]

        # Legacy schema
        mock_info = MagicMock()
        mock_info.config.params.vectors = MagicMock(spec=[])  # not a dict
        store.client.get_collection.return_value = mock_info

        # scroll returns empty to end migration quickly
        store.client.scroll.return_value = ([], None)

        store.ensure_collection()

        # Should have called delete_collection + create_collection (migration)
        store.client.delete_collection.assert_called_once_with(COLLECTION)
        store.client.create_collection.assert_called_once()

    def test_ensure_collection_error_disables(self):
        store = self._make_cloud_store()
        store.client.get_collections.side_effect = Exception("network error")

        store.ensure_collection()

        assert store._disabled is True
        assert store.client is None


class TestCloudMigrateCollection:
    """Test _migrate_collection with mocked client."""

    def _make_cloud_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = True
        store._jina_key = "jina-key"
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_migrate_empty_collection(self):
        store = self._make_cloud_store()
        store.client.scroll.return_value = ([], None)

        store._migrate_collection()

        store.client.delete_collection.assert_called_once_with(COLLECTION)
        store.client.create_collection.assert_called_once()
        # No upserts since there were no points
        store.client.upsert.assert_not_called()

    def test_migrate_with_points_cloud_mode(self):
        store = self._make_cloud_store()

        # Simulate one batch of 2 points
        pt1 = MagicMock()
        pt1.id = 1
        pt1.payload = {"content": "hello world", "memory_id": "mem_1"}
        pt1.vector = [0.1] * 384

        pt2 = MagicMock()
        pt2.id = 2
        pt2.payload = {"content": "goodbye world", "memory_id": "mem_2"}
        pt2.vector = {"": [0.2] * 384}  # dict-style old vector

        store.client.scroll.return_value = ([pt1, pt2], None)

        store._migrate_collection()

        store.client.delete_collection.assert_called_once()
        store.client.create_collection.assert_called_once()
        store.client.upsert.assert_called_once()
        upsert_call = store.client.upsert.call_args
        points = upsert_call.kwargs["points"]
        assert len(points) == 2

    def test_migrate_with_points_local_mode(self):
        store = self._make_cloud_store()
        store._cloud = False

        pt = MagicMock()
        pt.id = 1
        pt.payload = {"content": "test", "memory_id": "mem_1"}
        pt.vector = [0.1] * 384  # list-style vector reused directly

        store.client.scroll.return_value = ([pt], None)

        # Mock local embedding
        mock_sparse = MagicMock()
        mock_sparse.indices.tolist.return_value = [0, 1]
        mock_sparse.values.tolist.return_value = [0.5, 0.3]
        with patch.object(type(store), '_local_sparse_model', new_callable=PropertyMock) as mock_prop:
            mock_model = MagicMock()
            mock_model.embed.return_value = iter([mock_sparse])
            mock_prop.return_value = mock_model

            store._migrate_collection()

        store.client.upsert.assert_called_once()
        points = store.client.upsert.call_args.kwargs["points"]
        assert len(points) == 1
        # Local mode: dense vector is reused from old point
        assert points[0].vector["dense"] == [0.1] * 384

    def test_migrate_multiple_scroll_batches(self):
        store = self._make_cloud_store()

        pt1 = MagicMock()
        pt1.id = 1
        pt1.payload = {"content": "batch1", "memory_id": "m1"}
        pt1.vector = [0.1]

        pt2 = MagicMock()
        pt2.id = 2
        pt2.payload = {"content": "batch2", "memory_id": "m2"}
        pt2.vector = [0.2]

        # First scroll returns pt1 with offset, second returns pt2 with no offset
        store.client.scroll.side_effect = [
            ([pt1], "next_page"),
            ([pt2], None),
        ]

        store._migrate_collection()

        # Scroll called twice (paginated)
        assert store.client.scroll.call_count == 2
        # Both points collected then upserted in one batch (< 50 points)
        store.client.upsert.assert_called_once()
        points = store.client.upsert.call_args.kwargs["points"]
        assert len(points) == 2

    def test_migrate_point_with_none_payload(self):
        store = self._make_cloud_store()

        pt = MagicMock()
        pt.id = 1
        pt.payload = None
        pt.vector = [0.1]

        store.client.scroll.return_value = ([pt], None)

        store._migrate_collection()

        points = store.client.upsert.call_args.kwargs["points"]
        assert len(points) == 1


class TestCloudUpsertAndSearch:
    """Test upsert and search in cloud mode."""

    def _make_cloud_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = True
        store._jina_key = "jina-key"
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_cloud_upsert_uses_jina_docs(self):
        store = self._make_cloud_store()

        store.upsert("mem_1", "test content", "alice", "proj", "user_1")

        store.client.upsert.assert_called_once()
        call_kwargs = store.client.upsert.call_args.kwargs
        points = call_kwargs["points"]
        assert len(points) == 1
        vec = points[0].vector
        # Cloud mode: vectors are Document objects, not lists
        assert vec["dense"].model == "jinaai/jina-embeddings-v3"
        assert vec["sparse"].model == "Qdrant/bm25"

    def test_cloud_search_uses_jina_query(self):
        store = self._make_cloud_store()

        mock_point = MagicMock()
        mock_point.payload = {"memory_id": "mem_1"}
        mock_point.score = 0.95
        store.client.query_points.return_value.points = [mock_point]

        results = store.search("test query", limit=5, user_id="user_1")

        assert results == [("mem_1", 0.95)]
        store.client.query_points.assert_called_once()
        call_kwargs = store.client.query_points.call_args.kwargs
        prefetch = call_kwargs["prefetch"]
        # Dense prefetch uses jina doc with query task
        assert prefetch[0].query.model == "jinaai/jina-embeddings-v3"
        assert prefetch[0].query.options["task"] == "retrieval.query"
        # Sparse prefetch uses BM25 doc
        assert prefetch[1].query.model == "Qdrant/bm25"

    def test_cloud_search_without_user_id(self):
        store = self._make_cloud_store()
        store.client.query_points.return_value.points = []

        results = store.search("query", limit=3)

        assert results == []
        call_kwargs = store.client.query_points.call_args.kwargs
        # No user_id filter
        assert call_kwargs["prefetch"][0].filter is None


class TestSearchText:
    """Test search_text (Qdrant text index full-text search)."""

    def _make_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = False
        store._jina_key = ""
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_returns_memory_ids(self):
        store = self._make_store()
        pt1 = MagicMock()
        pt1.payload = {"memory_id": "mem_1"}
        pt2 = MagicMock()
        pt2.payload = {"memory_id": "mem_2"}
        store.client.scroll.return_value = ([pt1, pt2], None)

        results = store.search_text("python async", limit=5, user_id="user_1")

        assert results == [("mem_1", 1.0), ("mem_2", 1.0)]
        call_kwargs = store.client.scroll.call_args.kwargs
        scroll_filter = call_kwargs["scroll_filter"]
        # Should have user_id + content MatchText conditions
        assert len(scroll_filter.must) == 2

    def test_without_user_id(self):
        store = self._make_store()
        store.client.scroll.return_value = ([], None)

        results = store.search_text("query", limit=3)

        assert results == []
        call_kwargs = store.client.scroll.call_args.kwargs
        scroll_filter = call_kwargs["scroll_filter"]
        # Only content MatchText condition, no user_id
        assert len(scroll_filter.must) == 1

    def test_disabled_returns_empty(self):
        store = self._make_store()
        store._disabled = True

        results = store.search_text("anything", limit=5)

        assert results == []
        store.client.scroll.assert_not_called()

    def test_text_index_created_in_collection(self):
        """Verify _create_hybrid_collection creates the content text index."""
        store = self._make_store()
        store._create_hybrid_collection()

        # Should have at least one create_payload_index call for 'content'
        content_index_calls = [
            c for c in store.client.create_payload_index.call_args_list
            if c.kwargs.get("field_name") == "content"
        ]
        assert len(content_index_calls) == 1
        schema = content_index_calls[0].kwargs["field_schema"]
        assert schema.type == "text"
        assert schema.lowercase is True


class TestMigrateUserId:
    """Test migrate_user_id with mocked client."""

    def _make_store(self):
        store = object.__new__(VectorStore)
        store._disabled = False
        store._cloud = False
        store._jina_key = ""
        store._fastembed_dense = None
        store._fastembed_sparse = None
        store.client = MagicMock()
        return store

    def test_migrates_single_batch(self):
        store = self._make_store()

        pt1 = MagicMock()
        pt1.id = 1
        pt2 = MagicMock()
        pt2.id = 2

        store.client.scroll.return_value = ([pt1, pt2], None)

        count = store.migrate_user_id("old_user", "new_user")

        assert count == 2
        store.client.set_payload.assert_called_once_with(
            collection_name=COLLECTION,
            payload={"user_id": "new_user"},
            points=[1, 2],
        )

    def test_migrates_multiple_batches(self):
        store = self._make_store()

        pt1 = MagicMock()
        pt1.id = 1
        pt2 = MagicMock()
        pt2.id = 2

        store.client.scroll.side_effect = [
            ([pt1], "next_offset"),
            ([pt2], None),
        ]

        count = store.migrate_user_id("old", "new")

        assert count == 2
        assert store.client.set_payload.call_count == 2

    def test_migrates_zero_when_no_matches(self):
        store = self._make_store()
        store.client.scroll.return_value = ([], None)

        count = store.migrate_user_id("ghost", "new")

        assert count == 0
        store.client.set_payload.assert_not_called()
