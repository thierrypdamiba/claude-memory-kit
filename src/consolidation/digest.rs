use std::path::Path;
use anyhow::Result;
use chrono::NaiveDate;

use crate::consolidation::journal;
use crate::extract;

/// Consolidate old journal entries into a weekly digest
pub async fn consolidate_journals(
    store_path: &Path,
    api_key: &str,
) -> Result<Option<String>> {
    let stale = journal::stale_journals(store_path, 14)?;
    if stale.is_empty() {
        return Ok(None);
    }

    // Group stale journals by ISO week
    let mut week_groups: std::collections::BTreeMap<String, Vec<NaiveDate>> =
        std::collections::BTreeMap::new();
    for date in &stale {
        let week = date.format("%G-W%V").to_string();
        week_groups.entry(week).or_default().push(*date);
    }

    let mut digests_written = Vec::new();

    for (week_key, dates) in &week_groups {
        // Read all journal entries for this week
        let mut combined = String::new();
        for date in dates {
            let content = crate::store::markdown::read_journal(store_path, date)?;
            combined.push_str(&content);
            combined.push('\n');
        }

        if combined.trim().is_empty() {
            continue;
        }

        // Call Haiku to consolidate
        let digest = extract::consolidate_entries(&combined, api_key).await?;

        // Write digest file
        let digest_dir = store_path.join("digests");
        std::fs::create_dir_all(&digest_dir)?;
        let file = digest_dir.join(format!("{}.md", week_key));
        std::fs::write(&file, format!("# Week {}\n\n{}\n", week_key, digest))?;

        // Archive the original journals
        for date in dates {
            journal::archive_journal(store_path, date)?;
        }

        digests_written.push(week_key.clone());
    }

    if digests_written.is_empty() {
        Ok(None)
    } else {
        Ok(Some(format!(
            "Consolidated {} weeks: {}",
            digests_written.len(),
            digests_written.join(", ")
        )))
    }
}
