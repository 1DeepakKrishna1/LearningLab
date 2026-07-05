"""Seed the platform with the sample workflows in ../samples.

Usage (from platform/backend):
    python -m scripts.seed_samples
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.container import Container
from app.domain.workflow import Workflow

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"


async def main() -> None:
    container = Container()
    await container.startup()
    for path in sorted(SAMPLES_DIR.glob("*.json")):
        spec = json.loads(path.read_text("utf-8"))
        wf = Workflow(**spec)
        await container.workflow_service.save(wf)
        validation = container.workflow_service.validate_obj(wf)
        print(f"Seeded '{wf.name}' ({len(wf.nodes)} nodes) — valid={validation['valid']}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
