from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import DATABASE_PATH
from receipt_ocr.database import init_database


def main() -> None:
    init_database(DATABASE_PATH)
    print(f"Initialized database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()