"""MCP server entry point. Model-friendly design: 3 tools, auto-context, auto-maintenance."""

import asyncio
import logging
import re

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .cli_auth import get_user_id
from .config import get_store_path
from .store import Store
from .tools import (
    do_remember, do_recall, do_reflect,
    do_identity, do_forget, do_auto_extract, do_prime,
)
from .tools.checkpoint import do_checkpoint, CHECKPOINT_GUIDANCE, CHECKPOINT_EVERY

log = logging.getLogger("cmk")

# Track saves for auto-reflect and auto-checkpoint
_save_count = 0
_checkpoint_count = 0
_REFLECT_EVERY = 15


def _auto_gate(text: str) -> str:
    """Classify gate from content using keyword heuristics.

    No API call needed. Good enough for 80% of cases.
    The gate is internal architecture, not user-facing.
    """
    lower = text.lower()

    # Promissory: commitments, promises, follow-ups
    if any(kw in lower for kw in [
        "i will", "i'll", "i promised", "i need to",
        "follow up", "follow-up", "todo", "to do",
        "i should", "committed to", "agreed to",
        "deadline", "by tomorrow", "by monday",
        "remind me", "don't forget",
    ]):
        return "promissory"

    # Correction: updates or contradicts previous knowledge
    if any(kw in lower for kw in [
        "actually", "correction", "i was wrong",
        "turns out", "not true", "no longer",
        "changed my mind", "updated", "contrary to",
        "instead of", "rather than", "opposite",
    ]):
        return "correction"

    # Behavioral: changes future actions, preferences, patterns
    if any(kw in lower for kw in [
        "from now on", "always", "never",
        "prefer", "preference", "likes to",
        "wants me to", "style is", "approach is",
        "workflow", "when i", "habit",
        "don't like", "annoyed by",
    ]):
        return "behavioral"

    # Relational: about a person, their traits, relationship dynamics
    person_patterns = [
        r"\b(he|she|they)\b.*(is|are|likes|prefers|hates|works|said)",
        r"\b\w+\b\s+(is a|works at|lives in|prefers|likes|said)",
    ]
    for pat in person_patterns:
        if re.search(pat, lower):
            return "relational"

    if any(kw in lower for kw in [
        "their name", "works at", "relationship",
        "family", "partner", "friend", "colleague",
        "boss", "manager", "team lead",
    ]):
        return "relational"

    # Default: epistemic (learning, facts, knowledge)
    return "epistemic"


def _extract_person_project(text: str) -> tuple[str | None, str | None]:
    """Try to extract person and project from content. Simple heuristics."""
    person = None
    project = None

    # Person: look for names (capitalized words after relational keywords)
    name_match = re.search(
        r"\b(?:about|for|with|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        text,
    )
    if name_match:
        candidate = name_match.group(1)
        # Skip common non-name words
        if candidate.lower() not in {
            "the", "this", "that", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday",
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        }:
            person = candidate

    # Project: look for quoted strings or "project X" patterns
    project_match = re.search(
        r'(?:project|repo|app|codebase|working on)\s+["\']?(\S+)["\']?',
        text,
        re.IGNORECASE,
    )
    if project_match:
        project = project_match.group(1).strip("\"'.,;")

    return person, project


def _build_instructions(store: Store, user_id: str) -> str:
    """Build dynamic server instructions with identity card and recent context."""
    parts = [
        "You have persistent memory via Claude Memory Kit (CMK).",
        "You WILL forget everything between sessions unless you save it.",
        "",
        "4 tools: save, search, forget, checkpoint.",
        "",
        "PROACTIVE SAVING (do this automatically, user should not have to ask):",
        "- User states a preference or opinion: save it.",
        "- User corrects you or says you're wrong: save the correction.",
        "- User mentions a person, their role, or relationship: save it.",
        "- User makes a commitment or asks you to follow up: save it.",
        "- You learn something surprising or non-obvious: save it.",
        "- A decision is made about architecture, approach, or tooling: save it.",
        "- The user's name, project, or working style comes up: save it.",
        "",
        "Do NOT save: routine commands, file paths, build output, small talk.",
        "Do NOT ask permission to save. Just save. The user expects it.",
        "",
        "When context might exist from past sessions, call search first.",
        "Everything else (classification, consolidation, identity) is automatic.",
        "",
        "SESSION CONTINUITY:",
        "- Checkpoints are auto-saved every 8 memory saves.",
        "- You can also call checkpoint manually when wrapping up complex work.",
        "- Your last checkpoint is loaded above at session start.",
    ]

    # Load identity card if it exists
    identity = store.db.get_identity(user_id=user_id)
    if identity:
        parts.append("")
        parts.append("--- Who I am ---")
        parts.append(identity.content)

    # Load latest checkpoint (where we left off last session)
    checkpoint = store.db.latest_checkpoint(user_id=user_id)
    if checkpoint:
        parts.append("")
        parts.append("--- Last session checkpoint ---")
        parts.append(checkpoint["content"])

    # Load recent context (last few journal entries, excluding checkpoints)
    recent = store.db.recent_journal(days=2, user_id=user_id)
    if recent:
        non_checkpoint = [e for e in recent if e.get("gate") != "checkpoint"]
        if non_checkpoint:
            parts.append("")
            parts.append("--- Recent context ---")
            for e in non_checkpoint[:8]:
                parts.append(f"[{e['gate']}] {e['content']}")

    return "\n".join(parts)


