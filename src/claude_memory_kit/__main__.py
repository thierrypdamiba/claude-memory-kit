"""Entry point for python -m claude_memory_kit."""

import asyncio
from .server import run_server

asyncio.run(run_server())
