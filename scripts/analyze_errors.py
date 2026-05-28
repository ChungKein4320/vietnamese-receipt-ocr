from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EVALUATION_DIR


DOCS_DIR = PROJECT_ROOT / "docs"
ERROR_ANALYSIS_MD = DOCS_DIR / "error_analysis.md"
ERROR_BUCKETS_CSV = EVALUATION_DIR / "error_buckets.csv"

EVALUATION_REPORT_CSV = EVALUATION_DIR / "evaluation_report.csv"
EVALUATION_SUMMARY_JSON = EVALUATION_DIR / "evaluation_summary.json"


FIELD_CONFIGS = [
    {
        "field": "store_name",
        "ok_col": "store_name_ok",
        "score_col": "store_name_score",
        "gt_col": "store_name_gt",
        "pred_col": "store_name_pred",
    },
    {
        "field": "datetime",
        "ok_col": "datetime_ok",
        "score_col": "datetime_score",
        "gt_col": "datetime_gt",
        "pred_col": "datetime_pred",
    },
    {
        "field": "invoice_id",
        "ok_col": "invoice_id_ok",
        "score_col": "invoice_id_score",
        "gt_col": "invoice_id_gt",
        "pred_col": "invoice_id_pred",
    },
    {
        "field": "total_amount",
        "ok_col": "total_amount_ok",
        "score_col": "total_amount_score",
        "gt_col": "total_amount_gt",
        "pred_col": "total_amount_pred",
    },
    {
        "field": "payment_method",
        "ok_col": "payment_method_ok",
        "score_col": "payment_method_score",
        "gt_col": "payment_method_gt",
        "pred_col": "payment_method_pred",
    },
    {
        "field": "items_count",
        "ok_col": "items_count_ok",
        "score_col": "items_count_score",
        "gt_col": "items_count_gt",
        "pred_col": "items_count_pred",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def load_report(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Evaluation report not found: {path}\n"
            "Run: python scripts/evaluate_extraction.py --all"
        )

    return pd.read_csv(path)


def normalize_cell(value: Any) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() == "nan":
        return ""

    return text


def accuracy_to_percent(value: float | int | None) -> str:
    if value is None:
        return "N/A"

    return f"{float(value) * 100:.2f}%"


def build_error_buckets(report_df: pd.DataFrame, summary: dict[str, Any]) -> pd.DataFrame:
    rows = []

    num_receipts = int(summary.get("num_receipts", len(report_df)))
    field_accuracy = summary.get("field_accuracy", {})

    for config in FIELD_CONFIGS:
        field = config["field"]
        ok_col = config["ok_col"]

        if ok_col not in report_df.columns:
            continue

        num_errors = int((report_df[ok_col].astype(str) == "0").sum())
        accuracy = field_accuracy.get(field)

        rows.append(
            {
                "field": field,
                "accuracy": accuracy,
                "accuracy_percent": accuracy_to_percent(accuracy),
                "num_errors": num_errors,
                "num_receipts": num_receipts,
                "error_rate": round(num_errors / num_receipts, 4) if num_receipts else None,
            }
        )

    return pd.DataFrame(rows)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """
    Convert a DataFrame to a GitHub-compatible markdown table
    without requiring pandas optional dependency 'tabulate'.
    """
    if df.empty:
        return "_No rows._"

    columns = [str(column) for column in df.columns]

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    rows = []

    for _, row in df.iterrows():
        row_values = []

        for column in df.columns:
            value = normalize_cell(row[column])
            value = value.replace("|", "\\|")
            row_values.append(value)

        rows.append("| " + " | ".join(row_values) + " |")

    return "\n".join([header, separator, *rows])


def build_field_error_table(report_df: pd.DataFrame, config: dict[str, str]) -> pd.DataFrame:
    ok_col = config["ok_col"]
    score_col = config["score_col"]
    gt_col = config["gt_col"]
    pred_col = config["pred_col"]

    error_df = report_df[report_df[ok_col].astype(str) == "0"].copy()

    if error_df.empty:
        return pd.DataFrame(columns=["receipt_id", "ground_truth", "prediction", "score"])

    output_df = pd.DataFrame(
        {
            "receipt_id": error_df["receipt_id"].map(normalize_cell),
            "ground_truth": error_df[gt_col].map(normalize_cell),
            "prediction": error_df[pred_col].map(normalize_cell),
            "score": error_df[score_col].map(normalize_cell),
        }
    )

    return output_df


def build_warning_table(report_df: pd.DataFrame) -> pd.DataFrame:
    if "prediction_warnings" not in report_df.columns:
        return pd.DataFrame(columns=["warning", "count"])

    warning_counts: dict[str, int] = {}

    for raw_value in report_df["prediction_warnings"].fillna(""):
        value = str(raw_value).strip()

        if not value:
            continue

        warnings = [item.strip() for item in value.split("|") if item.strip()]

        for warning in warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1

    rows = [
        {
            "warning": warning,
            "count": count,
        }
        for warning, count in sorted(
            warning_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return pd.DataFrame(rows)


def build_markdown_report(
    report_df: pd.DataFrame,
    summary: dict[str, Any],
    error_buckets_df: pd.DataFrame,
    warning_df: pd.DataFrame,
) -> str:
    overall_accuracy = summary.get("overall_accuracy")
    num_receipts = summary.get("num_receipts", len(report_df))

    lines = []

    lines.append("# Error Analysis")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "Analyze the remaining errors of the OCR + rule-based extraction pipeline "
        "after the MVP v1 implementation."
    )
    lines.append("")
    lines.append("This report is generated from:")
    lines.append("")
    lines.append("```text")
    lines.append("data/evaluation/evaluation_report.csv")
    lines.append("data/evaluation/evaluation_summary.json")
    lines.append("```")
    lines.append("")
    lines.append("## Current Evaluation Summary")
    lines.append("")
    lines.append(f"- Number of receipts: `{num_receipts}`")
    lines.append(f"- Overall accuracy: `{accuracy_to_percent(overall_accuracy)}`")
    lines.append("")
    lines.append("### Field-level error buckets")
    lines.append("")
    lines.append(dataframe_to_markdown(error_buckets_df))
    lines.append("")
    lines.append("## Field-level Error Details")
    lines.append("")

    for config in FIELD_CONFIGS:
        field = config["field"]
        error_table = build_field_error_table(report_df, config)

        lines.append(f"### {field}")
        lines.append("")

        if error_table.empty:
            lines.append("_No errors detected for this field._")
        else:
            lines.append(dataframe_to_markdown(error_table))

        lines.append("")

    lines.append("## Parser Warnings")
    lines.append("")

    if warning_df.empty:
        lines.append("_No parser warnings found in the current evaluation report._")
    else:
        lines.append(dataframe_to_markdown(warning_df))

    lines.append("")
    lines.append("## Observations")
    lines.append("")
    lines.append("### Strongest field")
    lines.append("")
    lines.append(
        "`total_amount` is currently the strongest field. The main improvement came from "
        "normalizing Vietnamese money formats such as `70.000d`, `80.000d`, `20.000d`, "
        "and `CASH(VND)-88000`."
    )
    lines.append("")
    lines.append("### Weakest field")
    lines.append("")
    lines.append(
        "`invoice_id` is currently the weakest field. Receipt IDs appear in many inconsistent "
        "formats and can be confused with phone numbers, cashier IDs, receipt titles, "
        "or transaction codes."
    )
    lines.append("")
    lines.append("### Item extraction")
    lines.append("")
    lines.append(
        "`items_count` is still unstable because item names, quantities, unit prices, "
        "and line totals are often split across multiple OCR lines. A pure text-based parser "
        "has limited layout awareness."
    )
    lines.append("")
    lines.append("### Payment method")
    lines.append("")
    lines.append(
        "`payment_method` is rule-based and depends on keyword matching. It can fail when OCR "
        "misses or corrupts words such as `tien mat`, `cash`, or card-related terms."
    )
    lines.append("")
    lines.append("## Parser v0.2 Improvement Plan")
    lines.append("")
    lines.append("Recommended priority order:")
    lines.append("")
    lines.append("1. Improve `invoice_id` extraction with stricter receipt-code patterns.")
    lines.append("2. Improve `datetime` parsing for split date/time lines and OCR-corrupted separators.")
    lines.append("3. Improve `payment_method` keyword normalization.")
    lines.append("4. Add item-level evaluation beyond `items_count`.")
    lines.append("5. Start layout-aware item parsing using PaddleOCR bounding boxes.")
    lines.append("")
    lines.append("## Next Step")
    lines.append("")
    lines.append(
        "Use this error analysis to implement `rule_based_v0.2` and compare it against "
        "`rule_based_v0.1` using the same evaluation pipeline."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    report_df = load_report(EVALUATION_REPORT_CSV)
    summary = load_json(EVALUATION_SUMMARY_JSON)

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    error_buckets_df = build_error_buckets(report_df, summary)
    warning_df = build_warning_table(report_df)

    ERROR_BUCKETS_CSV.parent.mkdir(parents=True, exist_ok=True)
    error_buckets_df.to_csv(ERROR_BUCKETS_CSV, index=False, encoding="utf-8-sig")

    markdown_report = build_markdown_report(
        report_df=report_df,
        summary=summary,
        error_buckets_df=error_buckets_df,
        warning_df=warning_df,
    )

    ERROR_ANALYSIS_MD.write_text(markdown_report, encoding="utf-8")

    print("Generated error analysis files:")
    print(f"- {ERROR_ANALYSIS_MD}")
    print(f"- {ERROR_BUCKETS_CSV}")


if __name__ == "__main__":
    main()