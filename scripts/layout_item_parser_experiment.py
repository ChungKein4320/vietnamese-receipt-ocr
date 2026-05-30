from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import EVALUATION_DIR, GROUND_TRUTH_DIR
from receipt_ocr.text_normalizer import (
    clean_line,
    find_money_values,
    is_probable_barcode,
    normalize_for_matching,
    parse_quantity,
)


LAYOUT_DEBUG_DIR = EVALUATION_DIR / "layout_debug"
LAYOUT_ITEM_REPORT_CSV = EVALUATION_DIR / "layout_item_parser_report.csv"
LAYOUT_ITEM_SUMMARY_JSON = EVALUATION_DIR / "layout_item_parser_summary.json"
LAYOUT_ITEM_ANALYSIS_MD = PROJECT_ROOT / "docs" / "layout_item_parser_experiment.md"


ITEM_SECTION_START_KEYWORDS = [
    "MAT HANG",
    "TEN HANG",
    "TEN MON",
    "SAN PHAM",
    "ITEM",
    "DESCRIPTION",
    "DON GIA",
    "D GIA",
    "D.GIA",
    "DG",
    "SL",
]

ITEM_SECTION_END_KEYWORDS = [
    "TONG",
    "CONG TIEN",
    "THANH TOAN",
    "TIEN KHACH",
    "TIEN MAT",
    "TRA LAI",
    "VAT",
    "GTGT",
    "CAM ON",
    "THANK",
]


@dataclass
class LayoutRow:
    receipt_id: str
    row_id: int
    texts: list[str]
    x_mins: list[float]

    @property
    def text(self) -> str:
        return " | ".join(self.texts)


@dataclass
class LayoutItem:
    receipt_id: str
    name: str
    quantity: float | None
    unit_price: int | None
    line_total: int | None
    source_row_id: int
    value_row_id: int | None
    strategy: str


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


