from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from receipt_ocr.config import OCR_OUTPUT_DIR


@lru_cache(maxsize=2)
def get_ocr_engine(lang: str = "en"):
    """
    Create and cache a PaddleOCR engine.

    MVP baseline uses lang="en" because many Vietnamese receipts contain:
    - Latin characters
    - numbers
    - product names
    - prices
    - invoice codes

    Vietnamese accents may not always be recognized correctly in this baseline.
    """
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_angle_cls=True,
        lang=lang,
        show_log=False,
    )


def _is_ocr_line(obj: Any) -> bool:
    """
    PaddleOCR v2 line format is usually:
        [box, (text, confidence)]
    """
    if not isinstance(obj, list):
        return False

    if len(obj) != 2:
        return False

    text_score = obj[1]

    if not isinstance(text_score, (tuple, list)):
        return False

    if len(text_score) != 2:
        return False

    return True


def _flatten_paddle_result(raw_result: Any) -> list[Any]:
    """
    Normalize PaddleOCR output into a list of OCR lines.

    Depending on PaddleOCR version and input type, result may look like:
        [[line1, line2, ...]]
    or:
        [line1, line2, ...]
    """
    if raw_result is None:
        return []

    if not isinstance(raw_result, list) or len(raw_result) == 0:
        return []

    if _is_ocr_line(raw_result[0]):
        return raw_result

    if len(raw_result) == 1 and isinstance(raw_result[0], list):
        page_result = raw_result[0]
        if len(page_result) > 0 and _is_ocr_line(page_result[0]):
            return page_result

    lines = []

    for page in raw_result:
        if isinstance(page, list):
            for line in page:
                if _is_ocr_line(line):
                    lines.append(line)

    return lines


def _to_serializable_box(box: Any) -> list[list[float]]:
    """
    Convert OCR bounding box points to JSON-serializable format.
    """
    serializable_box = []

    for point in box:
        serializable_box.append([float(point[0]), float(point[1])])

    return serializable_box


def run_ocr(image_path: str | Path, lang: str = "en") -> list[dict[str, Any]]:
    """
    Run OCR on one image and return normalized OCR lines.

    Returns:
        [
            {
                "text": "...",
                "confidence": 0.98,
                "box": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
            }
        ]
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    ocr = get_ocr_engine(lang=lang)
    raw_result = ocr.ocr(str(image_path), cls=True)
    raw_lines = _flatten_paddle_result(raw_result)

    normalized_lines = []

    for line in raw_lines:
        box = line[0]
        text = str(line[1][0]).strip()
        confidence = float(line[1][1])

        if text:
            normalized_lines.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "box": _to_serializable_box(box),
                }
            )

    return normalized_lines


def ocr_lines_to_text(lines: list[dict[str, Any]]) -> str:
    """
    Convert OCR line dictionaries to plain text.
    """
    return "\n".join(line["text"] for line in lines)


def save_ocr_outputs(
    image_path: str | Path,
    lines: list[dict[str, Any]],
) -> tuple[Path, Path]:
    """
    Save OCR output as both TXT and JSON.

    Output examples:
        data/ocr_outputs/receipt_001_ocr.txt
        data/ocr_outputs/receipt_001_ocr.json
    """
    image_path = Path(image_path)
    OCR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem

    txt_path = OCR_OUTPUT_DIR / f"{stem}_ocr.txt"
    json_path = OCR_OUTPUT_DIR / f"{stem}_ocr.json"

    txt_path.write_text(
        ocr_lines_to_text(lines),
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(
            {
                "image_path": str(image_path).replace("\\", "/"),
                "num_lines": len(lines),
                "lines": lines,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return txt_path, json_path