from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EVALUATION_DIR, EXTRACTED_RESULT_DIR
from receipt_ocr.layout_item_parser import parse_layout_receipt_items_for_receipt


LAYOUT_DEBUG_DIR = EVALUATION_DIR / "layout_debug"
LAYOUT_EXTRACTED_RESULT_DIR = PROJECT_ROOT / "data" / "layout_extracted_results"
LAYOUT_ITEM_PARSER_VERSION = "layout_aware_item_v0.4_candidate"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def item_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "to_dict"):
        return item.to_dict()

    if is_dataclass(item):
        return asdict(item)

    if isinstance(item, dict):
        return item

    raise TypeError(f"Unsupported item type: {type(item)}")


def find_receipt_ids() -> list[str]:
    receipt_ids = []

    for path in sorted(EXTRACTED_RESULT_DIR.glob("receipt_*_extracted.json")):
        receipt_id = path.stem.replace("_extracted", "")
        receipt_ids.append(receipt_id)

    return receipt_ids


def run_one(receipt_id: str) -> Path:
    extracted_path = EXTRACTED_RESULT_DIR / f"{receipt_id}_extracted.json"
    layout_csv_path = LAYOUT_DEBUG_DIR / f"{receipt_id}_layout_lines.csv"

    if not extracted_path.exists():
        raise FileNotFoundError(f"Extracted JSON not found: {extracted_path}")

    if not layout_csv_path.exists():
        raise FileNotFoundError(
            f"Layout CSV not found: {layout_csv_path}. "
            "Run scripts/inspect_ocr_layout.py or scripts/batch_inspect_ocr_layout.py first."
        )

    payload = load_json(extracted_path)

    layout_items = parse_layout_receipt_items_for_receipt(
        receipt_id=receipt_id,
        layout_debug_dir=LAYOUT_DEBUG_DIR,
    )

    payload["original_parser_version"] = payload.get("parser_version")
    payload["parser_version"] = "rule_based_v0.3+layout_aware_item_v0.4_candidate"
    payload["item_parser_version"] = LAYOUT_ITEM_PARSER_VERSION
    payload["items"] = [item_to_dict(item) for item in layout_items]
    payload["items_count"] = len(layout_items)

    output_path = LAYOUT_EXTRACTED_RESULT_DIR / f"{receipt_id}_layout_extracted.json"
    save_json(payload, output_path)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace receipt items with layout-aware item parser output."
    )

    parser.add_argument(
        "--receipt-id",
        type=str,
        default=None,
        help="Receipt ID, for example receipt_004.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run layout-aware item extraction for all receipts.",
    )

    args = parser.parse_args()

    if not args.all and not args.receipt_id:
        raise ValueError("Use --all or --receipt-id.")

    if args.all and args.receipt_id:
        raise ValueError("Use either --all or --receipt-id, not both.")

    if args.all:
        receipt_ids = find_receipt_ids()
    else:
        receipt_ids = [args.receipt_id]

    if not receipt_ids:
        raise FileNotFoundError(f"No extracted JSON files found in {EXTRACTED_RESULT_DIR}")

    LAYOUT_EXTRACTED_RESULT_DIR.mkdir(parents=True, exist_ok=True)

    for receipt_id in receipt_ids:
        output_path = run_one(receipt_id)
        print(f"Layout item extraction completed: {receipt_id}")
        print(f"Saved: {output_path}")
        print("-" * 60)


if __name__ == "__main__":
    main()