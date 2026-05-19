"""Phase 2 — polling loop (stub, implement after Phase 1 reveals the API)."""
import asyncio

from db.schema import init_db


async def main() -> None:
    _conn = init_db()
    print("Phase 2 not yet implemented. Run discover.py first.")


asyncio.run(main())
