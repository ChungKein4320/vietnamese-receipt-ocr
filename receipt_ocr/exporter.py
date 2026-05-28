from __future__ import annotations

from pathlib import Path

import pandas as pd

from receipt_ocr.config import DATABASE_PATH, EXTRACTED_RESULT_DIR
from receipt_ocr.database import fetch_all_items, fetch_all_receipts


def export_receipts_csv(
    output_path: str | Path | None = None,
    db_path: str | Path = DATABASE_PATH,
) -> Path:
    """
    Export saved receipt-level records to CSV.
    """
    if output_path is None:
        output_path = EXTRACTED_RESULT_DIR / "receipts_export.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = fetch_all_receipts(db_path)
    dataframe = pd.DataFrame(rows)

    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def export_items_csv(
    output_path: str | Path | None = None,
    db_path: str | Path = DATABASE_PATH,
) -> Path:
    """
    Export saved item-level records to CSV.
    """
    if output_path is None:
        output_path = EXTRACTED_RESULT_DIR / "items_export.csv"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = fetch_all_items(db_path)
    dataframe = pd.DataFrame(rows)

    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path