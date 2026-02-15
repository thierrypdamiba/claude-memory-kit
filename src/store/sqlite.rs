use std::path::Path;
use anyhow::Result;
use rusqlite::Connection;

use crate::types::Memory;

pub struct SqliteStore {
    conn: Connection,
}

impl SqliteStore {
    pub fn open(store_path: &Path) -> Result<Self> {
        let db_path = store_path.join("index.db");
        let conn = Connection::open(&db_path)?;

        conn.execute_batch("
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                created TEXT NOT NULL,
                gate TEXT NOT NULL,
                person TEXT,
                project TEXT,
                confidence REAL NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 1,
                decay_class TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                category TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content, person, project,
                content='memories', content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, person, project)
                VALUES (new.rowid, new.content, new.person, new.project);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, person, project)
                VALUES ('delete', old.rowid, old.content, old.person, old.project);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, person, project)
                VALUES ('delete', old.rowid, old.content, old.person, old.project);
                INSERT INTO memories_fts(rowid, content, person, project)
                VALUES (new.rowid, new.content, new.person, new.project);
            END;
        ")?;

        Ok(Self { conn })
    }

    pub fn index_memory(&self, memory: &Memory) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO memories \
             (id, created, gate, person, project, confidence, \
              last_accessed, access_count, decay_class, content) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            rusqlite::params![
                memory.id,
                memory.created.to_rfc3339(),
                memory.gate.as_str(),
                memory.person,
                memory.project,
                memory.confidence,
                memory.last_accessed.to_rfc3339(),
                memory.access_count,
                serde_json::to_string(&memory.decay_class)?,
                memory.content,
            ],
        )?;
        Ok(())
    }

    pub fn search_fts(&self, query: &str, limit: usize) -> Result<Vec<Memory>> {
        let mut stmt = self.conn.prepare(
            "SELECT m.id, m.created, m.gate, m.person, m.project, \
                    m.confidence, m.last_accessed, m.access_count, \
                    m.decay_class, m.content \
             FROM memories_fts f \
             JOIN memories m ON f.rowid = m.rowid \
             WHERE memories_fts MATCH ?1 \
             ORDER BY rank \
             LIMIT ?2"
        )?;

        let rows = stmt.query_map(rusqlite::params![query, limit], |row| {
            Ok(Memory {
                id: row.get(0)?,
                created: parse_dt(row.get::<_, String>(1)?),
                gate: parse_gate(row.get::<_, String>(2)?),
                person: row.get(3)?,
                project: row.get(4)?,
                confidence: row.get(5)?,
                last_accessed: parse_dt(row.get::<_, String>(6)?),
                access_count: row.get(7)?,
                decay_class: parse_decay(row.get::<_, String>(8)?),
                content: row.get(9)?,
            })
        })?;

        let mut results = Vec::new();
        for row in rows {
            results.push(row?);
        }
        Ok(results)
    }

    pub fn touch_memory(&self, id: &str) -> Result<()> {
        self.conn.execute(
            "UPDATE memories SET access_count = access_count + 1, \
             last_accessed = ?1 WHERE id = ?2",
            rusqlite::params![chrono::Utc::now().to_rfc3339(), id],
        )?;
        Ok(())
    }

    pub fn delete_memory(&self, id: &str) -> Result<Option<Memory>> {
        let mem = self.get_memory(id)?;
        if mem.is_some() {
            self.conn.execute(
                "DELETE FROM memories WHERE id = ?1",
                rusqlite::params![id],
            )?;
        }
        Ok(mem)
    }

    fn get_memory(&self, id: &str) -> Result<Option<Memory>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, created, gate, person, project, confidence, \
                    last_accessed, access_count, decay_class, content \
             FROM memories WHERE id = ?1"
        )?;

        let mut rows = stmt.query_map(rusqlite::params![id], |row| {
            Ok(Memory {
                id: row.get(0)?,
                created: parse_dt(row.get::<_, String>(1)?),
                gate: parse_gate(row.get::<_, String>(2)?),
                person: row.get(3)?,
                project: row.get(4)?,
                confidence: row.get(5)?,
                last_accessed: parse_dt(row.get::<_, String>(6)?),
                access_count: row.get(7)?,
                decay_class: parse_decay(row.get::<_, String>(8)?),
                content: row.get(9)?,
            })
        })?;

        match rows.next() {
            Some(Ok(m)) => Ok(Some(m)),
            _ => Ok(None),
        }
    }
}

fn parse_dt(s: String) -> chrono::DateTime<chrono::Utc> {
    chrono::DateTime::parse_from_rfc3339(&s)
        .map(|dt| dt.with_timezone(&chrono::Utc))
        .unwrap_or_else(|_| chrono::Utc::now())
}

fn parse_gate(s: String) -> crate::types::Gate {
    crate::types::Gate::from_str(&s).unwrap_or(crate::types::Gate::Epistemic)
}

fn parse_decay(s: String) -> crate::types::DecayClass {
    serde_json::from_str(&s).unwrap_or(crate::types::DecayClass::Moderate)
}