def normalize_layout_matching_text(value: Any) -> str:
    """
    Normalize OCR text for layout-row matching.

    This is used only for layout parser decisions such as:
    - item section start/end detection
    - metadata/summary/noise filtering

    It should not modify the original extracted text.
    """
    text = normalize_for_matching(str(value or ""))

    replacements = {
        "T8NG": "TONG",
        "T0NG": "TONG",
        "C0NG": "CONG",
        "T0AN": "TOAN",
        "THNH": "THANH",
        "THNH TIER": "THANH TIEN",
        "T TIER": "T TIEN",
        "LGI": "LAI",
        "MAL": "MAT",
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    text = re.sub(r"[^A-Z0-9]+", " ", text)
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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def read_layout_rows(path: Path) -> list[LayoutRow]:
    receipt_id = path.stem.replace("_layout_lines", "")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        records = list(csv.DictReader(file))

    grouped: dict[int, list[dict[str, str]]] = {}

    for record in records:
        row_id_text = record.get("row_id") or ""

        if not row_id_text:
            continue

        try:
            row_id = int(float(row_id_text))
        except ValueError:
            continue

        grouped.setdefault(row_id, []).append(record)

    rows = []

    for row_id, row_records in sorted(grouped.items()):
        row_records = sorted(
            row_records,
            key=lambda record: float(record.get("x_min") or 0),
        )

        texts = [clean_line(record.get("text", "")) for record in row_records]
        texts = [text for text in texts if text]

        x_mins = [float(record.get("x_min") or 0) for record in row_records]

        if texts:
            rows.append(
                LayoutRow(
                    receipt_id=receipt_id,
                    row_id=row_id,
                    texts=texts,
                    x_mins=x_mins,
                )
            )

    return rows


def row_normalized(row: LayoutRow) -> str:
    return normalize_layout_matching_text(row.text)


def is_header_row(row: LayoutRow) -> bool:
    normalized = row_normalized(row)

    return any(keyword in normalized for keyword in ITEM_SECTION_START_KEYWORDS)


def is_end_row(row: LayoutRow) -> bool:
    normalized = row_normalized(row)

    return any(keyword in normalized for keyword in ITEM_SECTION_END_KEYWORDS)


def find_item_section_rows(rows: list[LayoutRow]) -> list[LayoutRow]:
    start_index = 0

    for index, row in enumerate(rows):
        if is_header_row(row):
            start_index = index + 1
            break

    end_index = len(rows)

    for index in range(start_index, len(rows)):
        if is_end_row(rows[index]):
            end_index = index
            break

    return rows[start_index:end_index]


def has_alpha(text: str) -> bool:
    return bool(re.search(r"[A-Za-zÀ-ỹ]", text))


def is_noise_name(text: str) -> bool:
    normalized_clean = normalize_layout_matching_text(text)

    if not normalized_clean:
        return True

    if len(normalized_clean) <= 2:
        return True

    noise_keywords = [
        "HOA DON",
        "PHIEU",
        "QUAY",
        "NVBH",
        "THU NGAN",
        "NHAN VIEN",
        "KHACH HANG",
        "KHACH LE",
        "HOTLINE",
        "TEL",
        "FAX",
        "WIFI",
        "CAM ON",
        "THANK",
        "TONG",
        "THANH TOAN",
        "TIEN",
        "TRA LAI",
        "GIAM",
        "CHIET KHAU",
        "VAT",
        "GTGT",
        "KM",
    ]

    if any(keyword in normalized_clean for keyword in noise_keywords):
        return True

    exact_headers = {
        "TT",
        "STT",
        "SL",
        "DG",
        "D GIA",
        "DON GIA",
        "GIA",
        "KM",
        "T TIEN",
        "THANH TIEN",
        "TEN MON",
        "TEN HANG",
        "MAT HANG",
    }

    if normalized_clean in exact_headers:
        return True

    return False


def is_probable_item_name_text(text: str) -> bool:
    text = clean_line(text)

    if not text:
        return False

    if not has_alpha(text):
        return False

    if is_probable_barcode(text):
        return False

    if find_money_values(text):
        return False

    if is_noise_name(text):
        return False

    return True


def extract_name_from_row(row: LayoutRow) -> str | None:
    # Prefer cells with alphabetic text that are not headers/noise.
    candidates = []

    for text in row.texts:
        cleaned = clean_line(text)

        if is_probable_item_name_text(cleaned):
            candidates.append(cleaned)

    if not candidates:
        return None

    # If a row has multiple text cells such as "Sua chua | matcha",
    # join neighboring text cells into one name.
    if len(candidates) >= 2:
        return " ".join(candidates)

    name = candidates[0]

    # Handle temporary-bill style:
    #   1 APPLE TEAICE
    # Keep quantity separately if needed later, but remove leading quantity from name.
    match = re.match(r"^\d+(?:[,.]\d+)?\s+([A-Za-zÀ-ỹ].+)$", name)

    if match:
        return clean_line(match.group(1))

    # Handle compact OCR:
    #   1COCONUT
    match = re.match(r"^\d+([A-Za-zÀ-ỹ].+)$", name)

    if match:
        return clean_line(match.group(1))

    return name


def collect_money_values(row: LayoutRow) -> list[int]:
    values = []

    for text in row.texts:
        values.extend(find_money_values(text))

    return values


def collect_quantity_values(row: LayoutRow) -> list[float]:
    quantities = []

    for text in row.texts:
        cleaned = clean_line(text)

        if is_probable_barcode(cleaned):
            continue

        if find_money_values(cleaned):
            continue

        quantity = parse_quantity(cleaned)

        if quantity is not None:
            quantities.append(quantity)

    return quantities


def parse_values_from_row(row: LayoutRow) -> tuple[float | None, int | None, int | None]:
    money_values = collect_money_values(row)
    quantity_values = collect_quantity_values(row)

    quantity = quantity_values[0] if quantity_values else None
    unit_price = None
    line_total = None

    if len(money_values) >= 2:
        unit_price = money_values[0]
        line_total = money_values[-1]
    elif len(money_values) == 1:
        unit_price = money_values[0]
        line_total = money_values[0]

    return quantity, unit_price, line_total


def parse_single_row_item(row: LayoutRow) -> LayoutItem | None:
    name = extract_name_from_row(row)

    if not name:
        return None

    quantity, unit_price, line_total = parse_values_from_row(row)

    if unit_price is None and line_total is None:
        return None

    return LayoutItem(
        receipt_id=row.receipt_id,
        name=name,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        source_row_id=row.row_id,
        value_row_id=row.row_id,
        strategy="single_row",
    )


def parse_name_value_pair(
    name_row: LayoutRow,
    value_row: LayoutRow,
) -> LayoutItem | None:
    name = extract_name_from_row(name_row)

    if not name:
        return None

    quantity, unit_price, line_total = parse_values_from_row(value_row)

    if unit_price is None and line_total is None:
        return None

    return LayoutItem(
        receipt_id=name_row.receipt_id,
        name=name,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        source_row_id=name_row.row_id,
        value_row_id=value_row.row_id,
        strategy="name_value_pair",
    )


def parse_layout_items_for_receipt(receipt_id: str) -> list[LayoutItem]:
    csv_path = LAYOUT_DEBUG_DIR / f"{receipt_id}_layout_lines.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Layout CSV not found: {csv_path}")

    rows = read_layout_rows(csv_path)
    section_rows = find_item_section_rows(rows)

    items: list[LayoutItem] = []
    index = 0

    while index < len(section_rows):
        row = section_rows[index]

        # First try single-row item layouts.
        single_row_item = parse_single_row_item(row)

        if single_row_item is not None:
            items.append(single_row_item)
            index += 1
            continue

        # Then try name row + value row.
        if is_probable_item_name_text(row.text):
            for lookahead_index in range(index + 1, min(index + 4, len(section_rows))):
                value_row = section_rows[lookahead_index]

                # Stop if another item name appears before values.
                if lookahead_index > index + 1 and is_probable_item_name_text(value_row.text):
                    break

                pair_item = parse_name_value_pair(row, value_row)

                if pair_item is not None:
                    items.append(pair_item)
                    index = lookahead_index + 1
                    break
            else:
                index += 1

            continue

        index += 1

    return items


