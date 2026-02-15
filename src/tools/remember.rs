use anyhow::Result;
use chrono::Utc;

use crate::server::MemoryServer;
use crate::types::{DecayClass, Gate, JournalEntry, Memory};
use crate::store::markdown;

impl MemoryServer {
    pub async fn do_remember(
        &self,
        content: &str,
        gate: &str,
        person: Option<&str>,
        project: Option<&str>,
    ) -> Result<String> {
        let gate = Gate::from_str(gate)
            .ok_or_else(|| anyhow::anyhow!(
                "invalid gate '{}'. use: behavioral, relational, epistemic, promissory", gate
            ))?;

        let now = Utc::now();
        let id = format!(
            "mem_{}_{}",
            now.format("%Y%m%d_%H%M%S"),
            &uuid::Uuid::new_v4().to_string()[..4]
        );

        let memory = Memory {
            id: id.clone(),
            created: now,
            gate: gate.clone(),
            person: person.map(|s| s.to_string()),
            project: project.map(|s| s.to_string()),
            confidence: 0.9,
            last_accessed: now,
            access_count: 1,
            decay_class: DecayClass::from_gate(&gate),
            content: content.to_string(),
        };

        // 1. Write to today's journal
        let entry = JournalEntry {
            timestamp: now,
            gate: gate.clone(),
            content: content.to_string(),
            person: person.map(|s| s.to_string()),
            project: project.map(|s| s.to_string()),
        };
        markdown::write_journal_entry(&self.store_path, &entry)?;

        // 2. Write long-term memory file
        markdown::write_long_term(&self.store_path, &memory)?;

        // 3. Index in FTS5, embed in Qdrant, add to Neo4j graph
        let store = self.store.lock().await;
        store.db.index_memory(&memory)?;

        if let Some(ref vectors) = store.vectors {
            if let Err(e) = vectors.embed_and_store(&id, content, person, project).await {
                tracing::warn!("qdrant embed failed: {}", e);
            }
        }

        if let Some(ref graph) = store.graph {
            if let Err(e) = graph.upsert_memory_node(
                &id, gate.as_str(), person, project, content,
            ).await {
                tracing::warn!("neo4j upsert failed: {}", e);
            }
            if let Err(e) = graph.auto_link(&id, person, project).await {
                tracing::warn!("neo4j auto-link failed: {}", e);
            }
        }

        Ok(format!(
            "Remembered [{}]: {} (id: {})",
            gate.as_str(),
            if content.len() > 80 { &content[..80] } else { content },
            id
        ))
    }
}
