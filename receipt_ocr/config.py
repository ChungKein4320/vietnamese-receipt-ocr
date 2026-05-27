from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_RECEIPT_DIR = DATA_DIR / "raw" / "receipts"
PROCESSED_IMAGE_DIR = DATA_DIR / "processed" / "images"
OCR_OUTPUT_DIR = DATA_DIR / "ocr_outputs"
EXTRACTED_RESULT_DIR = DATA_DIR / "extracted_results"

DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "receipts.db"