def get_gt_items(receipt_id: str) -> list[dict[str, Any]]:
    gt_path = GROUND_TRUTH_DIR / f"{receipt_id}.json"
    payload = load_json(gt_path)
    items = payload.get("items", [])

    if not isinstance(items, list):
        return []

    return [item for item in items if isinstance(item, dict)]


def normalize_number(value: Any) -> float | None:
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

    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return None


def number_equal(a: Any, b: Any) -> bool:
    number_a = normalize_number(a)
    number_b = normalize_number(b)

    if number_a is None and number_b is None:
        return True

    if number_a is None or number_b is None:
        return False

    return abs(number_a - number_b) < 1e-6


def evaluate_receipt(receipt_id: str) -> list[dict[str, Any]]:
    gt_items = get_gt_items(receipt_id)
    pred_items = parse_layout_items_for_receipt(receipt_id)

    max_len = max(len(gt_items), len(pred_items))
    rows = []

    for index in range(max_len):
        gt_item = gt_items[index] if index < len(gt_items) else {}
        pred_item = pred_items[index] if index < len(pred_items) else None

        pred_name = pred_item.name if pred_item else ""
        pred_quantity = pred_item.quantity if pred_item else None
        pred_unit_price = pred_item.unit_price if pred_item else None
        pred_line_total = pred_item.line_total if pred_item else None

        name_score = text_similarity(gt_item.get("name", ""), pred_name)

        rows.append(
            {
                "receipt_id": receipt_id,
                "item_index": index + 1,
                "gt_name": gt_item.get("name", ""),
                "pred_name": pred_name,
                "name_score": name_score,
                "name_ok": int(name_score >= 0.75),
                "gt_quantity": gt_item.get("quantity", ""),
                "pred_quantity": pred_quantity if pred_quantity is not None else "",
                "quantity_ok": int(number_equal(gt_item.get("quantity"), pred_quantity)),
                "gt_unit_price": gt_item.get("unit_price", ""),
                "pred_unit_price": pred_unit_price if pred_unit_price is not None else "",
                "unit_price_ok": int(number_equal(gt_item.get("unit_price"), pred_unit_price)),
                "gt_line_total": gt_item.get("line_total", ""),
                "pred_line_total": pred_line_total if pred_line_total is not None else "",
                "line_total_ok": int(number_equal(gt_item.get("line_total"), pred_line_total)),
                "gt_items_count": len(gt_items),
                "pred_items_count": len(pred_items),
                "items_count_ok": int(len(gt_items) == len(pred_items)),
                "strategy": pred_item.strategy if pred_item else "",
                "source_row_id": pred_item.source_row_id if pred_item else "",
                "value_row_id": pred_item.value_row_id if pred_item else "",
            }
        )

    return rows


def find_receipt_ids() -> list[str]:
    return [
        path.stem.replace("_layout_lines", "")
        for path in sorted(LAYOUT_DEBUG_DIR.glob("receipt_*_layout_lines.csv"))
    ]


def dataframe_to_markdown(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    table_rows = []

    for row in rows:
        values = []

        for column in columns:
            value = str(row.get(column, ""))
            value = value.replace("|", "\\|")
            values.append(value)

        table_rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator, *table_rows])


