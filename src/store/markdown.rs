use std::path::Path;
use anyhow::Result;
use chrono::{NaiveDate, Utc};

use crate::types::{IdentityCard, JournalEntry, Memory};

/// Append a journal entry to today's file
pub fn write_journal_entry(store_path: &Path, entry: &JournalEntry) -> Result<()> {
    let date = entry.timestamp.format("%Y-%m-%d").to_string();
    let dir = store_path.join("journal");
    std::fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.md", date));

    let time = entry.timestamp.format("%H:%M").to_string();
    let gate = entry.gate.as_str();
    let line = format!(
        "\n## {} - {}\n[{}] {}\n",
        time, gate, gate, entry.content
    );

    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .create(true).append(true).open(&file)?;

    // Write header if new file
    if f.metadata()?.len() == 0 {
        write!(f, "# {}\n", date)?;
    }
    write!(f, "{}", line)?;
    Ok(())
}

/// Read all journal entries for a given date
pub fn read_journal(store_path: &Path, date: &NaiveDate) -> Result<String> {
    let file = store_path
        .join("journal")
        .join(format!("{}.md", date.format("%Y-%m-%d")));
    if file.exists() {
        Ok(std::fs::read_to_string(&file)?)
    } else {
        Ok(String::new())
    }
}

/// Write a long-term memory file with YAML frontmatter
pub fn write_long_term(store_path: &Path, memory: &Memory) -> Result<()> {
    let category = category_for_gate(&memory.gate);
    let slug = slugify(&memory.id);
    let dir = store_path.join("long-term").join(category);
    std::fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.md", slug));

    let frontmatter = serde_yaml::to_string(&memory)?;
    let content = format!("---\n{}---\n\n{}\n", frontmatter, memory.content);
    std::fs::write(&file, content)?;
    Ok(())
}

/// Read identity card
pub fn read_identity(store_path: &Path) -> Result<Option<IdentityCard>> {
    let file = store_path.join("identity.md");
    if !file.exists() {
        return Ok(None);
    }
    let raw = std::fs::read_to_string(&file)?;
    Ok(Some(IdentityCard {
        person: None,
        project: None,
        content: raw,
        last_updated: Utc::now(),
    }))
}

/// Write identity card
pub fn write_identity(store_path: &Path, card: &IdentityCard) -> Result<()> {
    let file = store_path.join("identity.md");
    std::fs::write(&file, &card.content)?;
    Ok(())
}

/// Search all markdown files for a query string (basic grep)
pub fn search_all(store_path: &Path, query: &str) -> Result<Vec<String>> {
    let mut results = Vec::new();
    let query_lower = query.to_lowercase();

    for entry in walkdir::WalkDir::new(store_path)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("md") {
            continue;
        }
        if let Ok(content) = std::fs::read_to_string(path) {
            if content.to_lowercase().contains(&query_lower) {
                results.push(content);
            }
        }
    }
    Ok(results)
}

fn category_for_gate(gate: &crate::types::Gate) -> &str {
    match gate {
        crate::types::Gate::Relational => "people",
        crate::types::Gate::Epistemic => "learnings",
        crate::types::Gate::Behavioral => "decisions",
        crate::types::Gate::Promissory => "commitments",
    }
}

fn slugify(s: &str) -> String {
    s.chars()
        .map(|c| if c.is_alphanumeric() || c == '-' { c } else { '_' })
        .collect()
}
