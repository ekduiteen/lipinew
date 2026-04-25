from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from db.connection import SessionLocal  # noqa: E402
from services.training_exporter import export_training_rows  # noqa: E402


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Export language-adaptive ASR training rows.")
    parser.add_argument("--country", required=True, help="Country code, e.g. NP")
    parser.add_argument("--language", help="Target language code, e.g. newari")
    parser.add_argument("--all-languages", action="store_true", help="Export all languages under country")
    parser.add_argument("--tier", default="gold", choices=["gold", "silver", "bronze", "rejected"])
    args = parser.parse_args()

    if not args.language and not args.all_languages:
        parser.error("Provide --language or --all-languages")

    async with SessionLocal() as db:
        result = await export_training_rows(
            db,
            country_code=args.country.upper(),
            target_language=None if args.all_languages else args.language,
            tier=args.tier,
        )
        await db.commit()
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())
