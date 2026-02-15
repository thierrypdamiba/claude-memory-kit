import hashlib
import os
import logging
import struct

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Document,
    Filter, FieldCondition, MatchValue,
    HnswConfigDiff, KeywordIndexParams, KeywordIndexType,
    FilterSelector,
)

from ..config import get_qdrant_config

log = logging.getLogger("cmk")

COLLECTION = "cmk_memories"
JINA_MODEL = "jinaai/jina-embeddings-v3"
JINA_DIM = 1024
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
LOCAL_DIM = 384


def _stable_id(memory_id: str) -> int:
    """Deterministic hash that survives across Python sessions."""
    digest = hashlib.sha256(memory_id.encode()).digest()
    return struct.unpack(">Q", digest[:8])[0] >> 1


class VectorStore:
    def __init__(self, store_path: str):
        self._disabled = False
        self._cloud = False
        self._jina_key = ""
        self._fastembed_model = None
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
                    log.warning("qdrant locked. vectors disabled, FTS only.")
                    self.client = None
                    self._disabled = True
                else:
                    raise

    @property
    def _local_model(self):
        if self._fastembed_model is None:
            from fastembed import TextEmbedding
            self._fastembed_model = TextEmbedding(LOCAL_MODEL)
        return self._fastembed_model

    def _embed_local(self, text: str) -> list[float]:
        return list(self._local_model.embed([text]))[0].tolist()

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

    def ensure_collection(self) -> None:
        if self._disabled:
            return
        try:
            names = [c.name for c in self.client.get_collections().collections]
            if COLLECTION not in names:
                dim = JINA_DIM if self._cloud else LOCAL_DIM
                kwargs = {}
                if self._cloud:
                    kwargs["hnsw_config"] = HnswConfigDiff(payload_m=16, m=0)
                self.client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(
                        size=dim, distance=Distance.COSINE
                    ),
                    **kwargs,
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
                log.info("created collection: %s (cloud=%s)", COLLECTION, self._cloud)
        except Exception as e:
            log.warning("collection setup failed: %s. vectors disabled.", e)
            self.client = None
            self._disabled = True

    def upsert(
        self,
        memory_id: str,
        content: str,
        person: str | None,
        project: str | None,
        user_id: str | None = None,
    ) -> None:
        if self._disabled:
            return
        point_id = _stable_id(memory_id)
        payload = {
            "memory_id": memory_id,
            "content": content,
            "person": person or "",
            "project": project or "",
        }
        if user_id:
            payload["user_id"] = user_id

        if self._cloud:
            vector = self._jina_doc(content, task="retrieval.passage")
        else:
            vector = self._embed_local(content)

        self.client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
    ) -> list[tuple[str, float]]:
        if self._disabled:
            return []

        if self._cloud:
            q = self._jina_doc(query, task="retrieval.query")
        else:
            q = self._embed_local(query)

        query_filter = None
        if user_id:
            query_filter = Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ])

        results = self.client.query_points(
            collection_name=COLLECTION,
            query=q,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            (p.payload.get("memory_id", ""), p.score)
            for p in results.points
        ]

    def migrate_user_id(self, from_id: str, to_id: str) -> int:
        """Update user_id on all points belonging to from_id. Returns count of migrated points."""
        if self._disabled:
            return 0

        # Scroll through all points with the old user_id
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
            # Update payload on each point
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
