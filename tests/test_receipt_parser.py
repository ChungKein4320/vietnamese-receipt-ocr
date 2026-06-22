from receipt_ocr.receipt_parser import (
    extract_datetime,
    extract_invoice_id,
    extract_items,
    extract_payment_method,
    extract_store_name,
    extract_total_amount,
    parse_receipt_text,
)


SAMPLE_RECEIPT_LINES = [
    "WINMART+",
    "Hoa don ban le",
    "Ngay: 15/08/2020 10:28",
    "So: HD12345",
    "Ten hang",
    "SUA TUOI VINAMILK",
    "2",
    "15.000",
    "30.000",
    "TONG THANH TOAN",
    "30.000",
    "TIEN MAT",
]


def test_extract_core_receipt_fields_from_lines():
    assert extract_store_name(SAMPLE_RECEIPT_LINES) == "WINMART+"
    assert extract_datetime(SAMPLE_RECEIPT_LINES) == "2020-08-15 10:28"
    assert extract_invoice_id(SAMPLE_RECEIPT_LINES) == "12345"
    assert extract_total_amount(SAMPLE_RECEIPT_LINES) == 30000
    assert extract_payment_method(SAMPLE_RECEIPT_LINES) == "cash"


def test_extract_items_from_basic_item_section():
    items = extract_items(SAMPLE_RECEIPT_LINES)

    assert len(items) == 1
    assert items[0].name == "SUA TUOI VINAMILK"
    assert items[0].quantity == 2
    assert items[0].unit_price == 15000
    assert items[0].line_total == 30000


def test_parse_receipt_text_returns_structured_result_without_warnings():
    result = parse_receipt_text(
        receipt_id="receipt_test_001",
        text="\n".join(SAMPLE_RECEIPT_LINES),
        source_ocr_path="data/ocr_outputs/receipt_test_001_ocr.txt",
    )

    assert result.receipt_id == "receipt_test_001"
    assert result.source_ocr_path == "data/ocr_outputs/receipt_test_001_ocr.txt"
    assert result.store_name == "WINMART+"
    assert result.datetime == "2020-08-15 10:28"
    assert result.invoice_id == "12345"
    assert result.total_amount == 30000
    assert result.payment_method == "cash"
    assert result.num_ocr_lines == len(SAMPLE_RECEIPT_LINES)
    assert result.parser_version == "rule_based_v0.3"
    assert result.warnings == []


def test_parse_receipt_text_adds_warnings_for_missing_required_fields():
    result = parse_receipt_text(
        receipt_id="receipt_empty",
        text="",
    )

    assert "store_name_not_found" in result.warnings
    assert "datetime_not_found" in result.warnings
    assert "total_amount_not_found" in result.warnings
    assert "items_not_found" in result.warnings
