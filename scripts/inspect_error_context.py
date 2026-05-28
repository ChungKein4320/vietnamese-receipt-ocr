from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EVALUATION_DIR, OCR_OUTPUT_DIR, EXTRACTED_RESULT_DIR, GROUND_TRUTH_DIR


EVALUATION_REPORT_CSV = EVALUATION_DIR / "evaluation_report.csv"


FIELD_TO_COLUMNS = {
    "store_name": ("store_name_gt", "store_name_pred", "store_name_ok"),
    "datetime": ("datetime_gt", "datetime_pred", "datetime_ok"),
    "invoice_id": ("invoice_id_gt", "invoice_id_pred", "invoice_id_ok"),
    "total_amount": ("total_amount_gt", "total_amount_pred", "total_amount_ok"),
    "payment_method": ("payment_method_gt", "payment_method_pred", "payment_method_ok"),
    "items_count": ("items_count_gt", "items_count_pred", "items_count_ok"),
}


def load_text(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def print_section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_ocr_lines(receipt_id: str) -> None:
    ocr_path = OCR_OUTPUT_DIR / f"{receipt_id}_ocr.txt"
    text = load_text(ocr_path)

    if not text:
        print(f"OCR text not found: {ocr_path}")
        return

    print(f"OCR text: {ocr_path}")
    print("-" * 90)

    for index, line in enumerate(text.splitlines(), start=1):
        print(f"{index:02d}: {line}")


def print_json_summary(receipt_id: str) -> None:
    gt_path = GROUND_TRUTH_DIR / f"{receipt_id}.json"
    pred_path = EXTRACTED_RESULT_DIR / f"{receipt_id}_extracted.json"

    gt = load_json(gt_path)
    pred = load_json(pred_path)

    print("\nGround truth:")
    print(json.dumps(gt, ensure_ascii=False, indent=2))

    print("\nPrediction:")
    print(json.dumps(pred, ensure_ascii=False, indent=2))


def inspect_field_errors(field: str) -> None:
    if field not in FIELD_TO_COLUMNS:
        raise ValueError(f"Unknown field: {field}. Choose one of: {list(FIELD_TO_COLUMNS)}")

    if not EVALUATION_REPORT_CSV.exists():
        raise FileNotFoundError(
            f"Evaluation report not found: {EVALUATION_REPORT_CSV}\n"
            "Run: python scripts/evaluate_extraction.py --all"
        )

    gt_col, pred_col, ok_col = FIELD_TO_COLUMNS[field]

    report_df = pd.read_csv(EVALUATION_REPORT_CSV)
    error_df = report_df[report_df[ok_col].astype(str) == "0"].copy()

    if error_df.empty:
        print(f"No errors found for field: {field}")
        return

    print_section(f"Inspecting field errors: {field}")

    for _, row in error_df.iterrows():
        receipt_id = str(row["receipt_id"])

        print_section(f"{receipt_id} | field={field}")
        print(f"ground_truth: {row.get(gt_col, '')}")
        print(f"prediction   : {row.get(pred_col, '')}")

        print("\nOCR lines:")
        print_ocr_lines(receipt_id)

        print("\nStructured JSON:")
        print_json_summary(receipt_id)


def inspect_receipt(receipt_id: str) -> None:
    print_section(f"Inspecting receipt: {receipt_id}")
    print_ocr_lines(receipt_id)
    print_json_summary(receipt_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect OCR context for failed extraction cases."
    )

    parser.add_argument(
        "--field",
        type=str,
        default=None,
        choices=list(FIELD_TO_COLUMNS),
        help="Inspect all failed receipts for a specific field.",
    )

    parser.add_argument(
        "--receipt-id",
        type=str,
        default=None,
        help="Inspect one receipt by id, for example receipt_011.",
    )

    args = parser.parse_args()

    if args.field is None and args.receipt_id is None:
        raise ValueError("Provide --field or --receipt-id.")

    if args.field is not None and args.receipt_id is not None:
        raise ValueError("Use either --field or --receipt-id, not both.")

    if args.field is not None:
        inspect_field_errors(args.field)

    if args.receipt_id is not None:
        inspect_receipt(args.receipt_id)


if __name__ == "__main__":
    main()