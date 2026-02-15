pub mod markdown;
pub mod sqlite;
pub mod embeddings;
pub mod graph;

use std::path::{Path, PathBuf};
use anyhow::Result;

pub struct Store {
    pub path: PathBuf,
    pub db: sqlite::SqliteStore,
    pub vectors: Option<embeddings::EmbeddingStore>,
    pub graph: Option<graph::GraphStore>,
}

impl Store {
    pub async fn init(path: &Path) -> Result<Self> {
        // Ensure directory structure exists
        let dirs = [
            "journal", "digests", "summaries", "themes",
            "long-term/people", "long-term/learnings",
            "long-term/decisions", "long-term/commitments",
            "archive/identity",
        ];
        for dir in &dirs {
            std::fs::create_dir_all(path.join(dir))?;
        }

        let db = sqlite::SqliteStore::open(path)?;

        // Try to connect to Qdrant (optional, degrades gracefully)
        let vectors = match embeddings::EmbeddingStore::connect().await {
            Ok(v) => {
                tracing::info!("qdrant cloud connected");
                Some(v)
            }
            Err(e) => {
                tracing::warn!("qdrant unavailable, vector search disabled: {}", e);
                None
            }
        };

        // Try to connect to Neo4j (optional, degrades gracefully)
        let graph = match graph::GraphStore::connect().await {
            Ok(g) => {
                tracing::info!("neo4j aura connected");
                Some(g)
            }
            Err(e) => {
                tracing::warn!("neo4j unavailable, graph search disabled: {}", e);
                None
            }
        };

        Ok(Self {
            path: path.to_path_buf(),
            db,
            vectors,
            graph,
        })
    }
}
