from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import (
    DATASET_MANIFEST_PATH,
    EVALUATION_DIR,
    EXTRACTED_RESULT_DIR,
)
from receipt_ocr.dataset_manifest import (
    ALLOWED_SPLITS,
    ManifestValidationError,
    load_dataset_manifest,
    records_for_split,
)
from receipt_ocr.evaluator import (
    evaluate_single_receipt,
    load_json,
    summarize_evaluation,
)


def prediction_path_for(ground_truth_path: Path) -> Path:
    receipt_id = ground_truth_path.stem
    return EXTRACTED_RESULT_DIR / f"{receipt_id}_extracted.json"


def evaluation_output_dir(split: str, receipt_id: str | None = None) -> Path:
    split_output_dir = EVALUATION_DIR / split

    if receipt_id is None:
        return split_output_dir

    return split_output_dir / "single" / receipt_id


def write_csv_report(rows: list[dict], output_path: Path) -> None:
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(summary: dict) -> None:
    print("\nEvaluation Summary")
    print("=" * 60)
    print(f"num_receipts     : {summary['num_receipts']}")
    print(f"overall_accuracy : {summary['overall_accuracy']}")
    print("-" * 60)

    for field, accuracy in summary["field_accuracy"].items():
        if accuracy is None:
            print(f"{field:<16}: N/A")
        else:
            print(f"{field:<16}: {accuracy:.2%}")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate extracted receipt JSON files against ground truth JSON files."
    )

    parser.add_argument(
        "--receipt-id",
        type=str,
        default=None,
        help="Evaluate one receipt ID, e.g. receipt_001.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all ground truth files.",
    )

    parser.add_argument(
        "--split",
        choices=sorted(ALLOWED_SPLITS),
        default="development",
        help="Dataset split to evaluate (default: development).",
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DATASET_MANIFEST_PATH,
        help="Path to the dataset split manifest.",
    )

    args = parser.parse_args()

    if args.receipt_id is None and not args.all:
        raise ValueError("Please provide --receipt-id or use --all.")

    if args.receipt_id is not None and args.all:
        raise ValueError("Use either --receipt-id or --all, not both.")

    try:
        records = records_for_split(
            load_dataset_manifest(
                args.manifest,
                project_root=PROJECT_ROOT,
                check_files=True,
            ),
            args.split,
        )
    except ManifestValidationError as error:
        parser.error(str(error))

    if args.receipt_id is not None:
        records = [record for record in records if record.receipt_id == args.receipt_id]

        if not records:
            parser.error(
                f"Receipt '{args.receipt_id}' is not in split '{args.split}'."
            )

    split_output_dir = evaluation_output_dir(args.split, args.receipt_id)
    split_output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    missing_predictions = []

    for record in records:
        ground_truth_path = PROJECT_ROOT / record.ground_truth_path

        if not ground_truth_path.exists():
            raise FileNotFoundError(f"Ground truth not found: {ground_truth_path}")

        prediction_path = prediction_path_for(ground_truth_path)

        if not prediction_path.exists():
            missing_predictions.append(str(prediction_path))
            continue

        ground_truth = load_json(ground_truth_path)
        prediction = load_json(prediction_path)

        row = evaluate_single_receipt(
            ground_truth=ground_truth,
            prediction=prediction,
        )

        rows.append(row)

    if missing_predictions:
        print("\nMissing prediction files:")
        for path in missing_predictions:
            print(f"- {path}")

    if not rows:
        raise FileNotFoundError(
            f"No predictions available for split '{args.split}'."
        )

    summary = summarize_evaluation(rows)
    summary["split"] = args.split

    csv_output_path = split_output_dir / "evaluation_report.csv"
    json_output_path = split_output_dir / "evaluation_summary.json"

    write_csv_report(rows, csv_output_path)

    json_output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_summary(summary)

    print("\nSaved reports:")
    print(f"- {csv_output_path}")
    print(f"- {json_output_path}")


if __name__ == "__main__":
    main()
