"""MCP entrypoint — sets project root on sys.path (for Cursor MCP without cwd)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flights.mcp_server import main

if __name__ == "__main__":
    main()
