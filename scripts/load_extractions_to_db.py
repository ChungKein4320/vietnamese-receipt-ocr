from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EXTRACTED_RESULT_DIR
from receipt_ocr.database import count_receipts, save_extraction_to_db


def collect_extraction_files() -> list[Path]:
    return sorted(EXTRACTED_RESULT_DIR.glob("*_extracted.json"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_one_file(path: Path) -> None:
    result = load_json(path)
    receipt_db_id = save_extraction_to_db(result, replace=True)
    print(f"Saved {result['receipt_id']} to database with id={receipt_db_id}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load extracted receipt JSON files into SQLite."
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to one extracted JSON file.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Load all extracted JSON files from data/extracted_results/.",
    )

    args = parser.parse_args()

    if args.file is None and not args.all:
        raise ValueError("Please provide --file or use --all.")

    if args.file is not None and args.all:
        raise ValueError("Use either --file or --all, not both.")

    if args.file is not None:
        load_one_file(Path(args.file))
    else:
        files = collect_extraction_files()

        if not files:
            raise FileNotFoundError(f"No extracted JSON files found in {EXTRACTED_RESULT_DIR}")

        for path in files:
            load_one_file(path)

    print(f"\nTotal receipts in database: {count_receipts()}")


if __name__ == "__main__":
    main()