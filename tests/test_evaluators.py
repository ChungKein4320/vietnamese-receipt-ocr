from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

from receipt_ocr import evaluator as receipt_evaluator
from scripts import evaluate_items, evaluate_layout_items


ITEM_EVALUATORS = [
    pytest.param(
        evaluate_items,
        "EXTRACTED_RESULT_DIR",
        "_extracted.json",
        id="text_parser",
    ),
    pytest.param(
        evaluate_layout_items,
        "LAYOUT_EXTRACTED_RESULT_DIR",
        "_layout_extracted.json",
        id="layout_parser",
    ),
]

ITEM_EVALUATOR_MODULES = [
    pytest.param(evaluate_items, id="text_parser"),
    pytest.param(evaluate_layout_items, id="layout_parser"),
]


def _write_payload(path: Path, items: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"receipt_id": "receipt_001", "items": items}),
        encoding="utf-8",
    )


def _configure_item_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: ModuleType,
    prediction_dir_attribute: str,
    prediction_suffix: str,
    ground_truth_items: list[dict[str, object]],
    predicted_items: list[dict[str, object]],
) -> None:
    ground_truth_dir = tmp_path / "ground_truth"
    prediction_dir = tmp_path / "predictions"

    monkeypatch.setattr(module, "GROUND_TRUTH_DIR", ground_truth_dir)
    monkeypatch.setattr(module, prediction_dir_attribute, prediction_dir)

    _write_payload(ground_truth_dir / "receipt_001.json", ground_truth_items)
    _write_payload(
        prediction_dir / f"receipt_001{prediction_suffix}",
        predicted_items,
    )


@pytest.mark.parametrize(
    ("module", "prediction_dir_attribute", "prediction_suffix"),
    ITEM_EVALUATORS,
)
def test_item_evaluator_matches_rows_by_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: ModuleType,
    prediction_dir_attribute: str,
    prediction_suffix: str,
) -> None:
    first_item = {
        "name": "Ca phe",
        "quantity": 1,
        "unit_price": 20_000,
        "line_total": 20_000,
    }
    second_item = {
        "name": "Banh mi",
        "quantity": 1,
        "unit_price": 15_000,
        "line_total": 15_000,
    }
    _configure_item_files(
        monkeypatch,
        tmp_path,
        module,
        prediction_dir_attribute,
        prediction_suffix,
        [first_item, second_item],
        [second_item, first_item],
    )

    rows = module.evaluate_receipt_items("receipt_001")

    assert [row["item_index"] for row in rows] == [1, 2]
    assert [row["name_ok"] for row in rows] == [0, 0]
    assert rows[0]["gt_name"] == "Ca phe"
    assert rows[0]["pred_name"] == "Banh mi"


@pytest.mark.parametrize(
    ("module", "prediction_dir_attribute", "prediction_suffix"),
    ITEM_EVALUATORS,
)
def test_item_name_threshold_is_inclusive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: ModuleType,
    prediction_dir_attribute: str,
    prediction_suffix: str,
) -> None:
    item = {
        "name": "ground truth",
        "quantity": 1,
        "unit_price": 10_000,
        "line_total": 10_000,
    }
    _configure_item_files(
        monkeypatch,
        tmp_path,
        module,
        prediction_dir_attribute,
        prediction_suffix,
        [item],
        [{**item, "name": "prediction"}],
    )

    monkeypatch.setattr(module, "text_similarity", lambda *_: 0.75)
    assert module.evaluate_receipt_items("receipt_001")[0]["name_ok"] == 1

    monkeypatch.setattr(module, "text_similarity", lambda *_: 0.7499)
    assert module.evaluate_receipt_items("receipt_001")[0]["name_ok"] == 0


@pytest.mark.parametrize(
    ("module", "prediction_dir_attribute", "prediction_suffix"),
    ITEM_EVALUATORS,
)
def test_missing_prediction_fails_all_item_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: ModuleType,
    prediction_dir_attribute: str,
    prediction_suffix: str,
) -> None:
    _configure_item_files(
        monkeypatch,
        tmp_path,
        module,
        prediction_dir_attribute,
        prediction_suffix,
        [
            {
                "name": "Sua tuoi",
                "quantity": 2,
                "unit_price": 8_000,
                "line_total": 16_000,
            }
        ],
        [],
    )

    row = module.evaluate_receipt_items("receipt_001")[0]

    assert row["pred_exists"] == 0
    assert row["items_count_ok"] == 0
    assert [
        row["name_ok"],
        row["quantity_ok"],
        row["unit_price_ok"],
        row["line_total_ok"],
    ] == [0, 0, 0, 0]


@pytest.mark.parametrize("module", ITEM_EVALUATOR_MODULES)
def test_number_normalization_supports_vietnamese_money_format(
    module: ModuleType,
) -> None:
    assert module.number_equal("95.000", 95_000)
    assert module.number_equal("1,5", 1.5)
    assert not module.number_equal("95.000", 9_500)
    assert module.number_equal(None, None)


@pytest.mark.parametrize("module", ITEM_EVALUATOR_MODULES)
def test_item_summary_uses_unweighted_field_mean(
    module: ModuleType,
) -> None:
    report = pd.DataFrame(
        [
            {
                "receipt_id": "receipt_001",
                "gt_exists": 1,
                "pred_exists": 1,
                "name_ok": 1,
                "quantity_ok": 1,
                "unit_price_ok": 1,
                "line_total_ok": 0,
                "gt_items_count": 1,
                "pred_items_count": 1,
                "items_count_ok": 1,
            },
            {
                "receipt_id": "receipt_002",
                "gt_exists": 1,
                "pred_exists": 0,
                "name_ok": 0,
                "quantity_ok": 0,
                "unit_price_ok": 0,
                "line_total_ok": 0,
                "gt_items_count": 1,
                "pred_items_count": 0,
                "items_count_ok": 0,
            },
        ]
    )

    summary = module.build_summary(report)

    assert summary["num_receipts"] == 2
    assert summary["total_gt_items"] == 2
    assert summary["total_pred_items"] == 1
    assert summary["items_count_accuracy"] == 0.5
    assert summary["field_accuracies"] == {
        "name_accuracy": 0.5,
        "quantity_accuracy": 0.5,
        "unit_price_accuracy": 0.5,
        "line_total_accuracy": 0.0,
    }
    assert summary["overall_item_field_accuracy"] == 0.375


def test_receipt_field_similarity_thresholds_are_inclusive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(receipt_evaluator, "string_similarity", lambda *_: 0.75)
    assert receipt_evaluator.compare_store_name("expected", "predicted")[0]

    monkeypatch.setattr(receipt_evaluator, "string_similarity", lambda *_: 0.85)
    assert receipt_evaluator.compare_invoice_id("expected", "predicted")[0]


def test_receipt_datetime_accepts_date_only_match() -> None:
    is_correct, score = receipt_evaluator.compare_datetime(
        "2026-07-14 09:30",
        "2026-07-14",
    )

    assert is_correct
    assert score == 0.8


def test_receipt_summary_averages_all_six_fields() -> None:
    summary = receipt_evaluator.summarize_evaluation(
        [
            {
                "store_name_ok": 1,
                "datetime_ok": 1,
                "invoice_id_ok": 1,
                "total_amount_ok": 1,
                "payment_method_ok": 1,
                "items_count_ok": 0,
            }
        ]
    )

    assert summary["num_receipts"] == 1
    assert summary["overall_accuracy"] == 0.8333
    assert summary["field_accuracy"]["items_count"] == 0.0
