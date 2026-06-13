#!/usr/bin/env python3
"""Quick verification script for the LM Studio API client."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

from lmstudio.api import LMStudioClient  # noqa: E402


async def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2137

    async with aiohttp.ClientSession() as session:
        client = LMStudioClient(session, host, port)
        models = await client.async_get_models()

    print(f"Connected to http://{host}:{port}")
    print(f"Found {len(models)} model(s):\n")
    for model in models:
        loaded = model.get("loaded_instances") or []
        status = "loaded" if loaded else "available"
        print(f"- [{status}] {model.get('display_name')} ({model.get('key')})")
        print(f"    type={model.get('type')} publisher={model.get('publisher')}")


if __name__ == "__main__":
    asyncio.run(main())
