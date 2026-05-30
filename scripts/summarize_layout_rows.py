from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYOUT_DEBUG_DIR = PROJECT_ROOT / "data" / "evaluation" / "layout_debug"
OUTPUT_PATH = LAYOUT_DEBUG_DIR / "layout_row_summary.txt"


def read_layout_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def group_rows(records: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}

    for record in records:
        row_id = record.get("row_id") or "NA"
        grouped.setdefault(row_id, []).append(record)

    return grouped


def row_sort_key(row_id: str) -> int:
    try:
        return int(row_id)
    except ValueError:
        return 9999


def summarize_file(path: Path) -> list[str]:
    receipt_id = path.stem.replace("_layout_lines", "")
    records = read_layout_csv(path)
    grouped = group_rows(records)

    lines = []
    lines.append("=" * 100)
    lines.append(receipt_id)
    lines.append("=" * 100)

    for row_id in sorted(grouped, key=row_sort_key):
        row_records = grouped[row_id]

        row_records = sorted(
            row_records,
            key=lambda record: float(record.get("x_min") or 0),
        )

        row_text = " | ".join(record.get("text", "") for record in row_records)
        lines.append(f"{int(row_id):03d}: {row_text}" if row_id != "NA" else f"NA : {row_text}")

    lines.append("")

    return lines


def main() -> None:
    csv_paths = sorted(LAYOUT_DEBUG_DIR.glob("receipt_*_layout_lines.csv"))

    if not csv_paths:
        raise FileNotFoundError(f"No layout CSV files found in: {LAYOUT_DEBUG_DIR}")

    all_lines = []

    for path in csv_paths:
        all_lines.extend(summarize_file(path))

    OUTPUT_PATH.write_text("\n".join(all_lines), encoding="utf-8")

    print(f"Saved layout row summary: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()