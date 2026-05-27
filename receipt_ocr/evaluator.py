from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from receipt_ocr.text_normalizer import strip_vietnamese_accents


EVALUATED_FIELDS = [
    "store_name",
    "datetime",
    "invoice_id",
    "total_amount",
    "payment_method",
    "items_count",
]


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_string(value: Any) -> str | None:
    """
    Normalize a string for comparison.

    This removes accents, uppercases text, and collapses non-alphanumeric characters.
    """
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = strip_vietnamese_accents(text)
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_code(value: Any) -> str | None:
    """
    Normalize invoice/code-like values.
    """
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = strip_vietnamese_accents(text)
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)

    return text or None


def normalize_int(value: Any) -> int | None:
    """
    Normalize money/count-like values to int.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    text = str(value).strip()

    if not text:
        return None

    digits = re.sub(r"[^\d]", "", text)

    if not digits:
        return None

    return int(digits)


def string_similarity(left: str | None, right: str | None) -> float:
    if left is None or right is None:
        return 0.0

    return SequenceMatcher(None, left, right).ratio()


def compare_store_name(expected: Any, predicted: Any) -> tuple[bool, float]:
    """
    Store names can differ slightly because OCR may miss accents or characters.

    Example:
        "VinCommerce" vs "VinComnerce"
    """
    expected_norm = normalize_string(expected)
    predicted_norm = normalize_string(predicted)

    score = string_similarity(expected_norm, predicted_norm)

    return score >= 0.75, score


def compare_datetime(expected: Any, predicted: Any) -> tuple[bool, float]:
    """
    Datetime is considered correct if:
    - exact normalized match, or
    - predicted date matches expected date when expected has time but OCR/parser only found date.
    """
    expected_norm = str(expected).strip() if expected is not None else None
    predicted_norm = str(predicted).strip() if predicted is not None else None

    if not expected_norm and not predicted_norm:
        return True, 1.0

    if not expected_norm or not predicted_norm:
        return False, 0.0

    if expected_norm == predicted_norm:
        return True, 1.0

    expected_date = expected_norm[:10]
    predicted_date = predicted_norm[:10]

    if expected_date == predicted_date:
        return True, 0.8

    return False, 0.0


def compare_invoice_id(expected: Any, predicted: Any) -> tuple[bool, float]:
    expected_norm = normalize_code(expected)
    predicted_norm = normalize_code(predicted)

    if not expected_norm and not predicted_norm:
        return True, 1.0

    if not expected_norm or not predicted_norm:
        return False, 0.0

    if expected_norm == predicted_norm:
        return True, 1.0

    score = string_similarity(expected_norm, predicted_norm)
    return score >= 0.85, score


def compare_total_amount(expected: Any, predicted: Any) -> tuple[bool, float]:
    expected_int = normalize_int(expected)
    predicted_int = normalize_int(predicted)

    if expected_int is None and predicted_int is None:
        return True, 1.0

    if expected_int is None or predicted_int is None:
        return False, 0.0

    return expected_int == predicted_int, 1.0 if expected_int == predicted_int else 0.0


def compare_payment_method(expected: Any, predicted: Any) -> tuple[bool, float]:
    expected_norm = normalize_string(expected)
    predicted_norm = normalize_string(predicted)

    if expected_norm is None:
        expected_norm = "UNKNOWN"

    if predicted_norm is None:
        predicted_norm = "UNKNOWN"

    return expected_norm == predicted_norm, 1.0 if expected_norm == predicted_norm else 0.0


def compare_items_count(expected_items: Any, predicted_items: Any) -> tuple[bool, float]:
    expected_count = len(expected_items) if isinstance(expected_items, list) else 0
    predicted_count = len(predicted_items) if isinstance(predicted_items, list) else 0

    if expected_count == predicted_count:
        return True, 1.0

    if expected_count == 0:
        return False, 0.0

    score = max(0.0, 1.0 - abs(expected_count - predicted_count) / expected_count)
    return False, score


def evaluate_single_receipt(
    ground_truth: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    receipt_id = ground_truth.get("receipt_id") or prediction.get("receipt_id")

    store_ok, store_score = compare_store_name(
        ground_truth.get("store_name"),
        prediction.get("store_name"),
    )

    datetime_ok, datetime_score = compare_datetime(
        ground_truth.get("datetime"),
        prediction.get("datetime"),
    )

    invoice_ok, invoice_score = compare_invoice_id(
        ground_truth.get("invoice_id"),
        prediction.get("invoice_id"),
    )

    total_ok, total_score = compare_total_amount(
        ground_truth.get("total_amount"),
        prediction.get("total_amount"),
    )

    payment_ok, payment_score = compare_payment_method(
        ground_truth.get("payment_method"),
        prediction.get("payment_method"),
    )

    items_count_ok, items_count_score = compare_items_count(
        ground_truth.get("items"),
        prediction.get("items"),
    )

    return {
        "receipt_id": receipt_id,
        "store_name_ok": int(store_ok),
        "store_name_score": round(store_score, 3),
        "store_name_gt": ground_truth.get("store_name"),
        "store_name_pred": prediction.get("store_name"),
        "datetime_ok": int(datetime_ok),
        "datetime_score": round(datetime_score, 3),
        "datetime_gt": ground_truth.get("datetime"),
        "datetime_pred": prediction.get("datetime"),
        "invoice_id_ok": int(invoice_ok),
        "invoice_id_score": round(invoice_score, 3),
        "invoice_id_gt": ground_truth.get("invoice_id"),
        "invoice_id_pred": prediction.get("invoice_id"),
        "total_amount_ok": int(total_ok),
        "total_amount_score": round(total_score, 3),
        "total_amount_gt": ground_truth.get("total_amount"),
        "total_amount_pred": prediction.get("total_amount"),
        "payment_method_ok": int(payment_ok),
        "payment_method_score": round(payment_score, 3),
        "payment_method_gt": ground_truth.get("payment_method"),
        "payment_method_pred": prediction.get("payment_method"),
        "items_count_ok": int(items_count_ok),
        "items_count_score": round(items_count_score, 3),
        "items_count_gt": len(ground_truth.get("items", [])),
        "items_count_pred": len(prediction.get("items", [])),
        "prediction_warnings": "|".join(prediction.get("warnings", [])),
    }


def summarize_evaluation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "num_receipts": 0,
            "field_accuracy": {},
        }

    field_accuracy = {}

    for field in EVALUATED_FIELDS:
        ok_key = f"{field}_ok"
        values = [row[ok_key] for row in rows if ok_key in row]

        if not values:
            field_accuracy[field] = None
            continue

        field_accuracy[field] = round(sum(values) / len(values), 4)

    overall_values = []

    for row in rows:
        for field in EVALUATED_FIELDS:
            ok_key = f"{field}_ok"
            if ok_key in row:
                overall_values.append(row[ok_key])

    overall_accuracy = (
        round(sum(overall_values) / len(overall_values), 4)
        if overall_values
        else None
    )

    return {
        "num_receipts": len(rows),
        "fields": EVALUATED_FIELDS,
        "field_accuracy": field_accuracy,
        "overall_accuracy": overall_accuracy,
    }