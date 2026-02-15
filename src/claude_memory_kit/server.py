"""MCP server entry point. 7 tools: remember, recall, reflect, identity, forget, auto_extract, prime."""

import asyncio
import logging

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

log = logging.getLogger("cmk")

TOOL_DEFS = [
    Tool(
        name="remember",
        description=(
            "Store a new memory. Must pass a write gate: "
            "behavioral (changes future actions), "
            "relational (about a person), "
            "epistemic (lesson learned), "
            "promissory (commitment made), "
            "correction (updates a previous belief). "
            "Write in first person."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The memory content, written in first person",
                },
                "gate": {
                    "type": "string",
                    "description": "Write gate: behavioral, relational, epistemic, promissory, or correction",
                },
                "person": {
                    "type": "string",
                    "description": "Person this memory is about (optional)",
                },
                "project": {
                    "type": "string",
                    "description": "Project context (optional)",
                },
            },
            "required": ["content", "gate"],
        },
    ),
    Tool(
        name="recall",
        description=(
            "Search memories. Parallel fan-out: "
            "FTS + vector similarity + graph traversal. "
            "Returns ranked results with IDs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query: keywords, question, or concept",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="reflect",
        description=(
            "Trigger memory consolidation. "
            "Compresses old journal entries into digests, "
            "regenerates identity card from recent memories."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="identity",
        description=(
            "Load identity card. Returns who you are "
            "in relation to this person and project (~200 tokens). "
            "On first session, starts an onboarding conversation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "onboard_response": {
                    "type": "string",
                    "description": "Response to onboarding question (only during first setup)",
                },
            },
        },
    ),
    Tool(
        name="forget",
        description=(
            "Forget a memory. Requires the memory ID "
            "(from recall results) and a reason. "
            "Memory is archived, not deleted."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "ID of the memory to forget",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this memory should be forgotten",
                },
            },
            "required": ["memory_id", "reason"],
        },
    ),
    Tool(
        name="auto_extract",
        description=(
            "Extract memories from a conversation transcript. "
            "Uses Opus to identify memories that pass write gates. "
            "Called automatically by session hooks."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "Conversation transcript to extract memories from",
                },
            },
            "required": ["transcript"],
        },
    ),
    Tool(
        name="prime",
        description=(
            "Proactive recall. Surface relevant memories "
            "from the user's latest message. "
            "Fast path: vector search only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The user's latest message to find context for",
                },
            },
            "required": ["message"],
        },
    ),
]


SERVER_INSTRUCTIONS = (
    "Claude Memory Kit (CMK). You have persistent memory. "
    "7 tools: remember (store with write gates), "
    "recall (tri-store search: FTS + vectors + graph), "
    "reflect (consolidate and compress memories), "
    "identity (load who-am-I card), "
    "forget (archive with reason), "
    "auto_extract (pull memories from transcript), "
    "prime (proactive recall from latest message). "
    "Memories are first-person prose, not structured data. "
    "At session start, call identity to load who you are. "
    "When something matters, call remember to keep it. "
    "You will forget everything otherwise."
)


def create_server() -> Server:
    server = Server("claude-memory-kit", instructions=SERVER_INSTRUCTIONS)
    store_path = get_store_path()
    store = Store(store_path)
    store.db.migrate()
    store.vectors.ensure_collection()

    @server.list_tools()
    async def list_tools():
        return TOOL_DEFS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            result = await _dispatch(store, name, arguments)
        except Exception as e:
            log.error("tool %s failed: %s", name, e)
            result = f"Error: {e}"
        return [TextContent(type="text", text=result)]

    return server


async def _dispatch(store: Store, name: str, args: dict) -> str:
    uid = get_user_id()
    if name == "remember":
        return await do_remember(
            store, args["content"], args["gate"],
            args.get("person"), args.get("project"),
            user_id=uid,
        )
    if name == "recall":
        return await do_recall(store, args["query"], user_id=uid)
    if name == "reflect":
        return await do_reflect(store, user_id=uid)
    if name == "identity":
        return await do_identity(
            store, args.get("onboard_response"), user_id=uid
        )
    if name == "forget":
        return await do_forget(
            store, args["memory_id"], args["reason"], user_id=uid
        )
    if name == "auto_extract":
        return await do_auto_extract(
            store, args["transcript"], user_id=uid
        )
    if name == "prime":
        return await do_prime(store, args["message"], user_id=uid)
    return f"Unknown tool: {name}"


async def run_server() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        log.info("starting claude-memory-kit MCP server (stdio)")
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options(),
        )
