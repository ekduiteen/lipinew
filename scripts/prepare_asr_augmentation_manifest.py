from __future__ import annotations

import argparse
import json
from pathlib import Path


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ASR augmentation manifest from gold/silver exports.")
    parser.add_argument("--export-dir", required=True, help="Directory containing asr_gold.jsonl/asr_silver.jsonl")
    parser.add_argument("--include-silver", action="store_true", help="Include eligible silver rows")
    parser.add_argument("--output", default="augmentation_manifest.jsonl")
    args = parser.parse_args()

    export_dir = Path(args.export_dir)
    sources = [export_dir / "asr_gold.jsonl"]
    if args.include_silver:
        sources.append(export_dir / "asr_silver.jsonl")

    output_path = export_dir / args.output
    written = 0
    with output_path.open("w", encoding="utf-8") as out:
        for source in sources:
            tier = "gold" if "gold" in source.name else "silver"
            for row in _iter_jsonl(source) or []:
                if row.get("training_tier") not in {"gold", "silver"}:
                    continue
                if not row.get("consent_training_use") or not row.get("audio_path"):
                    continue
                transcript = row.get("normalized_transcript") or row.get("teacher_corrected_transcript")
                if not transcript:
                    continue
                manifest_row = {
                    "audio_path": row["audio_path"],
                    "transcript": transcript,
                    "target_language": row.get("target_language"),
                    "training_tier": tier,
                    "augmentation_plan": {
                        "speed_perturbation": [0.95, 1.0, 1.05],
                        "volume_randomization": True,
                        "light_noise_injection": True,
                        "pitch_shift": [-1, 0, 1],
                        "specaugment": True,
                    },
                }
                out.write(json.dumps(manifest_row, ensure_ascii=False) + "\n")
                written += 1
    print({"output": str(output_path), "rows": written})


if __name__ == "__main__":
    main()
