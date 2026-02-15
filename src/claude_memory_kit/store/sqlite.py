import os
import json
import sqlite3
from datetime import datetime, timezone

from ..types import (
    Memory, Gate, DecayClass, JournalEntry,
    IdentityCard, OnboardingState,
)


class SqliteStore:
    def __init__(self, store_path: str):
        os.makedirs(store_path, exist_ok=True)
        db_path = os.path.join(store_path, "index.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def migrate(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                created TEXT NOT NULL,
                gate TEXT NOT NULL,
                person TEXT,
                project TEXT,
                confidence REAL NOT NULL DEFAULT 0.9,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 1,
                decay_class TEXT NOT NULL,
                content TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'local'
            );

            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                gate TEXT NOT NULL,
                content TEXT NOT NULL,
                person TEXT,
                project TEXT,
                user_id TEXT NOT NULL DEFAULT 'local'
            );
            CREATE INDEX IF NOT EXISTS idx_journal_date
                ON journal(date);

            CREATE TABLE IF NOT EXISTS identity (
                user_id TEXT PRIMARY KEY DEFAULT 'local',
                person TEXT,
                project TEXT,
                content TEXT NOT NULL,
                last_updated TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS edges (
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                created TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'local',
                PRIMARY KEY (from_id, to_id, relation)
            );

            CREATE TABLE IF NOT EXISTS relationships (
                person TEXT PRIMARY KEY,
                communication_style TEXT,
                vals TEXT,
                energizers TEXT,
                triggers TEXT,
                open_commitments TEXT,
                last_updated TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS onboarding (
                user_id TEXT PRIMARY KEY DEFAULT 'local',
                step INTEGER NOT NULL DEFAULT 0,
                person TEXT,
                project TEXT,
                style TEXT
            );

            CREATE TABLE IF NOT EXISTS archive (
                id TEXT PRIMARY KEY,
                original_gate TEXT,
                content TEXT NOT NULL,
                reason TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'local'
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT DEFAULT '',
                plan TEXT DEFAULT 'free',
                created TEXT NOT NULL,
                last_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT DEFAULT '',
                key_hash TEXT UNIQUE NOT NULL,
                prefix TEXT NOT NULL,
                created TEXT NOT NULL,
                last_used TEXT,
                revoked INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'local',
                scope TEXT NOT NULL DEFAULT 'global',
                condition TEXT NOT NULL,
                enforcement TEXT NOT NULL DEFAULT 'suggest',
                created TEXT NOT NULL,
                last_triggered TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_rules_user
                ON rules(user_id);

        """)
        self._migrate_add_columns()
        # Create user_id indexes after columns are guaranteed to exist
        self.conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_memories_user
                ON memories(user_id);
            CREATE INDEX IF NOT EXISTS idx_journal_user
                ON journal(user_id);
            CREATE INDEX IF NOT EXISTS idx_archive_user
                ON archive(user_id);
        """)
        self._ensure_fts()
        self.conn.commit()

    def _migrate_add_columns(self) -> None:
        """Safely add user_id columns to existing tables."""
        migrations = [
            ("memories", "user_id", "TEXT NOT NULL DEFAULT 'local'"),
            ("journal", "user_id", "TEXT NOT NULL DEFAULT 'local'"),
            ("edges", "user_id", "TEXT NOT NULL DEFAULT 'local'"),
            ("archive", "user_id", "TEXT NOT NULL DEFAULT 'local'"),
        ]
        for table, col, typedef in migrations:
            try:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"
                )
            except sqlite3.OperationalError:
                pass  # column already exists

    def _ensure_fts(self) -> None:
        # Check if FTS table exists
        row = self.conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='memories_fts'"
        ).fetchone()
        if row:
            return
        self.conn.executescript("""
            CREATE VIRTUAL TABLE memories_fts USING fts5(
                content, person, project,
                content='memories', content_rowid='rowid'
            );
            CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, person, project)
                VALUES (new.rowid, new.content, new.person, new.project);
            END;
            CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(
                    memories_fts, rowid, content, person, project
                ) VALUES (
                    'delete', old.rowid, old.content, old.person, old.project
                );
            END;
        """)

    # ---- Memory CRUD ----

    def insert_memory(self, memory: Memory, user_id: str = "local") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO memories "
            "(id, created, gate, person, project, confidence, "
            "last_accessed, access_count, decay_class, content, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                memory.id,
                memory.created.isoformat(),
                memory.gate.value,
                memory.person,
                memory.project,
                memory.confidence,
                memory.last_accessed.isoformat(),
                memory.access_count,
                memory.decay_class.value,
                memory.content,
                user_id,
            ),
        )
        self.conn.commit()

    def get_memory(self, id: str, user_id: str = "local") -> Memory | None:
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ? AND user_id = ?",
            (id, user_id),
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def list_memories(
        self, limit: int = 50, offset: int = 0, user_id: str = "local",
        gate: str | None = None, person: str | None = None,
        project: str | None = None,
    ) -> list[Memory]:
        clauses = ["user_id = ?"]
        params: list = [user_id]
        if gate:
            clauses.append("gate = ?")
            params.append(gate)
        if person:
            clauses.append("person = ?")
            params.append(person)
        if project:
            clauses.append("project = ?")
            params.append(project)
        where = " AND ".join(clauses)
        params.extend([limit, offset])
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE {where} "
            "ORDER BY created DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def search_fts(
        self, query: str, limit: int = 5, user_id: str = "local"
    ) -> list[Memory]:
        try:
            rows = self.conn.execute(
                "SELECT m.* FROM memories_fts f "
                "JOIN memories m ON f.rowid = m.rowid "
                "WHERE memories_fts MATCH ? AND m.user_id = ? "
                "ORDER BY rank LIMIT ?",
                (query, user_id, limit),
            ).fetchall()
            return [self._row_to_memory(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def touch_memory(self, id: str, user_id: str = "local") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET access_count = access_count + 1, "
            "last_accessed = ? WHERE id = ? AND user_id = ?",
            (now, id, user_id),
        )
        self.conn.commit()

    def delete_memory(self, id: str, user_id: str = "local") -> Memory | None:
        mem = self.get_memory(id, user_id)
        if mem:
            self.conn.execute(
                "DELETE FROM memories WHERE id = ? AND user_id = ?",
                (id, user_id),
            )
            self.conn.commit()
        return mem

    def update_memory(
        self, id: str, user_id: str = "local", **kwargs
    ) -> None:
        """Update memory fields. Supported: content, gate, person, project."""
        allowed = {"content", "gate", "person", "project"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [id, user_id]
        self.conn.execute(
            f"UPDATE memories SET {set_clause} "
            "WHERE id = ? AND user_id = ?",
            params,
        )
        self.conn.commit()

    def set_pinned(
        self, id: str, pinned: bool, user_id: str = "local"
    ) -> None:
        """Set the pinned flag on a memory. Adds column if missing."""
        try:
            self.conn.execute(
                "ALTER TABLE memories ADD COLUMN pinned INTEGER DEFAULT 0"
            )
        except Exception:
            pass
        self.conn.execute(
            "UPDATE memories SET pinned = ? WHERE id = ? AND user_id = ?",
            (1 if pinned else 0, id, user_id),
        )
        self.conn.commit()

    def count_memories(self, user_id: str = "local") -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else 0

    def count_by_gate(self, user_id: str = "local") -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT gate, COUNT(*) FROM memories "
            "WHERE user_id = ? GROUP BY gate",
            (user_id,),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def update_confidence(
        self, id: str, confidence: float, user_id: str = "local"
    ) -> None:
        self.conn.execute(
            "UPDATE memories SET confidence = ? "
            "WHERE id = ? AND user_id = ?",
            (confidence, id, user_id),
        )
        self.conn.commit()

    # ---- Journal ----

    def insert_journal(
        self, entry: JournalEntry, user_id: str = "local"
    ) -> None:
        date = entry.timestamp.strftime("%Y-%m-%d")
        self.conn.execute(
            "INSERT INTO journal "
            "(date, timestamp, gate, content, person, project, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                date,
                entry.timestamp.isoformat(),
                entry.gate.value,
                entry.content,
                entry.person,
                entry.project,
                user_id,
            ),
        )
        self.conn.commit()

    def recent_journal(
        self, days: int = 3, user_id: str = "local"
    ) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM journal WHERE user_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (user_id, days * 20),
        ).fetchall()
        return [dict(r) for r in rows]

    def journal_by_date(
        self, date: str, user_id: str = "local"
    ) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM journal "
            "WHERE date = ? AND user_id = ? ORDER BY timestamp",
            (date, user_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def stale_journal_dates(
        self, max_age_days: int = 14, user_id: str = "local"
    ) -> list[str]:
        from datetime import timedelta
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=max_age_days)
        ).strftime("%Y-%m-%d")
        rows = self.conn.execute(
            "SELECT DISTINCT date FROM journal "
            "WHERE date < ? AND user_id = ? ORDER BY date",
            (cutoff, user_id),
        ).fetchall()
        return [r[0] for r in rows]

    def archive_journal_date(
        self, date: str, user_id: str = "local"
    ) -> None:
        self.conn.execute(
            "DELETE FROM journal WHERE date = ? AND user_id = ?",
            (date, user_id),
        )
        self.conn.commit()

    # ---- Identity ----

    def get_identity(self, user_id: str = "local") -> IdentityCard | None:
        row = self.conn.execute(
            "SELECT * FROM identity WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            # Fallback: check old singleton format (id=1)
            row = self.conn.execute(
                "SELECT * FROM identity WHERE id = 1"
            ).fetchone() if self._has_column("identity", "id") else None
            if not row:
                return None
        return IdentityCard(
            person=row["person"],
            project=row["project"],
            content=row["content"],
            last_updated=datetime.fromisoformat(row["last_updated"]),
        )

    def set_identity(
        self, card: IdentityCard, user_id: str = "local"
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO identity "
            "(user_id, person, project, content, last_updated) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id, card.person, card.project,
                card.content, card.last_updated.isoformat(),
            ),
        )
        self.conn.commit()

    def _has_column(self, table: str, column: str) -> bool:
        cols = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(c[1] == column for c in cols)

    # ---- Graph edges ----

    def add_edge(
        self, from_id: str, to_id: str, relation: str,
        user_id: str = "local",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO edges "
            "(from_id, to_id, relation, created, user_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (from_id, to_id, relation, now, user_id),
        )
        self.conn.commit()

    def find_related(
        self, memory_id: str, depth: int = 2, user_id: str = "local"
    ) -> list[dict]:
        visited = set()
        current = {memory_id}
        results = []

        for _ in range(depth):
            if not current:
                break
            placeholders = ",".join("?" for _ in current)
            params = list(current) * 3 + [user_id]
            rows = self.conn.execute(
                f"SELECT e.from_id, e.to_id, e.relation, m.content "
                f"FROM edges e "
                f"JOIN memories m ON m.id = CASE "
                f"  WHEN e.from_id IN ({placeholders}) THEN e.to_id "
                f"  ELSE e.from_id END "
                f"WHERE (e.from_id IN ({placeholders}) "
                f"  OR e.to_id IN ({placeholders})) "
                f"  AND e.user_id = ?",
                params,
            ).fetchall()

            next_level = set()
            for r in rows:
                other = r[1] if r[0] in current else r[0]
                if other not in visited and other != memory_id:
                    visited.add(other)
                    next_level.add(other)
                    preview = r[3][:200] if r[3] else ""
                    results.append({
                        "id": other,
                        "relation": r[2],
                        "preview": preview,
                    })
            current = next_level

        return results

    def auto_link(
        self, memory_id: str, person: str | None,
        project: str | None, user_id: str = "local",
    ) -> None:
        if person:
            rows = self.conn.execute(
                "SELECT id FROM memories "
                "WHERE person = ? AND id != ? AND user_id = ?",
                (person, memory_id, user_id),
            ).fetchall()
            for r in rows:
                self.add_edge(memory_id, r[0], "RELATED_TO", user_id)

        if project:
            rows = self.conn.execute(
                "SELECT id FROM memories "
                "WHERE project = ? AND id != ? AND user_id = ?",
                (project, memory_id, user_id),
            ).fetchall()
            for r in rows:
                self.add_edge(memory_id, r[0], "RELATED_TO", user_id)

    # ---- Onboarding ----

    def get_onboarding(self, user_id: str = "local") -> OnboardingState | None:
        row = self.conn.execute(
            "SELECT * FROM onboarding WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            # Fallback: old singleton format
            row = self.conn.execute(
                "SELECT * FROM onboarding WHERE id = 1"
            ).fetchone() if self._has_column("onboarding", "id") else None
            if not row:
                return None
        return OnboardingState(
            step=row["step"],
            person=row["person"],
            project=row["project"],
            style=row["style"],
        )

    def set_onboarding(
        self, state: OnboardingState, user_id: str = "local"
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO onboarding "
            "(user_id, step, person, project, style) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, state.step, state.person, state.project, state.style),
        )
        self.conn.commit()

    def delete_onboarding(self, user_id: str = "local") -> None:
        self.conn.execute(
            "DELETE FROM onboarding WHERE user_id = ?", (user_id,)
        )
        self.conn.commit()

    # ---- Archive ----

    def archive_memory(
        self, id: str, gate: str, content: str, reason: str,
        user_id: str = "local",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO archive "
            "(id, original_gate, content, reason, archived_at, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (id, gate, content, reason, now, user_id),
        )
        self.conn.commit()

    # ---- Users ----

    def upsert_user(
        self, user_id: str, email: str | None = None,
        name: str = "", plan: str = "free",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO users (id, email, name, plan, created, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "last_seen = ?, name = COALESCE(?, name), "
            "email = COALESCE(?, email)",
            (user_id, email, name, plan, now, now, now, name, email),
        )
        self.conn.commit()

    def get_user(self, user_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    # ---- API Keys ----

    def insert_api_key(
        self, key_id: str, user_id: str, key_hash: str,
        prefix: str, name: str = "",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO api_keys "
            "(id, user_id, name, key_hash, prefix, created) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (key_id, user_id, name, key_hash, prefix, now),
        )
        self.conn.commit()

    def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM api_keys "
            "WHERE key_hash = ? AND revoked = 0",
            (key_hash,),
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), row["id"]),
            )
            self.conn.commit()
        return dict(row) if row else None

    def list_api_keys(self, user_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, name, prefix, created, last_used, revoked "
            "FROM api_keys WHERE user_id = ? ORDER BY created DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        cur = self.conn.execute(
            "UPDATE api_keys SET revoked = 1 "
            "WHERE id = ? AND user_id = ?",
            (key_id, user_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ---- Rules ----

    def list_rules(self, user_id: str = "local") -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM rules WHERE user_id = ? ORDER BY created DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_rule(self, rule_id: str, user_id: str = "local") -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM rules WHERE id = ? AND user_id = ?",
            (rule_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    def insert_rule(
        self, rule_id: str, user_id: str, scope: str,
        condition: str, enforcement: str = "suggest",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO rules "
            "(id, user_id, scope, condition, enforcement, created) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rule_id, user_id, scope, condition, enforcement, now),
        )
        self.conn.commit()

    def update_rule(
        self, rule_id: str, user_id: str = "local", **kwargs
    ) -> bool:
        allowed = {"scope", "condition", "enforcement"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [rule_id, user_id]
        cur = self.conn.execute(
            f"UPDATE rules SET {set_clause} "
            "WHERE id = ? AND user_id = ?",
            params,
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_rule(self, rule_id: str, user_id: str = "local") -> bool:
        cur = self.conn.execute(
            "DELETE FROM rules WHERE id = ? AND user_id = ?",
            (rule_id, user_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def touch_rule(self, rule_id: str, user_id: str = "local") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE rules SET last_triggered = ? "
            "WHERE id = ? AND user_id = ?",
            (now, rule_id, user_id),
        )
        self.conn.commit()

    # ---- Migration ----

    def count_user_data(self, user_id: str) -> dict:
        """Count all data owned by a user_id across tables."""
        counts = {}
        for table in ("memories", "journal", "edges", "archive"):
            row = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            counts[table] = row[0] if row else 0
        # identity and onboarding are single-row per user
        row = self.conn.execute(
            "SELECT COUNT(*) FROM identity WHERE user_id = ?", (user_id,)
        ).fetchone()
        counts["identity"] = row[0] if row else 0
        row = self.conn.execute(
            "SELECT COUNT(*) FROM onboarding WHERE user_id = ?", (user_id,)
        ).fetchone()
        counts["onboarding"] = row[0] if row else 0
        return counts

    def migrate_user_data(self, from_id: str, to_id: str) -> dict:
        """Move all data from one user_id to another. Returns counts of migrated rows."""
        counts = {}
        for table in ("memories", "journal", "edges", "archive"):
            cur = self.conn.execute(
                f"UPDATE {table} SET user_id = ? WHERE user_id = ?",
                (to_id, from_id),
            )
            counts[table] = cur.rowcount

        # Identity: merge or move
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM identity WHERE user_id = ?", (to_id,)
        ).fetchone()
        if existing and existing[0] > 0:
            # Target already has identity, delete source
            self.conn.execute(
                "DELETE FROM identity WHERE user_id = ?", (from_id,)
            )
            counts["identity"] = 0
        else:
            cur = self.conn.execute(
                "UPDATE identity SET user_id = ? WHERE user_id = ?",
                (to_id, from_id),
            )
            counts["identity"] = cur.rowcount

        # Onboarding: same logic
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM onboarding WHERE user_id = ?", (to_id,)
        ).fetchone()
        if existing and existing[0] > 0:
            self.conn.execute(
                "DELETE FROM onboarding WHERE user_id = ?", (from_id,)
            )
            counts["onboarding"] = 0
        else:
            cur = self.conn.execute(
                "UPDATE onboarding SET user_id = ? WHERE user_id = ?",
                (to_id, from_id),
            )
            counts["onboarding"] = cur.rowcount

        self.conn.commit()
        return counts

    # ---- Helpers ----

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            created=datetime.fromisoformat(row["created"]),
            gate=Gate(row["gate"]),
            person=row["person"],
            project=row["project"],
            confidence=row["confidence"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            access_count=row["access_count"],
            decay_class=DecayClass(row["decay_class"]),
            content=row["content"],
        )
