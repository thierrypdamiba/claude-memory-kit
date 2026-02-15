use anyhow::Result;
use crate::server::MemoryServer;
use crate::store::markdown;

impl MemoryServer {
    pub async fn do_recall(&self, query: &str) -> Result<String> {
        let store = self.store.lock().await;
        let mut results = Vec::new();
        let mut seen_ids = std::collections::HashSet::new();

        // 1. FTS5 search
        match store.db.search_fts(query, 5) {
            Ok(fts_results) => {
                for mem in fts_results {
                    if seen_ids.insert(mem.id.clone()) {
                        let _ = store.db.touch_memory(&mem.id);
                        results.push(format!(
                            "[{}] ({}, {}) {}\n  id: {}",
                            mem.gate.as_str(),
                            mem.created.format("%Y-%m-%d"),
                            mem.person.as_deref().unwrap_or("?"),
                            mem.content,
                            mem.id,
                        ));
                    }
                }
            }
            Err(e) => tracing::warn!("fts5 search failed: {}", e),
        }

        // 2. Qdrant vector search
        if let Some(ref vectors) = store.vectors {
            match vectors.search_similar(query, 5).await {
                Ok(vec_results) => {
                    for (mem_id, score) in vec_results {
                        if seen_ids.insert(mem_id.clone()) {
                            results.push(format!(
                                "[vector match, score={:.2}] id: {}", score, mem_id
                            ));
                        }
                    }
                }
                Err(e) => tracing::warn!("qdrant search failed: {}", e),
            }
        }

        // 3. Neo4j graph traversal (for sparse results)
        if results.len() < 3 {
            if let Some(ref graph) = store.graph {
                for id in seen_ids.clone().iter().take(2) {
                    match graph.find_related(id, 2).await {
                        Ok(related) => {
                            for (rid, relation, preview) in related {
                                if seen_ids.insert(rid.clone()) {
                                    results.push(format!(
                                        "[graph: {}] {} (id: {})",
                                        relation, preview, rid
                                    ));
                                }
                            }
                        }
                        Err(e) => tracing::warn!("neo4j traversal failed: {}", e),
                    }
                }
            }
        }

        // 4. Fallback: grep markdown
        if results.is_empty() {
            match markdown::search_all(&self.store_path, query) {
                Ok(grep_results) => {
                    for content in grep_results.iter().take(3) {
                        let preview: String = content.chars().take(300).collect();
                        results.push(format!("[file search] {}", preview));
                    }
                }
                Err(e) => tracing::warn!("markdown search failed: {}", e),
            }
        }

        if results.is_empty() {
            Ok("No memories found matching that query.".into())
        } else {
            Ok(format!(
                "Found {} memories:\n\n{}",
                results.len(),
                results.join("\n\n")
            ))
        }
    }
}
