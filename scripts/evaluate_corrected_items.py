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

from receipt_ocr.config import EVALUATION_DIR, GROUND_TRUTH_DIR


CORRECTED_RESULT_DIR = PROJECT_ROOT / "data" / "corrected_results"

CORRECTED_ITEM_REPORT_CSV = EVALUATION_DIR / "corrected_item_evaluation_report.csv"
CORRECTED_ITEM_SUMMARY_JSON = EVALUATION_DIR / "corrected_item_evaluation_summary.json"
CORRECTED_ITEM_ANALYSIS_MD = PROJECT_ROOT / "docs" / "corrected_item_evaluation.md"


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


def get_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", [])

    if not isinstance(items, list):
        return []

    return [item for item in items if isinstance(item, dict)]


def find_receipt_ids() -> list[str]:
    return [path.stem for path in sorted(GROUND_TRUTH_DIR.glob("receipt_*.json"))]


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"

    columns = [str(column) for column in df.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    rows = []

    for _, row in df.iterrows():
        values = []

        for column in df.columns:
            value = "" if pd.isna(row[column]) else str(row[column])
            value = value.replace("|", "\\|")
            values.append(value)

        rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator, *rows])


def evaluate_corrected_names() -> pd.DataFrame:
    rows = []

    for receipt_id in find_receipt_ids():
        gt_path = GROUND_TRUTH_DIR / f"{receipt_id}.json"
        corrected_path = CORRECTED_RESULT_DIR / f"{receipt_id}_corrected.json"

        if not corrected_path.exists():
            continue

        gt_payload = load_json(gt_path)
        corrected_payload = load_json(corrected_path)

        gt_items = get_items(gt_payload)
        corrected_items = get_items(corrected_payload)

        max_len = max(len(gt_items), len(corrected_items))

        for index in range(max_len):
            gt_item = gt_items[index] if index < len(gt_items) else {}
            pred_item = corrected_items[index] if index < len(corrected_items) else {}

            raw_name = pred_item.get("name", "")
            corrected_name = pred_item.get("corrected_name", "")
            gt_name = gt_item.get("name", "")

            raw_score = text_similarity(gt_name, raw_name)
            corrected_score = text_similarity(gt_name, corrected_name)

            rows.append(
                {
                    "receipt_id": receipt_id,
                    "item_index": index + 1,
                    "gt_name": gt_name,
                    "raw_name": raw_name,
                    "corrected_name": corrected_name,
                    "raw_score": raw_score,
                    "corrected_score": corrected_score,
                    "raw_ok": int(raw_score >= 0.75),
                    "corrected_ok": int(corrected_score >= 0.75),
                    "score_delta": round(corrected_score - raw_score, 4),
                }
            )

    return pd.DataFrame(rows)


def build_summary(report_df: pd.DataFrame) -> dict[str, Any]:
    if report_df.empty:
        return {
            "num_rows": 0,
            "raw_name_accuracy": 0.0,
            "corrected_name_accuracy": 0.0,
            "avg_raw_score": 0.0,
            "avg_corrected_score": 0.0,
            "avg_score_delta": 0.0,
            "num_improved": 0,
            "num_regressed": 0,
            "num_unchanged": 0,
        }

    improved_df = report_df[report_df["score_delta"] > 0]
    regressed_df = report_df[report_df["score_delta"] < 0]
    unchanged_df = report_df[report_df["score_delta"] == 0]

    return {
        "num_rows": int(report_df.shape[0]),
        "raw_name_accuracy": round(float(report_df["raw_ok"].mean()), 4),
        "corrected_name_accuracy": round(float(report_df["corrected_ok"].mean()), 4),
        "avg_raw_score": round(float(report_df["raw_score"].mean()), 4),
        "avg_corrected_score": round(float(report_df["corrected_score"].mean()), 4),
        "avg_score_delta": round(float(report_df["score_delta"].mean()), 4),
        "num_improved": int(improved_df.shape[0]),
        "num_regressed": int(regressed_df.shape[0]),
        "num_unchanged": int(unchanged_df.shape[0]),
    }


def build_markdown_report(report_df: pd.DataFrame, summary: dict[str, Any]) -> str:
    improved_df = (
        report_df[report_df["score_delta"] > 0]
        .sort_values(["score_delta"], ascending=False)
        .head(20)
    )

    regressed_df = (
        report_df[report_df["score_delta"] < 0]
        .sort_values(["score_delta"], ascending=True)
        .head(20)
    )

    lines = []

    lines.append("# Corrected Item Name Evaluation")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "Evaluate whether OCR text correction improves item name quality without changing numeric fields."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Number of compared item rows: `{summary['num_rows']}`")
    lines.append(f"- Raw item name accuracy: `{summary['raw_name_accuracy'] * 100:.2f}%`")
    lines.append(f"- Corrected item name accuracy: `{summary['corrected_name_accuracy'] * 100:.2f}%`")
    lines.append(f"- Average raw similarity score: `{summary['avg_raw_score']:.4f}`")
    lines.append(f"- Average corrected similarity score: `{summary['avg_corrected_score']:.4f}`")
    lines.append(f"- Average score delta: `{summary['avg_score_delta']:.4f}`")
    lines.append(f"- Improved rows: `{summary['num_improved']}`")
    lines.append(f"- Regressed rows: `{summary['num_regressed']}`")
    lines.append(f"- Unchanged rows: `{summary['num_unchanged']}`")
    lines.append("")
    lines.append("## Most Improved Rows")
    lines.append("")
    lines.append(dataframe_to_markdown(improved_df))
    lines.append("")
    lines.append("## Regressed Rows")
    lines.append("")
    lines.append(dataframe_to_markdown(regressed_df))
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This evaluator only checks item names.")
    lines.append("- It compares `name` versus `corrected_name` against ground truth.")
    lines.append("- Numeric fields are intentionally not modified by the correction layer.")
    lines.append("- The current correction layer is rule-based and experimental.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    CORRECTED_ITEM_ANALYSIS_MD.parent.mkdir(parents=True, exist_ok=True)

    report_df = evaluate_corrected_names()
    summary = build_summary(report_df)

    report_df.to_csv(CORRECTED_ITEM_REPORT_CSV, index=False, encoding="utf-8-sig")

    CORRECTED_ITEM_SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    CORRECTED_ITEM_ANALYSIS_MD.write_text(
        build_markdown_report(report_df, summary),
        encoding="utf-8",
    )

    print("Corrected item name evaluation completed.")
    print(f"- {CORRECTED_ITEM_REPORT_CSV}")
    print(f"- {CORRECTED_ITEM_SUMMARY_JSON}")
    print(f"- {CORRECTED_ITEM_ANALYSIS_MD}")
    print("")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()