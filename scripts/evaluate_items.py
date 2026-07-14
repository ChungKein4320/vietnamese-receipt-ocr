from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EVALUATION_DIR, EXTRACTED_RESULT_DIR, GROUND_TRUTH_DIR


ITEM_REPORT_CSV = EVALUATION_DIR / "item_evaluation_report.csv"
ITEM_SUMMARY_JSON = EVALUATION_DIR / "item_evaluation_summary.json"
ITEM_ANALYSIS_MD = PROJECT_ROOT / "docs" / "item_level_evaluation.md"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()

    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def text_similarity(a: Any, b: Any) -> float:
    text_a = normalize_text(a)
    text_b = normalize_text(b)

    if not text_a and not text_b:
        return 1.0

    if not text_a or not text_b:
        return 0.0

    return round(SequenceMatcher(None, text_a, text_b).ratio(), 4)


def parse_number(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, int | float):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)

    if not text:
        return None

    # Vietnamese money format: 95.000 -> 95000
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return None


def number_equal(gt_value: Any, pred_value: Any) -> bool:
    gt_number = parse_number(gt_value)
    pred_number = parse_number(pred_value)

    if gt_number is None and pred_number is None:
        return True

    if gt_number is None or pred_number is None:
        return False

    return abs(gt_number - pred_number) < 1e-6


def normalize_number_for_report(value: Any) -> str:
    number = parse_number(value)

    if number is None:
        return ""

    if number.is_integer():
        return str(int(number))

    return str(number)


def get_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])

    if not isinstance(items, list):
        return []

    normalized_items = []

    for item in items:
        if isinstance(item, dict):
            normalized_items.append(item)

    return normalized_items


def evaluate_receipt_items(receipt_id: str) -> list[dict[str, Any]]:
    gt_path = GROUND_TRUTH_DIR / f"{receipt_id}.json"
    pred_path = EXTRACTED_RESULT_DIR / f"{receipt_id}_extracted.json"

    gt_payload = load_json(gt_path)
    pred_payload = load_json(pred_path)

    gt_items = get_items(gt_payload)
    pred_items = get_items(pred_payload)

    max_len = max(len(gt_items), len(pred_items))
    rows = []

    for item_index in range(max_len):
        gt_item = gt_items[item_index] if item_index < len(gt_items) else {}
        pred_item = pred_items[item_index] if item_index < len(pred_items) else {}

        gt_exists = item_index < len(gt_items)
        pred_exists = item_index < len(pred_items)

        name_score = text_similarity(
            gt_item.get("name"),
            pred_item.get("name"),
        )

        name_ok = int(name_score >= 0.75) if gt_exists else 0
        quantity_ok = int(number_equal(gt_item.get("quantity"), pred_item.get("quantity"))) if gt_exists else 0
        unit_price_ok = int(number_equal(gt_item.get("unit_price"), pred_item.get("unit_price"))) if gt_exists else 0
        line_total_ok = int(number_equal(gt_item.get("line_total"), pred_item.get("line_total"))) if gt_exists else 0

        if not pred_exists:
            name_ok = 0
            quantity_ok = 0
            unit_price_ok = 0
            line_total_ok = 0

        rows.append(
            {
                "receipt_id": receipt_id,
                "item_index": item_index + 1,
                "gt_exists": int(gt_exists),
                "pred_exists": int(pred_exists),
                "gt_name": gt_item.get("name", ""),
                "pred_name": pred_item.get("name", ""),
                "name_score": name_score,
                "name_ok": name_ok,
                "gt_quantity": normalize_number_for_report(gt_item.get("quantity")),
                "pred_quantity": normalize_number_for_report(pred_item.get("quantity")),
                "quantity_ok": quantity_ok,
                "gt_unit_price": normalize_number_for_report(gt_item.get("unit_price")),
                "pred_unit_price": normalize_number_for_report(pred_item.get("unit_price")),
                "unit_price_ok": unit_price_ok,
                "gt_line_total": normalize_number_for_report(gt_item.get("line_total")),
                "pred_line_total": normalize_number_for_report(pred_item.get("line_total")),
                "line_total_ok": line_total_ok,
                "gt_items_count": len(gt_items),
                "pred_items_count": len(pred_items),
                "items_count_ok": int(len(gt_items) == len(pred_items)),
            }
        )

    if max_len == 0:
        rows.append(
            {
                "receipt_id": receipt_id,
                "item_index": 0,
                "gt_exists": 0,
                "pred_exists": 0,
                "gt_name": "",
                "pred_name": "",
                "name_score": 1.0,
                "name_ok": 1,
                "gt_quantity": "",
                "pred_quantity": "",
                "quantity_ok": 1,
                "gt_unit_price": "",
                "pred_unit_price": "",
                "unit_price_ok": 1,
                "gt_line_total": "",
                "pred_line_total": "",
                "line_total_ok": 1,
                "gt_items_count": 0,
                "pred_items_count": 0,
                "items_count_ok": 1,
            }
        )

    return rows


def find_receipt_ids() -> list[str]:
    receipt_ids = []

    for gt_path in sorted(GROUND_TRUTH_DIR.glob("receipt_*.json")):
        receipt_ids.append(gt_path.stem)

    return receipt_ids


def safe_mean(values: pd.Series) -> float:
    if values.empty:
        return 0.0

    return round(float(values.mean()), 4)


