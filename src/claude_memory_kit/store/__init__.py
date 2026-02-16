from .qdrant_store import QdrantStore
from .sqlite import SqliteStore


class Store:
    """Cloud-only store: Qdrant for memories, SQLite for auth only."""

    def __init__(self, path: str):
        self.path = path
        self.qdrant = QdrantStore(path)
        self.auth_db = SqliteStore(path)

    async def init(self) -> None:
        self.auth_db.migrate()
        self.qdrant.ensure_collection()

    def count_user_data(self, user_id: str) -> dict:
        count = self.qdrant.count_memories(user_id=user_id)
        return {"memories": count, "total": count}

    def migrate_user_data(self, from_id: str, to_id: str) -> dict:
        count = self.qdrant.migrate_user_id(from_id, to_id)
        return {"memories": count, "total": count}
