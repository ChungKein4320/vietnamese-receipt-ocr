from __future__ import annotations

import csv
import io
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.streamlit_app import apply_layout_aware_items, decode_upload, result_to_json_bytes
from receipt_ocr import ocr_engine
from receipt_ocr.database import fetch_items_for_receipt, save_extraction_to_db
from receipt_ocr.exporter import ITEM_CSV_COLUMNS, export_items_csv, export_receipts_csv, records_to_csv_bytes
from receipt_ocr.layout_item_parser import LayoutParsedItem, normalize_layout_item_values
from receipt_ocr.receipt_parser import extract_items, parse_receipt_text


SAMPLE_IMAGE = Path(__file__).resolve().parents[1] / "data/sample/synthetic_receipt.png"


def test_ocr_decodes_a_unicode_path_and_flattens_a_two_line_page(monkeypatch, tmp_path):
    image_path = tmp_path / "hóa đơn.png"
    image_path.write_bytes(SAMPLE_IMAGE.read_bytes())
    box = [[0, 0], [30, 0], [30, 20], [0, 20]]
    detections = [[box, ("Cà phê", 0.95)], [box, ("20.000", 0.99)]]

    class Predictor:
        def ocr(self, image, *, cls):
            assert image.ndim == 3 and image.shape[2] == 3
            assert cls
            return [detections]

    monkeypatch.setattr(ocr_engine, "get_ocr_engine", lambda **_: Predictor())
    lines = ocr_engine.run_ocr(image_path)
    assert ocr_engine.ocr_lines_to_text(lines) == "Cà phê\n20.000"
    assert lines[0]["box"] == box
    assert lines[0]["confidence"] == 0.95


def test_invalid_image_is_rejected_before_loading_the_model(monkeypatch):
    def unexpected_engine(**kwargs):
        pytest.fail("An invalid image should be rejected before loading OCR")

    monkeypatch.setattr(ocr_engine, "get_ocr_engine", unexpected_engine)
    with pytest.raises(ValueError, match="decode"):
        ocr_engine.run_ocr(b"not a PNG")
    with pytest.raises(OSError):
        decode_upload(b"not a PNG")


def test_layout_keeps_explicit_fractional_quantity():
    item = LayoutParsedItem(
        receipt_id="test",
        name="Cà phê",
        quantity=0.5,
        unit_price=20_000,
        line_total=20_000,
        source_row_id=1,
        value_row_id=1,
        strategy="single_row",
    )
    assert normalize_layout_item_values(item).quantity == 0.5


def test_text_parser_keeps_both_prices_in_a_split_line():
    items = extract_items(["Cà phê", "20.000 40.000", "2"])
    assert len(items) == 1
    assert (items[0].quantity, items[0].unit_price, items[0].line_total) == (2, 20_000, 40_000)


