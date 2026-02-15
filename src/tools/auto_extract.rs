use anyhow::Result;
use crate::server::MemoryServer;
use crate::extract;

impl MemoryServer {
    pub async fn do_auto_extract(&self, transcript: &str) -> Result<String> {
        let memories = extract::extract_memories(transcript, &self.api_key).await?;

        if memories.is_empty() {
            return Ok("No memories worth keeping from this transcript.".into());
        }

        let mut saved = Vec::new();
        for mem in &memories {
            match self.do_remember(
                &mem.content,
                &mem.gate,
                mem.person.as_deref(),
                mem.project.as_deref(),
            ).await {
                Ok(msg) => saved.push(msg),
                Err(e) => {
                    tracing::warn!("auto-extract save failed: {}", e);
                }
            }
        }

        Ok(format!(
            "Auto-extracted {} memories from transcript:\n{}",
            saved.len(),
            saved.join("\n")
        ))
    }
}
