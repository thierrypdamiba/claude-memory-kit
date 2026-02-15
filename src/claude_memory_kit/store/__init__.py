from .sqlite import SqliteStore
from .vectors import VectorStore


class Store:
    """Combined store: SQLite (content, FTS, graph, identity, journal) + Qdrant (vectors)."""

    def __init__(self, path: str):
        self.path = path
        self.db = SqliteStore(path)
        self.vectors = VectorStore(path)

    async def init(self) -> None:
        self.db.migrate()
        self.vectors.ensure_collection()

    def count_user_data(self, user_id: str) -> dict:
        """Count data owned by a user across all stores."""
        counts = self.db.count_user_data(user_id)
        counts["total"] = sum(
            counts.get(t, 0) for t in ("memories", "journal", "edges", "archive")
        )
        return counts

    def migrate_user_data(self, from_id: str, to_id: str) -> dict:
        """Migrate all data from one user_id to another across all stores."""
        sqlite_counts = self.db.migrate_user_data(from_id, to_id)
        vector_count = self.vectors.migrate_user_id(from_id, to_id)
        return {
            **sqlite_counts,
            "vectors": vector_count,
        }
