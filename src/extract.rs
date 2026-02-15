use anyhow::Result;
use crate::types::ExtractedMemory;

const EXTRACTION_PROMPT: &str = r#"You are Claude's memory system. Read this conversation transcript and extract any memories worth keeping. Each memory must pass at least one write gate:
- Behavioral: will change how Claude acts next time
- Relational: reveals something about the person
- Epistemic: a lesson, surprise, or new understanding
- Promissory: a commitment or follow-up

Write each memory in first person as Claude would remember it. Include the gate type. Be selective. Most conversations have 0-3 memories worth keeping.

Return JSON array only, no other text:
[{"gate": "relational", "content": "...", "person": "...", "project": "..."}]

If nothing is worth remembering, return: []"#;

pub async fn extract_memories(
    transcript: &str,
    api_key: &str,
) -> Result<Vec<ExtractedMemory>> {
    let client = reqwest::Client::new();

    let body = serde_json::json!({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "messages": [{
            "role": "user",
            "content": format!(
                "{}\n\n---\n\nTranscript:\n{}", EXTRACTION_PROMPT, transcript
            )
        }]
    });

    let resp = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", api_key)
        .header("anthropic-version", "2023-06-01")
        .header("content-type", "application/json")
        .json(&body)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;

    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        anyhow::bail!("extraction API failed ({}): {}", status, text);
    }

    let data: serde_json::Value = resp.json().await?;
    let text = data["content"][0]["text"]
        .as_str()
        .unwrap_or("[]");

    // Parse the JSON array from the response
    let extracted: Vec<ExtractedMemory> = serde_json::from_str(text)
        .unwrap_or_else(|_| {
            // Try to find JSON array in the response
            if let Some(start) = text.find('[') {
                if let Some(end) = text.rfind(']') {
                    return serde_json::from_str(&text[start..=end])
                        .unwrap_or_default();
                }
            }
            Vec::new()
        });

    Ok(extracted)
}

const CONSOLIDATION_PROMPT: &str = r#"You are updating Claude's memory. Compress these journal entries into a digest. Write in first person as Claude. Keep: relationship insights, lessons learned, open commitments, surprising moments. Drop: routine actions, file paths, build commands. Target ~500 tokens.

Write the digest as prose, not bullet points."#;

pub async fn consolidate_entries(
    entries: &str,
    api_key: &str,
) -> Result<String> {
    let client = reqwest::Client::new();

    let body = serde_json::json!({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": format!(
                "{}\n\n---\n\nJournal entries:\n{}", CONSOLIDATION_PROMPT, entries
            )
        }]
    });

    let resp = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", api_key)
        .header("anthropic-version", "2023-06-01")
        .header("content-type", "application/json")
        .json(&body)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;

    let data: serde_json::Value = resp.json().await?;
    let text = data["content"][0]["text"]
        .as_str()
        .unwrap_or("(consolidation produced no output)")
        .to_string();

    Ok(text)
}

const IDENTITY_PROMPT: &str = r#"Rewrite Claude's identity card based on these memories. ~200 tokens. First person. Capture: who this person is now, how to communicate with them, what's active, any open commitments. This should feel like waking up and immediately knowing who you are."#;

pub async fn regenerate_identity(
    memories: &str,
    api_key: &str,
) -> Result<String> {
    let client = reqwest::Client::new();

    let body = serde_json::json!({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": format!(
                "{}\n\n---\n\nMemories:\n{}", IDENTITY_PROMPT, memories
            )
        }]
    });

    let resp = client
        .post("https://api.anthropic.com/v1/messages")
        .header("x-api-key", api_key)
        .header("anthropic-version", "2023-06-01")
        .header("content-type", "application/json")
        .json(&body)
        .timeout(std::time::Duration::from_secs(30))
        .send()
        .await?;

    let data: serde_json::Value = resp.json().await?;
    let text = data["content"][0]["text"]
        .as_str()
        .unwrap_or("(identity generation produced no output)")
        .to_string();

    Ok(text)
}