def build_summary(report_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not report_rows:
        return {}

    receipt_ids = sorted(set(row["receipt_id"] for row in report_rows))

    receipt_level = []

    for receipt_id in receipt_ids:
        receipt_rows = [row for row in report_rows if row["receipt_id"] == receipt_id]
        first_row = receipt_rows[0]

        receipt_level.append(
            {
                "receipt_id": receipt_id,
                "gt_items_count": int(first_row["gt_items_count"]),
                "pred_items_count": int(first_row["pred_items_count"]),
                "items_count_ok": int(first_row["items_count_ok"]),
            }
        )

    gt_rows = [row for row in report_rows if row["gt_name"]]

    def mean_int(field: str, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0

        return round(sum(int(row[field]) for row in rows) / len(rows), 4)

    field_accuracies = {
        "name_accuracy": mean_int("name_ok", gt_rows),
        "quantity_accuracy": mean_int("quantity_ok", gt_rows),
        "unit_price_accuracy": mean_int("unit_price_ok", gt_rows),
        "line_total_accuracy": mean_int("line_total_ok", gt_rows),
    }

    overall_item_field_accuracy = round(
        sum(field_accuracies.values()) / len(field_accuracies),
        4,
    )

    return {
        "num_receipts": len(receipt_ids),
        "total_gt_items": sum(row["gt_items_count"] for row in receipt_level),
        "total_pred_items": sum(row["pred_items_count"] for row in receipt_level),
        "items_count_accuracy": mean_int("items_count_ok", receipt_level),
        "field_accuracies": field_accuracies,
        "overall_item_field_accuracy": overall_item_field_accuracy,
        "receipts_with_count_errors": [
            row["receipt_id"]
            for row in receipt_level
            if int(row["items_count_ok"]) == 0
        ],
    }


def build_markdown_report(report_rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    count_error_rows = [
        {
            "receipt_id": row["receipt_id"],
            "gt_items_count": row["gt_items_count"],
            "pred_items_count": row["pred_items_count"],
        }
        for row in report_rows
        if int(row["items_count_ok"]) == 0 and int(row["item_index"]) == 1
    ]

    failed_rows = [
        row
        for row in report_rows
        if row["gt_name"]
        and (
            int(row["name_ok"]) == 0
            or int(row["quantity_ok"]) == 0
            or int(row["unit_price_ok"]) == 0
            or int(row["line_total_ok"]) == 0
        )
    ]

    lines = []

    lines.append("# Layout-aware Item Parser Experiment")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "Evaluate an experimental item parser that uses OCR layout rows generated from PaddleOCR bounding boxes."
    )
    lines.append("")
    lines.append("This experiment does not replace the main `rule_based_v0.3` parser.")
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

    lines.append(dataframe_to_markdown(field_rows, ["field", "accuracy"]))
    lines.append("")
    lines.append("## Receipts with Item Count Errors")
    lines.append("")
    lines.append(dataframe_to_markdown(count_error_rows, ["receipt_id", "gt_items_count", "pred_items_count"]))
    lines.append("")
    lines.append("## Failed Rows")
    lines.append("")

    failed_columns = [
        "receipt_id",
        "item_index",
        "gt_name",
        "pred_name",
        "name_score",
        "gt_quantity",
        "pred_quantity",
        "gt_unit_price",
        "pred_unit_price",
        "gt_line_total",
        "pred_line_total",
        "strategy",
        "source_row_id",
        "value_row_id",
    ]

    lines.append(dataframe_to_markdown(failed_rows[:80], failed_columns))
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This is an experimental parser based on layout rows, not raw OCR text order.")
    lines.append("- It is expected to perform better on name/value row pairs.")
    lines.append("- It may still fail on highly irregular rows, merged cells, promotion rows, or OCR value corruption.")
    lines.append("- The main parser remains `rule_based_v0.3` until this experiment outperforms it consistently.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    LAYOUT_ITEM_ANALYSIS_MD.parent.mkdir(parents=True, exist_ok=True)

    receipt_ids = find_receipt_ids()

    if not receipt_ids:
        raise FileNotFoundError(f"No layout CSV files found in {LAYOUT_DEBUG_DIR}")

    report_rows: list[dict[str, Any]] = []

    for receipt_id in receipt_ids:
        report_rows.extend(evaluate_receipt(receipt_id))

    summary = build_summary(report_rows)

    with LAYOUT_ITEM_REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        fieldnames = list(report_rows[0].keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    LAYOUT_ITEM_SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    LAYOUT_ITEM_ANALYSIS_MD.write_text(
        build_markdown_report(report_rows, summary),
        encoding="utf-8",
    )

    print("Layout-aware item parser experiment completed.")
    print(f"- {LAYOUT_ITEM_REPORT_CSV}")
    print(f"- {LAYOUT_ITEM_SUMMARY_JSON}")
    print(f"- {LAYOUT_ITEM_ANALYSIS_MD}")
    print("")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()