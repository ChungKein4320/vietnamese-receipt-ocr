from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.exporter import export_items_csv, export_receipts_csv


def main() -> None:
    receipts_path = export_receipts_csv()
    items_path = export_items_csv()

    print(f"Exported receipts CSV: {receipts_path}")
    print(f"Exported items CSV   : {items_path}")


if __name__ == "__main__":
    main()