def build_summary(report_df: pd.DataFrame) -> dict[str, Any]:
    gt_item_rows = report_df[report_df["gt_exists"] == 1].copy()

    receipt_level_df = (
        report_df.groupby("receipt_id", as_index=False)
        .agg(
            gt_items_count=("gt_items_count", "max"),
            pred_items_count=("pred_items_count", "max"),
            items_count_ok=("items_count_ok", "max"),
        )
        .sort_values("receipt_id")
    )

    field_accuracies = {
        "name_accuracy": safe_mean(gt_item_rows["name_ok"]),
        "quantity_accuracy": safe_mean(gt_item_rows["quantity_ok"]),
        "unit_price_accuracy": safe_mean(gt_item_rows["unit_price_ok"]),
        "line_total_accuracy": safe_mean(gt_item_rows["line_total_ok"]),
    }

    overall_item_field_accuracy = round(
        sum(field_accuracies.values()) / len(field_accuracies),
        4,
    )

    summary = {
        "num_receipts": int(receipt_level_df["receipt_id"].nunique()),
        "total_gt_items": int(gt_item_rows.shape[0]),
        "total_pred_items": int(report_df["pred_exists"].sum()),
        "items_count_accuracy": safe_mean(receipt_level_df["items_count_ok"]),
        "field_accuracies": field_accuracies,
        "overall_item_field_accuracy": overall_item_field_accuracy,
        "receipts_with_count_errors": receipt_level_df[
            receipt_level_df["items_count_ok"] == 0
        ]["receipt_id"].tolist(),
    }

    return summary


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"

    columns = [str(column) for column in df.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    rows = []

    for _, row in df.iterrows():
        row_values = []

        for column in df.columns:
            value = "" if pd.isna(row[column]) else str(row[column])
            value = value.replace("|", "\\|")
            row_values.append(value)

        rows.append("| " + " | ".join(row_values) + " |")

    return "\n".join([header, separator, *rows])


def build_markdown_report(report_df: pd.DataFrame, summary: dict[str, Any]) -> str:
    count_error_df = (
        report_df[["receipt_id", "gt_items_count", "pred_items_count", "items_count_ok"]]
        .drop_duplicates()
        .query("items_count_ok == 0")
        .sort_values("receipt_id")
    )

    failed_item_rows = report_df[
        (report_df["gt_exists"] == 1)
        & (
            (report_df["name_ok"] == 0)
            | (report_df["quantity_ok"] == 0)
            | (report_df["unit_price_ok"] == 0)
            | (report_df["line_total_ok"] == 0)
        )
    ].copy()

    display_failed_df = failed_item_rows[
        [
            "receipt_id",
            "item_index",
            "gt_name",
            "pred_name",
            "name_score",
            "gt_quantity",
            "pred_quantity",
            "quantity_ok",
            "gt_unit_price",
            "pred_unit_price",
            "unit_price_ok",
            "gt_line_total",
            "pred_line_total",
            "line_total_ok",
        ]
    ]

    lines = []

    lines.append("# Item-level Evaluation")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "Evaluate item extraction quality beyond receipt-level `items_count`."
    )
    lines.append("")
    lines.append("This report compares each ground-truth item with the predicted item at the same order index.")
    lines.append("")
    lines.append("Treat results as development metrics unless the inputs come from a separately held-out split.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Number of receipts: `{summary['num_receipts']}`")
    lines.append(f"- Total ground-truth items: `{summary['total_gt_items']}`")
    lines.append(f"- Total predicted items: `{summary['total_pred_items']}`")
    lines.append(f"- Items count accuracy: `{summary['items_count_accuracy'] * 100:.2f}%`")
    lines.append(f"- Overall item field accuracy: `{summary['overall_item_field_accuracy'] * 100:.2f}%`")
    lines.append("")

    lines.append("## Field Accuracies")
    lines.append("")
    field_rows = [
        {
            "field": field,
            "accuracy": f"{accuracy * 100:.2f}%",
        }
        for field, accuracy in summary["field_accuracies"].items()
    ]
    lines.append(dataframe_to_markdown(pd.DataFrame(field_rows)))
    lines.append("")

    lines.append("## Receipts with Item Count Errors")
    lines.append("")
    lines.append(dataframe_to_markdown(count_error_df))
    lines.append("")

    lines.append("## Failed Item Rows")
    lines.append("")
    lines.append(dataframe_to_markdown(display_failed_df))
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- This evaluator currently uses order-based matching. It assumes the predicted item order follows the receipt order."
    )
    lines.append(
        "- Name matching uses normalized text similarity with a threshold of `0.75`."
    )
    lines.append(
        "- Numeric fields are evaluated with exact equality after number normalization."
    )
    lines.append(
        "- This is a baseline item-level evaluator. Later versions can add fuzzy item alignment and layout-aware matching."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    ITEM_ANALYSIS_MD.parent.mkdir(parents=True, exist_ok=True)

    receipt_ids = find_receipt_ids()

    if not receipt_ids:
        raise FileNotFoundError(f"No ground truth JSON files found in: {GROUND_TRUTH_DIR}")

    all_rows = []

    for receipt_id in receipt_ids:
        pred_path = EXTRACTED_RESULT_DIR / f"{receipt_id}_extracted.json"

        if not pred_path.exists():
            print(f"Skipping {receipt_id}: prediction not found at {pred_path}")
            continue

        all_rows.extend(evaluate_receipt_items(receipt_id))

    report_df = pd.DataFrame(all_rows)
    summary = build_summary(report_df)

    report_df.to_csv(ITEM_REPORT_CSV, index=False, encoding="utf-8-sig")
    ITEM_SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown_report = build_markdown_report(report_df, summary)
    ITEM_ANALYSIS_MD.write_text(markdown_report, encoding="utf-8")

    print("Item-level evaluation completed.")
    print(f"- {ITEM_REPORT_CSV}")
    print(f"- {ITEM_SUMMARY_JSON}")
    print(f"- {ITEM_ANALYSIS_MD}")

    print("\nSummary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
