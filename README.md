# claude-memory-kit

Persistent memory for Claude. MCP server with hybrid search (dense + sparse vectors, RRF fusion), SQLite storage, and automatic sensitivity classification.

## install

```bash
uv tool install claude-memory-kit
```

Or with pip:

```bash
pip install claude-memory-kit
```

## setup

Add to your Claude Code MCP config (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "memory": {
      "command": "cmk"
    }
  }
}
```

That's it. Claude will automatically save and recall memories across sessions.

## how it works

3 tools exposed to Claude:

- **save**: store something worth remembering. gate, person, project, and sensitivity are auto-classified.
- **search**: hybrid search across memories (keyword + semantic + graph traversal).
- **forget**: remove a memory by ID with a reason.

Claude calls `save` proactively when it learns something worth keeping (preferences, corrections, commitments, facts about people). No manual intervention needed.

## features

- **Hybrid search**: dense vectors (fastembed) + sparse vectors (BM25) with Reciprocal Rank Fusion
- **Write gates**: behavioral, relational, epistemic, promissory, correction (auto-classified)
- **Memory decay**: configurable half-life per gate type, automatic archival
- **Graph traversal**: RELATED_TO, CONTRADICTS, FOLLOWS edges between memories
- **Sensitivity classification**: Opus-powered privacy detection (safe/sensitive/critical)
- **PII scanning**: regex-based detection for API keys, SSNs, credit cards, etc.
- **Identity card**: auto-generated summary of who Claude is working with
- **Journal consolidation**: automatic compression of old entries into digests

## dashboard

CMK includes a web dashboard for managing memories:

```bash
cmk serve --port 7749
```

Then build and run the dashboard (Next.js):

```bash
cd dashboard
pnpm install && pnpm dev
```

Dashboard features: timeline view, search, graph visualization, identity management, rules, API keys, and a privacy review page.

## cli

```bash
# save and search
cmk remember "user prefers dark mode" --gate behavioral
cmk recall "dark mode"

# maintenance
cmk scan
cmk classify
cmk classify --force
cmk reflect
cmk stats
cmk serve
```

| Command | Description |
|---|---|
| `cmk remember` | Store a memory with auto-classification |
| `cmk recall` | Search memories |
| `cmk scan` | PII scan across all memories |
| `cmk classify` | Opus sensitivity classification |
| `cmk classify --force` | Re-classify all memories |
| `cmk reflect` | Consolidate old entries + run decay |
| `cmk stats` | Storage and memory statistics |
| `cmk serve` | Start the API server |

## environment

```bash
# required for LLM features
ANTHROPIC_API_KEY=<your-api-key>

# optional: Qdrant Cloud
QDRANT_URL=<your-cluster-url>
QDRANT_API_KEY=<your-key>

# optional: custom storage path
MEMORY_STORE_PATH=~/.claude-memory
```

See `.env.example` for all options.

## license

MIT
