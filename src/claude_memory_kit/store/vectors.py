import hashlib
import os
import logging
import struct

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Document,
    Filter, FieldCondition, MatchValue, MatchText,
    HnswConfigDiff, KeywordIndexParams, KeywordIndexType,
    FilterSelector,
    SparseVectorParams, SparseVector, Modifier,
    Prefetch, FusionQuery, Fusion,
    TextIndexParams, TokenizerType,
)

from ..config import get_qdrant_config

log = logging.getLogger("cmk")

COLLECTION = "cmk_memories"
JINA_MODEL = "jinaai/jina-embeddings-v3"
JINA_DIM = 1024
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
LOCAL_DIM = 384
SPARSE_MODEL = "Qdrant/bm25"
BM25_CLOUD_MODEL = "Qdrant/bm25"


def _stable_id(memory_id: str) -> int:
    """Deterministic hash that survives across Python sessions."""
    digest = hashlib.sha256(memory_id.encode()).digest()
    return struct.unpack(">Q", digest[:8])[0] >> 1


class VectorStore:
    def __init__(self, store_path: str):
        self._disabled = False
        self._cloud = False
        self._jina_key = ""
        self._fastembed_dense = None
        self._fastembed_sparse = None
        cfg = get_qdrant_config()

        if cfg["mode"] == "cloud":
            self._cloud = True
            self._jina_key = cfg.get("jina_api_key", "")
            log.info("connecting to qdrant cloud (QCI + jina)")
            try:
                self.client = QdrantClient(
                    url=cfg["url"],
                    api_key=cfg.get("api_key", ""),
                    cloud_inference=True,
                    timeout=30,
                )
            except Exception as e:
                log.warning("qdrant cloud failed: %s. vectors disabled.", e)
                self.client = None
                self._disabled = True
                return
        else:
            qdrant_path = os.path.join(store_path, "qdrant")
            os.makedirs(qdrant_path, exist_ok=True)
            try:
                self.client = QdrantClient(path=qdrant_path)
            except RuntimeError as e:
                if "already accessed" in str(e):
                    log.debug("qdrant locked. vectors disabled, FTS only.")
                    self.client = None
                    self._disabled = True
                else:
                    raise

    # ---- Embedding helpers ----

    @property
    def _local_dense_model(self):
        if self._fastembed_dense is None:
            from fastembed import TextEmbedding
            self._fastembed_dense = TextEmbedding(LOCAL_MODEL)
        return self._fastembed_dense

    @property
    def _local_sparse_model(self):
        if self._fastembed_sparse is None:
            from fastembed import SparseTextEmbedding
            self._fastembed_sparse = SparseTextEmbedding(SPARSE_MODEL)
        return self._fastembed_sparse

    def _embed_local(self, text: str) -> list[float]:
        return list(self._local_dense_model.embed([text]))[0].tolist()

    def _embed_sparse_local(self, text: str) -> SparseVector:
        emb = list(self._local_sparse_model.embed([text]))[0]
        return SparseVector(
            indices=emb.indices.tolist(),
            values=emb.values.tolist(),
        )

    def _query_sparse_local(self, text: str) -> SparseVector:
        emb = list(self._local_sparse_model.query_embed(text))[0]
        return SparseVector(
            indices=emb.indices.tolist(),
            values=emb.values.tolist(),
        )

    def _jina_doc(self, text: str, task: str = "retrieval.passage"):
        return Document(
            text=text,
            model=JINA_MODEL,
            options={
                "jina-api-key": self._jina_key,
                "dimensions": JINA_DIM,
                "task": task,
            },
        )

    def _sparse_doc(self, text: str):
        return Document(text=text, model=BM25_CLOUD_MODEL)

    # ---- Collection management ----

    def _is_legacy_collection(self) -> bool:
        """Check if existing collection uses the old single-vector schema."""
        try:
            info = self.client.get_collection(COLLECTION)
            vc = info.config.params.vectors
            if isinstance(vc, dict) and "dense" in vc:
                return False
            return True
        except Exception:
            return False

    def _migrate_collection(self) -> None:
        """Migrate from single-vector to named-vector (dense + sparse) schema."""
        log.info("migrating collection %s to hybrid (dense + sparse) schema", COLLECTION)

        all_points = []
        offset = None
        while True:
            results, offset = self.client.scroll(
                collection_name=COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            if not results:
                break
            all_points.extend(results)
            if offset is None:
                break

        log.info("read %d points from legacy collection", len(all_points))

        self.client.delete_collection(COLLECTION)
        self._create_hybrid_collection()

        batch_size = 50
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            new_points = []
            for pt in batch:
                content = pt.payload.get("content", "") if pt.payload else ""
                old_vector = pt.vector
                if isinstance(old_vector, dict):
                    old_vector = old_vector.get("", old_vector)

                if self._cloud:
                    vector = {
                        "dense": self._jina_doc(content, task="retrieval.passage"),
                        "sparse": self._sparse_doc(content),
                    }
                else:
                    dense = old_vector if isinstance(old_vector, list) else self._embed_local(content)
                    vector = {
                        "dense": dense,
                        "sparse": self._embed_sparse_local(content),
                    }

                new_points.append(PointStruct(
                    id=pt.id,
                    vector=vector,
                    payload=pt.payload,
                ))

            if new_points:
                self.client.upsert(
                    collection_name=COLLECTION,
                    points=new_points,
                )
            log.info("migrated batch %d-%d of %d", i, i + len(batch), len(all_points))

        log.info("migration complete: %d points migrated to hybrid schema", len(all_points))

    def _create_hybrid_collection(self) -> None:
        """Create collection with named dense + sparse vectors."""
        dim = JINA_DIM if self._cloud else LOCAL_DIM
        kwargs = {}
        if self._cloud:
            kwargs["hnsw_config"] = HnswConfigDiff(payload_m=16, m=0)

        self.client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": VectorParams(size=dim, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(modifier=Modifier.IDF),
            },
            **kwargs,
        )

        # Text index on content for full-text search (replaces SQLite FTS5)
        self.client.create_payload_index(
            collection_name=COLLECTION,
            field_name="content",
            field_schema=TextIndexParams(
                type="text",
                tokenizer=TokenizerType.WORD,
                min_token_len=2,
                lowercase=True,
            ),
        )

        # Payload indexes for metadata queries
        for field in ("type", "gate", "sensitivity", "person", "project",
                       "memory_id", "date", "rule_id"):
            self.client.create_payload_index(
                collection_name=COLLECTION,
                field_name=field,
                field_schema=KeywordIndexParams(
                    type=KeywordIndexType.KEYWORD,
                ),
            )

        if self._cloud:
            self.client.create_payload_index(
                collection_name=COLLECTION,
                field_name="user_id",
                field_schema=KeywordIndexParams(
                    type=KeywordIndexType.KEYWORD,
                    is_tenant=True,
                ),
            )

    def ensure_collection(self) -> None:
        if self._disabled:
            return
        try:
            names = [c.name for c in self.client.get_collections().collections]
            if COLLECTION not in names:
                self._create_hybrid_collection()
                log.info("created hybrid collection: %s (cloud=%s)", COLLECTION, self._cloud)
            elif self._is_legacy_collection():
                self._migrate_collection()
        except Exception as e:
            log.warning("collection setup failed: %s. vectors disabled.", e)
            self.client = None
            self._disabled = True

    # ---- Upsert ----

    def upsert(
        self,
        memory_id: str,
        content: str,
        person: str | None,
        project: str | None,
        user_id: str | None = None,
        *,
        gate: str | None = None,
        confidence: float | None = None,
        created: float | None = None,
        last_accessed: float | None = None,
        access_count: int | None = None,
        decay_class: str | None = None,
        pinned: bool | None = None,
        sensitivity: str | None = None,
        sensitivity_reason: str | None = None,
    ) -> None:
        if self._disabled:
            return
        point_id = _stable_id(memory_id)
        payload: dict = {
            "type": "memory",
            "memory_id": memory_id,
            "content": content,
            "person": person or "",
            "project": project or "",
        }
        if user_id:
            payload["user_id"] = user_id
        if gate is not None:
            payload["gate"] = gate
        if confidence is not None:
            payload["confidence"] = confidence
        if created is not None:
            payload["created"] = created
        if last_accessed is not None:
            payload["last_accessed"] = last_accessed
        if access_count is not None:
            payload["access_count"] = access_count
        if decay_class is not None:
            payload["decay_class"] = decay_class
        if pinned is not None:
            payload["pinned"] = pinned
        if sensitivity is not None:
            payload["sensitivity"] = sensitivity
        if sensitivity_reason is not None:
            payload["sensitivity_reason"] = sensitivity_reason

        if self._cloud:
            vector = {
                "dense": self._jina_doc(content, task="retrieval.passage"),
                "sparse": self._sparse_doc(content),
            }
        else:
            vector = {
                "dense": self._embed_local(content),
                "sparse": self._embed_sparse_local(content),
            }

        self.client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    # ---- Hybrid search with RRF ----

    def search(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[tuple[str, float]]:
        if self._disabled:
            return []

        must_conditions = [
            FieldCondition(key="type", match=MatchValue(value="memory")),
        ]
        if user_id:
            must_conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        query_filter = Filter(must=must_conditions)

        if self._cloud:
            dense_query = self._jina_doc(query, task="retrieval.query")
            sparse_query = self._sparse_doc(query)
        else:
            dense_query = self._embed_local(query)
            sparse_query = self._query_sparse_local(query)

        prefetch_limit = max(limit * 4, 20)

        results = self.client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                Prefetch(
                    query=dense_query,
                    using="dense",
                    limit=prefetch_limit,
                    filter=query_filter,
                ),
                Prefetch(
                    query=sparse_query,
                    using="sparse",
                    limit=prefetch_limit,
                    filter=query_filter,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=limit,
            with_payload=True,
        )

        return [
            (p.payload.get("memory_id", ""), p.score)
            for p in results.points
        ]

    # ---- Full-text search via Qdrant text index ----

    def search_text(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[tuple[str, float]]:
        """Keyword search using Qdrant's text index on the content field.

        This replaces the SQLite FTS5 fallback. Each word in the query
        is matched independently (OR semantics, same as FTS5 default).
        Returns (memory_id, score) tuples sorted by relevance.
        """
        if self._disabled:
            return []

        # Build filter conditions
        must = [
            FieldCondition(key="type", match=MatchValue(value="memory")),
            FieldCondition(key="content", match=MatchText(text=query)),
        ]
        if user_id:
            must.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )

        results, _offset = self.client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return [
            (p.payload.get("memory_id", ""), 1.0)
            for p in results
        ]

    # ---- User migration ----

    def migrate_user_id(self, from_id: str, to_id: str) -> int:
        """Update user_id on all points belonging to from_id. Returns count of migrated points."""
        if self._disabled:
            return 0

        migrated = 0
        offset = None
        while True:
            results, offset = self.client.scroll(
                collection_name=COLLECTION,
                scroll_filter=Filter(must=[
                    FieldCondition(key="user_id", match=MatchValue(value=from_id))
                ]),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not results:
                break
            point_ids = [p.id for p in results]
            self.client.set_payload(
                collection_name=COLLECTION,
                payload={"user_id": to_id},
                points=point_ids,
            )
            migrated += len(results)
            if offset is None:
                break

        return migrated

    # ---- Delete ----

    def delete(self, memory_id: str, user_id: str | None = None) -> None:
        if self._disabled:
            return
        conditions = [
            FieldCondition(key="memory_id", match=MatchValue(value=memory_id))
        ]
        if user_id:
            conditions.append(
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            )
        self.client.delete(
            collection_name=COLLECTION,
            points_selector=FilterSelector(
                filter=Filter(must=conditions)
            ),
        )
