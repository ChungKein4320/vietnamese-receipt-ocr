from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from receipt_ocr.config import DATABASE_PATH, EXTRACTED_RESULT_DIR
from receipt_ocr.database import fetch_all_items, fetch_all_receipts


ITEM_CSV_COLUMNS = ("name", "quantity", "unit_price", "line_total")
SAVED_ITEM_CSV_COLUMNS = ("receipt_id", "store_name", "datetime", "item_index", *ITEM_CSV_COLUMNS)
RECEIPT_CSV_COLUMNS = (
    "id", "receipt_id", "store_name", "datetime", "invoice_id", "total_amount",
    "payment_method", "num_ocr_lines", "parser_version", "created_at", "updated_at",
)


def records_to_csv_bytes(rows: list[dict], columns: tuple[str, ...]) -> bytes:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def export_receipts_csv(
    output_path: str | Path | None = None,
    db_path: str | Path = DATABASE_PATH,
) -> Path:
    """Export saved receipt-level records to CSV."""
    if output_path is None:
        output_path = EXTRACTED_RESULT_DIR / "receipts_export.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(
        records_to_csv_bytes(fetch_all_receipts(db_path), RECEIPT_CSV_COLUMNS)
    )
    return output_path


def export_items_csv(
    output_path: str | Path | None = None,
    db_path: str | Path = DATABASE_PATH,
) -> Path:
    """Export saved item-level records to CSV."""
    if output_path is None:
        output_path = EXTRACTED_RESULT_DIR / "items_export.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(
        records_to_csv_bytes(fetch_all_items(db_path), SAVED_ITEM_CSV_COLUMNS)
    )
    return output_path
