from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.config import OCR_OUTPUT_DIR, RAW_RECEIPT_DIR, EVALUATION_DIR


LAYOUT_DEBUG_DIR = EVALUATION_DIR / "layout_debug"


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def find_image_path(receipt_id: str) -> Path:
    candidates = []

    for extension in ["png", "jpg", "jpeg"]:
        candidates.extend(RAW_RECEIPT_DIR.glob(f"{receipt_id}.{extension}"))

    if not candidates:
        raise FileNotFoundError(
            f"Image not found for {receipt_id} in {RAW_RECEIPT_DIR}"
        )

    return candidates[0]


def normalize_box(box: Any) -> list[list[float]] | None:
    """
    Normalize OCR box to 4 points:
        [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]

    Supports:
        - PaddleOCR polygon boxes
        - [x_min, y_min, x_max, y_max]
    """
    if box is None:
        return None

    if isinstance(box, list) and len(box) == 4:
        if all(isinstance(point, list | tuple) and len(point) >= 2 for point in box):
            return [[float(point[0]), float(point[1])] for point in box]

        if all(isinstance(value, int | float) for value in box):
            x_min, y_min, x_max, y_max = [float(value) for value in box]

            return [
                [x_min, y_min],
                [x_max, y_min],
                [x_max, y_max],
                [x_min, y_max],
            ]

    return None


def box_stats(box: list[list[float]]) -> dict[str, float]:
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    return {
        "x_min": round(x_min, 2),
        "x_max": round(x_max, 2),
        "y_min": round(y_min, 2),
        "y_max": round(y_max, 2),
        "x_center": round((x_min + x_max) / 2, 2),
        "y_center": round((y_min + y_max) / 2, 2),
        "width": round(x_max - x_min, 2),
        "height": round(y_max - y_min, 2),
    }


