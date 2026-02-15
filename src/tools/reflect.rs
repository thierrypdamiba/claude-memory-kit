use anyhow::Result;
use crate::server::MemoryServer;
use crate::consolidation::{digest, journal};
use crate::extract;
use crate::store::markdown;
use crate::types::IdentityCard;

impl MemoryServer {
    pub async fn do_reflect(&self) -> Result<String> {
        let mut report = Vec::new();

        // 1. Consolidate old journals into weekly digests
        match digest::consolidate_journals(&self.store_path, &self.api_key).await {
            Ok(Some(msg)) => report.push(msg),
            Ok(None) => report.push("No journals old enough to consolidate.".into()),
            Err(e) => report.push(format!("Journal consolidation failed: {}", e)),
        }

        // 2. Regenerate identity card from recent memories
        let recent = journal::recent_journals(&self.store_path, 5)?;
        if !recent.is_empty() {
            match extract::regenerate_identity(&recent, &self.api_key).await {
                Ok(new_identity) => {
                    // Archive old identity
                    if let Ok(Some(old)) = markdown::read_identity(&self.store_path) {
                        let archive_dir = self.store_path.join("archive/identity");
                        std::fs::create_dir_all(&archive_dir)?;
                        let archive_file = archive_dir.join(format!(
                            "{}.md", chrono::Utc::now().format("%Y-%m-%d")
                        ));
                        std::fs::write(&archive_file, &old.content)?;
                    }

                    let card = IdentityCard {
                        person: None,
                        project: None,
                        content: new_identity.clone(),
                        last_updated: chrono::Utc::now(),
                    };
                    markdown::write_identity(&self.store_path, &card)?;
                    report.push("Identity card regenerated.".into());
                }
                Err(e) => report.push(format!("Identity regeneration failed: {}", e)),
            }
        }

        if report.is_empty() {
            Ok("Reflection complete. Nothing to consolidate.".into())
        } else {
            Ok(format!("Reflection complete:\n- {}", report.join("\n- ")))
        }
    }
}
