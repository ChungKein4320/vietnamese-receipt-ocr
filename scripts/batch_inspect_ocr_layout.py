from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCR_OUTPUT_DIR = PROJECT_ROOT / "data" / "ocr_outputs"


def find_receipt_ids() -> list[str]:
    receipt_ids = []

    for path in sorted(OCR_OUTPUT_DIR.glob("receipt_*_ocr.json")):
        receipt_id = path.stem.replace("_ocr", "")
        receipt_ids.append(receipt_id)

    return receipt_ids


def main() -> None:
    receipt_ids = find_receipt_ids()

    if not receipt_ids:
        raise FileNotFoundError(f"No OCR JSON files found in: {OCR_OUTPUT_DIR}")

    print(f"Found {len(receipt_ids)} OCR JSON files.")

    for receipt_id in receipt_ids:
        print(f"\nInspecting layout: {receipt_id}")

        subprocess.run(
            [
                sys.executable,
                "scripts/inspect_ocr_layout.py",
                "--receipt-id",
                receipt_id,
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )

    print("\nBatch layout inspection completed.")
    print("Generated files under:")
    print("data/evaluation/layout_debug/")


if __name__ == "__main__":
    main()