def extract_records_from_dict(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Support custom JSON formats such as:
        {"lines": [...]}
        {"ocr_lines": [...]}
        {"results": [...]}
    """
    for key in ["lines", "ocr_lines", "results", "data"]:
        value = payload.get(key)

        if isinstance(value, list):
            return extract_records(value)

    return []


def extract_record_from_paddle_entry(entry: Any) -> dict[str, Any] | None:
    """
    Support common PaddleOCR output:
        [box, (text, confidence)]
        [box, [text, confidence]]
    """
    if not isinstance(entry, list | tuple) or len(entry) < 2:
        return None

    box = normalize_box(entry[0])
    text_payload = entry[1]

    if box is None:
        return None

    text = None
    confidence = None

    if isinstance(text_payload, list | tuple) and len(text_payload) >= 2:
        text = str(text_payload[0])
        confidence = float(text_payload[1])
    elif isinstance(text_payload, str):
        text = text_payload

    if not text:
        return None

    stats = box_stats(box)

    return {
        "text": text,
        "confidence": confidence,
        "box": box,
        **stats,
    }


def extract_record_from_dict(entry: dict[str, Any]) -> dict[str, Any] | None:
    text = (
        entry.get("text")
        or entry.get("transcription")
        or entry.get("label")
        or entry.get("value")
    )

    if not text:
        return None

    box = (
        entry.get("box")
        or entry.get("bbox")
        or entry.get("points")
        or entry.get("poly")
    )

    normalized_box = normalize_box(box)

    if normalized_box is None:
        # Fallback for OCR text-only JSON.
        return {
            "text": str(text),
            "confidence": entry.get("confidence") or entry.get("score"),
            "box": None,
            "x_min": None,
            "x_max": None,
            "y_min": None,
            "y_max": None,
            "x_center": None,
            "y_center": None,
            "width": None,
            "height": None,
        }

    stats = box_stats(normalized_box)

    return {
        "text": str(text),
        "confidence": entry.get("confidence") or entry.get("score"),
        "box": normalized_box,
        **stats,
    }


def extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return extract_records_from_dict(payload)

    if not isinstance(payload, list):
        return []

    records = []

    for entry in payload:
        record = None

        if isinstance(entry, dict):
            record = extract_record_from_dict(entry)
        else:
            record = extract_record_from_paddle_entry(entry)

        if record is not None:
            records.append(record)

    records = [
        record
        for record in records
        if record.get("text") is not None and str(record.get("text")).strip()
    ]

    return records


def assign_rows(records: list[dict[str, Any]], y_tolerance: float = 12.0) -> list[dict[str, Any]]:
    """
    Group OCR boxes into visual rows using y_center.
    """
    boxed_records = [record for record in records if record.get("y_center") is not None]
    unboxed_records = [record for record in records if record.get("y_center") is None]

    boxed_records = sorted(
        boxed_records,
        key=lambda record: (float(record["y_center"]), float(record["x_min"])),
    )

    row_centers: list[float] = []
    grouped_records: list[dict[str, Any]] = []

    for record in boxed_records:
        y_center = float(record["y_center"])

        assigned_row = None

        for row_index, row_center in enumerate(row_centers):
            if abs(y_center - row_center) <= y_tolerance:
                assigned_row = row_index + 1
                row_centers[row_index] = (row_center + y_center) / 2
                break

        if assigned_row is None:
            row_centers.append(y_center)
            assigned_row = len(row_centers)

        record = record.copy()
        record["row_id"] = assigned_row
        grouped_records.append(record)

    grouped_records = sorted(
        grouped_records,
        key=lambda record: (
            int(record.get("row_id", 9999)),
            float(record.get("x_min") or 0),
        ),
    )

    for index, record in enumerate(grouped_records, start=1):
        record["reading_order"] = index

    for record in unboxed_records:
        record = record.copy()
        record["row_id"] = None
        record["reading_order"] = None
        grouped_records.append(record)

    return grouped_records


def write_layout_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "reading_order",
        "row_id",
        "text",
        "confidence",
        "x_min",
        "y_min",
        "x_max",
        "y_max",
        "x_center",
        "y_center",
        "width",
        "height",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow(
                {
                    key: record.get(key)
                    for key in fieldnames
                }
            )


def annotate_image(
    image_path: Path,
    records: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    for record in records:
        box = record.get("box")

        if not box:
            continue

        points = [(float(x), float(y)) for x, y in box]
        draw.line(points + [points[0]], width=2)

        label = f"{record.get('row_id')}:{record.get('reading_order')}"
        x_min = float(record["x_min"])
        y_min = float(record["y_min"])

        draw.text((x_min, max(0, y_min - 16)), label, font=font)

    image.save(output_path)


def print_row_view(records: list[dict[str, Any]]) -> None:
    boxed_records = [record for record in records if record.get("row_id") is not None]

    rows: dict[int, list[dict[str, Any]]] = {}

    for record in boxed_records:
        row_id = int(record["row_id"])
        rows.setdefault(row_id, []).append(record)

    for row_id in sorted(rows):
        row_records = sorted(rows[row_id], key=lambda record: float(record.get("x_min") or 0))
        row_text = " | ".join(str(record["text"]) for record in row_records)
        print(f"{row_id:03d}: {row_text}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect PaddleOCR layout boxes for a receipt."
    )

    parser.add_argument(
        "--receipt-id",
        required=True,
        help="Receipt id, for example receipt_004.",
    )

    parser.add_argument(
        "--y-tolerance",
        type=float,
        default=12.0,
        help="Y-center tolerance for grouping boxes into rows.",
    )

    args = parser.parse_args()

    receipt_id = args.receipt_id

    ocr_json_path = OCR_OUTPUT_DIR / f"{receipt_id}_ocr.json"
    image_path = find_image_path(receipt_id)

    payload = load_json(ocr_json_path)
    records = extract_records(payload)

    if not records:
        raise ValueError(
            f"No OCR records extracted from {ocr_json_path}. "
            "Open the JSON and check its structure."
        )

    grouped_records = assign_rows(records, y_tolerance=args.y_tolerance)

    csv_path = LAYOUT_DEBUG_DIR / f"{receipt_id}_layout_lines.csv"
    annotated_path = LAYOUT_DEBUG_DIR / f"{receipt_id}_layout_annotated.png"

    write_layout_csv(grouped_records, csv_path)
    annotate_image(image_path, grouped_records, annotated_path)

    print(f"Receipt ID: {receipt_id}")
    print(f"OCR JSON : {ocr_json_path}")
    print(f"Image    : {image_path}")
    print(f"CSV      : {csv_path}")
    print(f"Annotated: {annotated_path}")
    print("")
    print("Grouped row view:")
    print("-" * 90)
    print_row_view(grouped_records)


if __name__ == "__main__":
    main()