def test_sqlite_upsert_replaces_items_and_rolls_back_on_error(tmp_path):
    db_path = tmp_path / "receipt.db"
    initial = {"receipt_id": "test", "items": [{"name": "Cà phê"}]}
    replacement = {"receipt_id": "test", "items": [{"name": "Bánh mì"}]}
    receipt_db_id = save_extraction_to_db(initial, db_path)
    assert save_extraction_to_db(replacement, db_path) == receipt_db_id

    with pytest.raises(sqlite3.IntegrityError):
        save_extraction_to_db(initial, db_path, replace=False)
    with pytest.raises(sqlite3.IntegrityError):
        save_extraction_to_db({"receipt_id": "test", "items": [{"name": None}]}, db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        raw_json, = connection.execute("SELECT raw_json FROM receipts").fetchone()
    assert json.loads(raw_json) == replacement
    assert [item["name"] for item in fetch_items_for_receipt(receipt_db_id, db_path)] == ["Bánh mì"]


def test_json_and_csv_preserve_unicode_and_nullable_prices(tmp_path):
    items = [
        {"name": "Cà phê, sữa", "quantity": 1.5, "unit_price": 20_000, "line_total": 30_000},
        {"name": "Bánh mì", "quantity": 1, "unit_price": None, "line_total": None},
    ]
    receipt = {"receipt_id": "test", "store_name": "Tiệm cà phê", "items": items}
    assert json.loads(result_to_json_bytes(receipt)) == receipt
    csv_bytes = records_to_csv_bytes(items, ITEM_CSV_COLUMNS)
    csv_rows = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    assert csv_rows[0] == {
        "name": items[0]["name"], "quantity": "1.5", "unit_price": "20000", "line_total": "30000",
    }
    assert csv_rows[1]["line_total"] == ""

    db_path = tmp_path / "receipt.db"
    save_extraction_to_db(receipt, db_path)
    items_csv = export_items_csv(tmp_path / "items.csv", db_path)
    receipts_csv = export_receipts_csv(tmp_path / "receipts.csv", db_path)
    with items_csv.open(encoding="utf-8-sig", newline="") as file:
        saved_items = list(csv.DictReader(file))
    with receipts_csv.open(encoding="utf-8-sig", newline="") as file:
        saved_receipt, = csv.DictReader(file)
    assert saved_items[0]["unit_price"] == "20000"
    assert saved_items[1]["unit_price"] == ""
    assert saved_receipt["store_name"] == receipt["store_name"]


def test_layout_fallback_keeps_text_items_and_reuses_ocr(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from app import streamlit_app as app

    ocr_path = SAMPLE_IMAGE.with_name(f"{SAMPLE_IMAGE.stem}_ocr.json")
    ocr_lines = json.loads(ocr_path.read_text(encoding="utf-8"))["lines"]
    state = {}
    calls = []

    def run_ocr(image_bytes, *, lang):
        calls.append(lang)
        return ocr_lines

    monkeypatch.setattr(app.st, "session_state", state)
    monkeypatch.setattr(app.st, "status", lambda *args, **kwargs: nullcontext(SimpleNamespace(update=lambda **_: None)))
    monkeypatch.setattr(app.st, "write", lambda *args: None)
    monkeypatch.setattr(app, "run_ocr", run_ocr)
    monkeypatch.setattr(app, "parse_layout_items_from_rows", lambda rows: [])

    app.reset_state_for_new_upload("sample", "en")
    app.run_pipeline(b"", "sample", "en", "text_based_v0.3")
    text_result = state["result_dict"]
    assert text_result["items"]

    app.reset_result_state()
    app.run_pipeline(b"", "sample", "en", "layout_aware_v0.4_candidate")
    fallback = state["result_dict"]
    assert calls == ["en"]
    assert fallback["items"] == text_result["items"]
    assert fallback["item_parser_version"] == "text_based_fallback"
    assert "layout_items_not_found" in fallback["warnings"]


def test_synthetic_sample_matches_both_saved_extractions():
    def read_sample_json(suffix):
        path = SAMPLE_IMAGE.with_name(f"{SAMPLE_IMAGE.stem}_{suffix}.json")
        return json.loads(path.read_text(encoding="utf-8"))

    ocr = read_sample_json("ocr")
    lines = ocr["lines"]
    ocr_text = ocr_engine.ocr_lines_to_text(lines)
    text_path = SAMPLE_IMAGE.with_name(f"{SAMPLE_IMAGE.stem}_ocr.txt")
    assert text_path.read_text(encoding="utf-8").rstrip("\n") == ocr_text
    assert len(lines) == ocr["num_lines"]
    assert all(len(line["box"]) == 4 for line in lines)

    truth = read_sample_json("ground_truth")
    text = parse_receipt_text(
        SAMPLE_IMAGE.stem, ocr_text, source_ocr_path=f"data/sample/{text_path.name}"
    ).to_dict()
    layout = apply_layout_aware_items(text, lines, SAMPLE_IMAGE.stem)
    assert text == read_sample_json("extracted")
    assert layout == read_sample_json("layout_extracted")
    for field in ("receipt_id", "store_name", "datetime", "invoice_id", "payment_method",
                  "total_amount", "vat", "service_fee", "items"):
        assert text[field] == layout[field] == truth[field]
