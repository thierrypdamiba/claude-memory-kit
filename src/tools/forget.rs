use anyhow::Result;
use crate::server::MemoryServer;

impl MemoryServer {
    pub async fn do_forget(&self, memory_id: &str, reason: &str) -> Result<String> {
        let store = self.store.lock().await;

        // 1. Remove from SQLite
        let memory = store.db.delete_memory(memory_id)?;
        if memory.is_none() {
            return Ok(format!("No memory found with id: {}", memory_id));
        }
        let memory = memory.unwrap();

        // 2. Archive with reason
        let archive_dir = self.store_path.join("archive");
        std::fs::create_dir_all(&archive_dir)?;
        let archive_file = archive_dir.join(format!("{}.md", memory_id));
        let content = format!(
            "---\narchived: {}\nreason: {}\noriginal_gate: {}\n---\n\n{}\n",
            chrono::Utc::now().to_rfc3339(),
            reason,
            memory.gate.as_str(),
            memory.content,
        );
        std::fs::write(&archive_file, content)?;

        // 3. Remove from Qdrant
        if let Some(ref vectors) = store.vectors {
            if let Err(e) = vectors.delete_point(memory_id).await {
                tracing::warn!("qdrant delete failed: {}", e);
            }
        }

        // 4. Remove from Neo4j
        if let Some(ref graph) = store.graph {
            if let Err(e) = graph.delete_node(memory_id).await {
                tracing::warn!("neo4j delete failed: {}", e);
            }
        }

        Ok(format!(
            "Forgotten: {} (reason: {}). Archived for accountability.",
            memory_id, reason
        ))
    }
}
