from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import RAW_RECEIPT_DIR
from receipt_ocr.ocr_engine import ocr_lines_to_text, run_ocr, save_ocr_outputs


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def collect_images() -> list[Path]:
    """
    Collect all supported receipt images from data/raw/receipts/.
    """
    images = []

    for path in RAW_RECEIPT_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            images.append(path)

    return sorted(images)


def run_single_image(image_path: Path, lang: str) -> None:
    """
    Run OCR on one image and save TXT/JSON outputs.
    """
    print(f"\nRunning OCR: {image_path}")

    lines = run_ocr(image_path=image_path, lang=lang)
    txt_path, json_path = save_ocr_outputs(image_path=image_path, lines=lines)

    print(f"Detected lines: {len(lines)}")
    print(f"Saved TXT : {txt_path}")
    print(f"Saved JSON: {json_path}")

    print("\nOCR preview:")
    print("-" * 60)
    preview = ocr_lines_to_text(lines)
    print(preview[:1500])
    print("-" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run PaddleOCR baseline on receipt images."
    )

    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to one receipt image.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run OCR on all images in data/raw/receipts/.",
    )

    parser.add_argument(
        "--lang",
        type=str,
        default="en",
        help="PaddleOCR language code. Default: en.",
    )

    args = parser.parse_args()

    if args.image is None and not args.all:
        raise ValueError("Please provide --image or use --all.")

    if args.image is not None and args.all:
        raise ValueError("Use either --image or --all, not both.")

    if args.image is not None:
        run_single_image(Path(args.image), lang=args.lang)
        return

    images = collect_images()

    if not images:
        raise FileNotFoundError(f"No images found in {RAW_RECEIPT_DIR}")

    print(f"Found {len(images)} images.")

    for image_path in images:
        run_single_image(image_path=image_path, lang=args.lang)


if __name__ == "__main__":
    main()