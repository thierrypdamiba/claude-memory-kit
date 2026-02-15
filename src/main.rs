mod server;
mod types;
mod store;
mod tools;
mod extract;
mod consolidation;

use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Result;
use rmcp::ServiceExt;
use tracing::info;

#[tokio::main]
async fn main() -> Result<()> {
    dotenv::dotenv().ok();
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("claude_memory=info".parse()?)
        )
        .with_writer(std::io::stderr)
        .init();

    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--extract") {
        return run_extract().await;
    }

    run_mcp_server().await
}

async fn run_mcp_server() -> Result<()> {
    let store_path = resolve_store_path();
    let api_key = std::env::var("ANTHROPIC_API_KEY").unwrap_or_default();
    let store = store::Store::init(&store_path).await?;

    let server = server::MemoryServer {
        store_path,
        api_key,
        store: Arc::new(tokio::sync::Mutex::new(store)),
    };

    let transport = rmcp::transport::io::stdio();
    info!("starting claude-memory MCP server (stdio)");

    let service = server.serve(transport).await
        .map_err(|e| anyhow::anyhow!("MCP server failed: {}", e))?;

    let _ = service.waiting().await;
    Ok(())
}

async fn run_extract() -> Result<()> {
    let mut transcript = String::new();
    std::io::Read::read_to_string(&mut std::io::stdin(), &mut transcript)?;
    if transcript.trim().is_empty() {
        return Ok(());
    }

    let store_path = resolve_store_path();
    let api_key = std::env::var("ANTHROPIC_API_KEY").unwrap_or_default();
    if api_key.is_empty() {
        eprintln!("ANTHROPIC_API_KEY not set, skipping extraction");
        return Ok(());
    }

    let store = store::Store::init(&store_path).await?;
    let server = server::MemoryServer {
        store_path,
        api_key,
        store: Arc::new(tokio::sync::Mutex::new(store)),
    };

    match server.do_auto_extract(&transcript).await {
        Ok(msg) => eprintln!("{}", msg),
        Err(e) => eprintln!("extraction failed: {}", e),
    }
    Ok(())
}

fn resolve_store_path() -> PathBuf {
    PathBuf::from(
        std::env::var("MEMORY_STORE_PATH").unwrap_or_else(|_| {
            let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
            format!("{}/.claude-memory/store", home)
        })
    )
}
