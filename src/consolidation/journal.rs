use std::path::Path;
use anyhow::Result;
use chrono::{NaiveDate, Utc, Duration};

/// List journal dates that exist in the store
pub fn list_journal_dates(store_path: &Path) -> Result<Vec<NaiveDate>> {
    let journal_dir = store_path.join("journal");
    if !journal_dir.exists() {
        return Ok(Vec::new());
    }

    let mut dates = Vec::new();
    for entry in std::fs::read_dir(&journal_dir)? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().to_string();
        if let Some(date_str) = name.strip_suffix(".md") {
            if let Ok(date) = NaiveDate::parse_from_str(date_str, "%Y-%m-%d") {
                dates.push(date);
            }
        }
    }
    dates.sort();
    Ok(dates)
}

/// Get journal dates older than N days that haven't been digested
pub fn stale_journals(store_path: &Path, max_age_days: i64) -> Result<Vec<NaiveDate>> {
    let cutoff = Utc::now().date_naive() - Duration::days(max_age_days);
    let dates = list_journal_dates(store_path)?;
    Ok(dates.into_iter().filter(|d| *d < cutoff).collect())
}

/// Read the last N journal files and concatenate their contents
pub fn recent_journals(store_path: &Path, count: usize) -> Result<String> {
    let dates = list_journal_dates(store_path)?;
    let recent: Vec<_> = dates.iter().rev().take(count).collect();

    let mut combined = String::new();
    for date in recent.iter().rev() {
        let content = crate::store::markdown::read_journal(store_path, date)?;
        if !content.is_empty() {
            combined.push_str(&content);
            combined.push('\n');
        }
    }
    Ok(combined)
}

/// Move a journal file to the archive
pub fn archive_journal(store_path: &Path, date: &NaiveDate) -> Result<()> {
    let src = store_path
        .join("journal")
        .join(format!("{}.md", date.format("%Y-%m-%d")));
    let dst_dir = store_path.join("archive").join("journal");
    std::fs::create_dir_all(&dst_dir)?;
    let dst = dst_dir.join(format!("{}.md", date.format("%Y-%m-%d")));

    if src.exists() {
        std::fs::rename(&src, &dst)?;
    }
    Ok(())
}
