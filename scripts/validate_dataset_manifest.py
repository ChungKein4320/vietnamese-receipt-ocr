from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.dataset_manifest import (  # noqa: E402
    ManifestValidationError,
    load_dataset_manifest,
    summarize_splits,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate development/held-out dataset membership."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "dataset_manifest.csv",
        help="Path to the private dataset manifest.",
    )
    parser.add_argument(
        "--check-files",
        action="store_true",
        help="Require every image and ground-truth path to exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        records = load_dataset_manifest(
            args.manifest,
            project_root=PROJECT_ROOT,
            check_files=args.check_files,
        )
    except ManifestValidationError as error:
        print(f"Manifest validation failed: {error}", file=sys.stderr)
        return 1

    split_counts = summarize_splits(records)
    print(f"Manifest valid: {args.manifest}")
    print(f"Total receipts: {len(records)}")

    for split, count in split_counts.items():
        print(f"{split}: {count}")

    if split_counts["held_out"] == 0:
        print("Held-out results are not available yet.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
