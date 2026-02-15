"""CLI entry point for Claude Memory Kit (CMK)."""

import asyncio
import sys

import click

from .cli_auth import get_user_id
from .config import get_store_path
from .store import Store


def _get_store() -> Store:
    store = Store(get_store_path())
    store.db.migrate()
    store.vectors.ensure_collection()
    return store


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Claude Memory Kit. Persistent memory for Claude."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(mcp)


@main.command()
@click.argument("content")
@click.option("--gate", required=True, help="Write gate: behavioral, relational, epistemic, promissory, correction")
@click.option("--person", default=None, help="Person this memory is about")
@click.option("--project", default=None, help="Project context")
def remember(content, gate, person, project):
    """Store a new memory."""
    from .tools.remember import do_remember
    store = _get_store()
    result = asyncio.run(
        do_remember(store, content, gate, person, project, user_id=get_user_id())
    )
    click.echo(result)


@main.command()
@click.argument("query")
def recall(query):
    """Search memories."""
    from .tools.recall import do_recall
    store = _get_store()
    result = asyncio.run(do_recall(store, query, user_id=get_user_id()))
    click.echo(result)


@main.command()
def reflect():
    """Trigger memory consolidation."""
    from .tools.reflect import do_reflect
    store = _get_store()
    result = asyncio.run(do_reflect(store, user_id=get_user_id()))
    click.echo(result)


@main.command()
def identity():
    """Show identity card."""
    from .tools.identity import do_identity
    store = _get_store()
    result = asyncio.run(do_identity(store, user_id=get_user_id()))
    click.echo(result)


@main.command()
@click.argument("memory_id")
@click.option("--reason", required=True, help="Why to forget this memory")
def forget(memory_id, reason):
    """Forget a memory (archive with reason)."""
    from .tools.forget import do_forget
    store = _get_store()
    result = asyncio.run(
        do_forget(store, memory_id, reason, user_id=get_user_id())
    )
    click.echo(result)


@main.command()
def extract():
    """Extract memories from stdin transcript."""
    from .tools.auto_extract import do_auto_extract
    transcript = sys.stdin.read()
    if not transcript.strip():
        click.echo("No transcript provided on stdin.")
        return
    store = _get_store()
    result = asyncio.run(
        do_auto_extract(store, transcript, user_id=get_user_id())
    )
    click.echo(result)


@main.command()
@click.argument("message")
def prime(message):
    """Proactive recall from a message."""
    from .tools.prime import do_prime
    store = _get_store()
    result = asyncio.run(do_prime(store, message, user_id=get_user_id()))
    click.echo(result)


@main.command()
@click.option("--port", default=7749, help="API server port")
def serve(port):
    """Start API server for dashboard."""
    import uvicorn
    uvicorn.run(
        "claude_memory_kit.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


@main.command()
def mcp():
    """Start MCP server (stdio transport)."""
    from .server import run_server
    asyncio.run(run_server())


@main.command()
def stats():
    """Show memory statistics."""
    store = _get_store()
    total = store.db.count_memories(user_id=get_user_id())
    by_gate = store.db.count_by_gate(user_id=get_user_id())
    ident = store.db.get_identity(user_id=get_user_id())
    click.echo(f"Total memories: {total}")
    for gate, count in sorted(by_gate.items()):
        click.echo(f"  {gate}: {count}")
    if ident:
        click.echo(f"\nIdentity: {ident.person or 'unknown'}")
    else:
        click.echo("\nNo identity card yet.")


@main.command(name="init")
@click.argument("api_key")
def init_cmd(api_key):
    """Set up CMK with your API key from cmk.dev."""
    from .cli_auth import do_init
    do_init(api_key)


@main.command()
def claim():
    """Migrate local memories to your cloud account."""
    uid = get_user_id()
    if uid == "local":
        click.echo("Not logged in. Run 'cmk login' first.")
        return

    store = _get_store()
    local_counts = store.count_user_data("local")
    total = local_counts.get("total", 0)

    if total == 0:
        click.echo("No local data to claim.")
        return

    click.echo(f"Found {total} local items to migrate:")
    for table in ("memories", "journal", "edges", "archive"):
        count = local_counts.get(table, 0)
        if count > 0:
            click.echo(f"  {table}: {count}")

    if not click.confirm("Migrate all local data to your cloud account?"):
        click.echo("Cancelled.")
        return

    result = store.migrate_user_data("local", uid)
    click.echo("\nMigrated:")
    for key, count in result.items():
        if count > 0:
            click.echo(f"  {key}: {count}")
    click.echo("Done. Local data now belongs to your cloud account.")


@main.command(name="export")
def export_data():
    """Export cloud memories back to local storage."""
    uid = get_user_id()
    if uid == "local":
        click.echo("Not logged in. Nothing to export.")
        return

    store = _get_store()
    cloud_counts = store.count_user_data(uid)
    total = cloud_counts.get("total", 0)

    if total == 0:
        click.echo("No cloud data to export.")
        return

    click.echo(f"Found {total} cloud items to export to local:")
    for table in ("memories", "journal", "edges", "archive"):
        count = cloud_counts.get(table, 0)
        if count > 0:
            click.echo(f"  {table}: {count}")

    if not click.confirm("Copy all cloud data to local storage?"):
        click.echo("Cancelled.")
        return

    result = store.migrate_user_data(uid, "local")
    click.echo("\nExported:")
    for key, count in result.items():
        if count > 0:
            click.echo(f"  {key}: {count}")
    click.echo("Done. Cloud data copied to local mode.")


@main.command()
def login():
    """Sign in to CMK cloud. Opens browser for authentication."""
    from .cli_auth import do_login
    do_login()


@main.command()
def logout():
    """Sign out of CMK cloud. Removes stored credentials."""
    from .cli_auth import do_logout
    do_logout()


@main.command()
def whoami():
    """Show current authentication status."""
    from .cli_auth import do_whoami
    do_whoami()
