from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EXTRACTED_RESULT_DIR
from receipt_ocr.ocr_text_corrector import correct_extraction_payload


CORRECTED_RESULT_DIR = PROJECT_ROOT / "data" / "corrected_results"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def correct_one_file(input_path: Path) -> Path:
    payload = load_json(input_path)
    corrected_payload = correct_extraction_payload(payload)

    receipt_id = corrected_payload.get("receipt_id") or input_path.stem.replace("_extracted", "")
    output_path = CORRECTED_RESULT_DIR / f"{receipt_id}_corrected.json"

    save_json(corrected_payload, output_path)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply OCR text correction to extracted receipt JSON files."
    )

    parser.add_argument(
        "--extracted-json",
        type=str,
        default=None,
        help="Path to one extracted JSON file.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Apply correction to all files in data/extracted_results.",
    )

    args = parser.parse_args()

    if not args.all and args.extracted_json is None:
        raise ValueError("Use --all or --extracted-json.")

    if args.all and args.extracted_json is not None:
        raise ValueError("Use either --all or --extracted-json, not both.")

    if args.all:
        input_paths = sorted(EXTRACTED_RESULT_DIR.glob("receipt_*_extracted.json"))
    else:
        input_paths = [Path(args.extracted_json)]

    if not input_paths:
        raise FileNotFoundError(f"No extracted JSON files found in {EXTRACTED_RESULT_DIR}")

    for input_path in input_paths:
        output_path = correct_one_file(input_path)
        print(f"Corrected: {input_path}")
        print(f"Saved    : {output_path}")
        print("-" * 60)


if __name__ == "__main__":
    main()