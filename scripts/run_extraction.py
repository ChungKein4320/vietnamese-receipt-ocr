from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import OCR_OUTPUT_DIR
from receipt_ocr.receipt_parser import parse_receipt_text, save_extraction_result


def collect_ocr_text_files() -> list[Path]:
    """
    Collect all OCR TXT files from data/ocr_outputs/.
    """
    return sorted(OCR_OUTPUT_DIR.glob("*_ocr.txt"))


def get_receipt_id_from_ocr_path(ocr_text_path: Path) -> str:
    """
    Convert:
        receipt_001_ocr.txt -> receipt_001
    """
    return ocr_text_path.stem.replace("_ocr", "")


def run_single_extraction(ocr_text_path: Path) -> None:
    """
    Parse one OCR TXT file and save structured JSON output.
    """
    if not ocr_text_path.exists():
        raise FileNotFoundError(f"OCR text file not found: {ocr_text_path}")

    receipt_id = get_receipt_id_from_ocr_path(ocr_text_path)
    text = ocr_text_path.read_text(encoding="utf-8")

    result = parse_receipt_text(
        receipt_id=receipt_id,
        text=text,
        source_ocr_path=ocr_text_path,
    )

    output_path = save_extraction_result(result)

    print(f"\nParsed: {ocr_text_path}")
    print(f"Saved : {output_path}")
    print("-" * 60)
    print(f"receipt_id     : {result.receipt_id}")
    print(f"store_name     : {result.store_name}")
    print(f"datetime       : {result.datetime}")
    print(f"invoice_id     : {result.invoice_id}")
    print(f"items_count    : {len(result.items)}")
    print(f"total_amount   : {result.total_amount}")
    print(f"payment_method : {result.payment_method}")
    print(f"warnings       : {result.warnings}")
    print("-" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run rule-based information extraction on OCR text files."
    )

    parser.add_argument(
        "--ocr-text",
        type=str,
        default=None,
        help="Path to one OCR TXT file.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run extraction on all *_ocr.txt files in data/ocr_outputs/.",
    )

    args = parser.parse_args()

    if args.ocr_text is None and not args.all:
        raise ValueError("Please provide --ocr-text or use --all.")

    if args.ocr_text is not None and args.all:
        raise ValueError("Use either --ocr-text or --all, not both.")

    if args.ocr_text is not None:
        run_single_extraction(Path(args.ocr_text))
        return

    ocr_text_files = collect_ocr_text_files()

    if not ocr_text_files:
        raise FileNotFoundError(f"No OCR text files found in {OCR_OUTPUT_DIR}")

    print(f"Found {len(ocr_text_files)} OCR text files.")

    for ocr_text_path in ocr_text_files:
        run_single_extraction(ocr_text_path)


if __name__ == "__main__":
    main()