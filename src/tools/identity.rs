use anyhow::Result;
use crate::server::MemoryServer;
use crate::store::markdown;
use crate::consolidation::journal;

const COLD_START_MESSAGE: &str = "\
First session. No identity card yet.

Pay attention to: how this person communicates, what they care about, \
whether they treat you as a tool or a collaborator. \
Write your first memory before the session ends.

Use `remember` with gate=relational to save what you notice about them.";

impl MemoryServer {
    pub async fn do_identity(&self) -> Result<String> {
        // Try to load existing identity card
        match markdown::read_identity(&self.store_path)? {
            Some(card) => {
                let mut output = card.content;

                // Append recent context from last 2 journal entries
                let recent = journal::recent_journals(&self.store_path, 2)?;
                if !recent.is_empty() {
                    output.push_str("\n\n---\nRecent context:\n");
                    // Truncate to ~500 tokens worth
                    let preview: String = recent.chars().take(2000).collect();
                    output.push_str(&preview);
                }

                Ok(output)
            }
            None => Ok(COLD_START_MESSAGE.to_string()),
        }
    }
}