# Tool definitions: 3 tools, minimal required params
TOOL_DEFS = [
    Tool(
        name="save",
        description=(
            "Save something to memory. Call this PROACTIVELY whenever "
            "you learn something worth keeping: preferences, facts about people, "
            "commitments, corrections, decisions, surprises. "
            "Classification and sensitivity are auto-detected. "
            "Don't ask permission. Just save."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "What to remember. Write naturally.",
                },
                "person": {
                    "type": "string",
                    "description": "Person this is about (auto-detected if omitted)",
                },
                "project": {
                    "type": "string",
                    "description": "Project context (auto-detected if omitted)",
                },
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="search",
        description=(
            "Search memories. Hybrid search: keywords + semantic + graph. "
            "Use natural language or keywords."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="forget",
        description=(
            "Remove a memory. Requires the memory ID "
            "(from search results) and a reason why."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Memory ID to forget",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this should be forgotten",
                },
            },
            "required": ["id", "reason"],
        },
    ),
    Tool(
        name="checkpoint",
        description=(
            "Save a session checkpoint. Called automatically every 8 saves, "
            "or call manually when finishing complex work. "
            + CHECKPOINT_GUIDANCE
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": (
                        "Structured session summary. " + CHECKPOINT_GUIDANCE
                    ),
                },
            },
            "required": ["summary"],
        },
    ),
]

# Keep legacy tool names as aliases for backwards compatibility
LEGACY_ALIASES = {
    "remember": "save",
    "recall": "search",
    "prime": "search",
}


def create_server() -> Server:
    store_path = get_store_path()
    store = Store(store_path)
    store.db.migrate()
    store.vectors.ensure_collection()
    user_id = get_user_id()

    instructions = _build_instructions(store, user_id)
    server = Server("claude-memory-kit", instructions=instructions)

    @server.list_tools()
    async def list_tools():
        return TOOL_DEFS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # Resolve legacy aliases
        resolved = LEGACY_ALIASES.get(name, name)
        try:
            result = await _dispatch(store, resolved, arguments, user_id)
        except Exception as e:
            log.error("tool %s failed: %s", name, e)
            result = f"Error: {e}"
        return [TextContent(type="text", text=result)]

    return server


async def _dispatch(store: Store, name: str, args: dict, user_id: str) -> str:
    global _save_count, _checkpoint_count

    if name == "save":
        text = args["text"]
        gate = _auto_gate(text)
        person = args.get("person")
        project = args.get("project")

        # Auto-detect person/project if not provided
        if not person or not project:
            auto_person, auto_project = _extract_person_project(text)
            if not person:
                person = auto_person
            if not project:
                project = auto_project

        result = await do_remember(
            store, text, gate, person, project, user_id=user_id,
        )

        _save_count += 1
        _checkpoint_count += 1

        # Auto-reflect after N saves
        if _save_count >= _REFLECT_EVERY:
            _save_count = 0
            try:
                reflect_result = await do_reflect(store, user_id=user_id)
                log.info("auto-reflect: %s", reflect_result)
            except Exception as e:
                log.warning("auto-reflect failed: %s", e)

        # Auto-checkpoint: prompt to save session state
        if _checkpoint_count >= CHECKPOINT_EVERY:
            _checkpoint_count = 0
            result += (
                "\n\n[auto-checkpoint] You've saved 8 memories this session. "
                "Call the checkpoint tool with a structured summary of: "
                "current task, decisions made, what didn't work, and next steps."
            )

        return result

    if name == "checkpoint":
        return await do_checkpoint(store, args["summary"], user_id=user_id)

    if name == "search":
        return await do_recall(store, args["query"], user_id=user_id)

    if name == "forget":
        return await do_forget(
            store, args["id"], args["reason"], user_id=user_id,
        )

    # Legacy tool names still work through the API/CLI
    if name == "identity":
        return await do_identity(
            store, args.get("onboard_response"), user_id=user_id,
        )
    if name == "reflect":
        return await do_reflect(store, user_id=user_id)
    if name == "auto_extract":
        return await do_auto_extract(
            store, args["transcript"], user_id=user_id,
        )

    return f"Unknown tool: {name}"


async def run_server() -> None:  # pragma: no cover
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        log.info("starting claude-memory-kit MCP server (stdio)")
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options(),
        )
