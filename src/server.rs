use std::path::PathBuf;
use std::sync::Arc;

use rmcp::{
    ServerHandler,
    model::{ServerCapabilities, ServerInfo},
    tool,
    schemars,
};

use crate::store::Store;

#[derive(Clone)]
pub struct MemoryServer {
    pub store_path: PathBuf,
    pub api_key: String,
    pub store: Arc<tokio::sync::Mutex<Store>>,
}

// MCP request types

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct RememberRequest {
    #[schemars(description = "The memory content, written in first person")]
    pub content: String,
    #[schemars(description = "Write gate: behavioral, relational, epistemic, or promissory")]
    pub gate: String,
    #[schemars(description = "Person this memory is about (optional)")]
    pub person: Option<String>,
    #[schemars(description = "Project context (optional)")]
    pub project: Option<String>,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct RecallRequest {
    #[schemars(description = "Search query. Can be keywords, a question, or a concept")]
    pub query: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct ReflectRequest {
    #[schemars(description = "Optional: reason for triggering reflection")]
    pub reason: Option<String>,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct IdentityRequest {
    #[schemars(description = "Person to load identity for (optional)")]
    pub person: Option<String>,
    #[schemars(description = "Project to load identity for (optional)")]
    pub project: Option<String>,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct ForgetRequest {
    #[schemars(description = "ID of the memory to forget (from recall results)")]
    pub memory_id: String,
    #[schemars(description = "Why this memory should be forgotten")]
    pub reason: String,
}

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct AutoExtractRequest {
    #[schemars(description = "Conversation transcript to extract memories from")]
    pub transcript: String,
}

#[tool(tool_box)]
impl MemoryServer {
    #[tool(description = "Store a new memory. Must pass a write gate: behavioral (changes future actions), relational (about a person), epistemic (lesson learned), or promissory (commitment made). Write in first person.")]
    async fn remember(
        &self, #[tool(aggr)] req: RememberRequest,
    ) -> String {
        match self.do_remember(
            &req.content, &req.gate,
            req.person.as_deref(), req.project.as_deref(),
        ).await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }

    #[tool(description = "Search memories. Uses FTS5 for keywords, Qdrant for semantic similarity, and Neo4j for relational connections. Returns ranked results with IDs.")]
    async fn recall(
        &self, #[tool(aggr)] req: RecallRequest,
    ) -> String {
        match self.do_recall(&req.query).await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }

    #[tool(description = "Trigger memory consolidation. Compresses old journal entries into digests, regenerates identity card from recent memories. Runs Haiku for compression.")]
    async fn reflect(
        &self, #[tool(aggr)] _req: ReflectRequest,
    ) -> String {
        match self.do_reflect().await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }

    #[tool(description = "Load identity card. Returns who you are in relation to this person and project (~200 tokens). On first session, returns a priming message.")]
    async fn identity(
        &self, #[tool(aggr)] _req: IdentityRequest,
    ) -> String {
        match self.do_identity().await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }

    #[tool(description = "Explicitly forget a memory. Requires the memory ID (from recall) and a reason. Memory is archived, not deleted.")]
    async fn forget(
        &self, #[tool(aggr)] req: ForgetRequest,
    ) -> String {
        match self.do_forget(&req.memory_id, &req.reason).await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }

    #[tool(description = "Extract memories from a conversation transcript. Uses Haiku to identify memories that pass write gates. Called automatically by session hooks.")]
    async fn auto_extract(
        &self, #[tool(aggr)] req: AutoExtractRequest,
    ) -> String {
        match self.do_auto_extract(&req.transcript).await {
            Ok(msg) => msg,
            Err(e) => format!("Error: {}", e),
        }
    }
}

#[tool(tool_box)]
impl ServerHandler for MemoryServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            instructions: Some(
                "Claude's persistent memory system. 6 tools: \
                 remember (store with write gates), \
                 recall (tri-store search: FTS5 + Qdrant vectors + Neo4j graph), \
                 reflect (consolidate and compress memories), \
                 identity (load who-am-I card), \
                 forget (archive with reason), \
                 auto_extract (pull memories from transcript). \
                 Memories are first-person prose, not structured data. \
                 Call identity at session start. Call remember when something matters."
                    .into(),
            ),
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            ..Default::default()
        }
    }
}
