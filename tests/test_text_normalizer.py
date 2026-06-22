from receipt_ocr.text_normalizer import (
    clean_line,
    find_money_values,
    is_probable_barcode,
    normalize_datetime_value,
    normalize_for_matching,
    normalize_text,
    parse_money_value,
    parse_quantity,
    strip_vietnamese_accents,
)


def test_clean_line_removes_extra_spaces():
    assert clean_line("  Tổng    tiền   ") == "Tổng tiền"


def test_normalize_text_removes_empty_lines_and_preserves_line_breaks():
    raw_text = "  WINMART  \n\n  Tổng    tiền  "
    assert normalize_text(raw_text) == "WINMART\nTổng tiền"


def test_strip_vietnamese_accents_and_normalize_for_matching():
    assert strip_vietnamese_accents("Tổng tiền Đ") == "Tong tien D"
    assert normalize_for_matching("Tổng tiền phải thanh toán") == "TONG TIEN PHAI THANH TOAN"


def test_parse_money_value_with_vietnamese_formats():
    assert parse_money_value("49.500 VND") == 49500
    assert parse_money_value("100,000") == 100000
    assert parse_money_value("abc") is None


def test_find_money_values_from_line():
    line = "Tổng cộng 99.000 VND, khách trả 100,000"
    assert find_money_values(line) == [99000, 100000]


def test_barcode_and_quantity_detection():
    assert is_probable_barcode("8935058962104") is True
    assert is_probable_barcode("TONG THANH TOAN") is False
    assert parse_quantity("2") == 2
    assert parse_quantity("1,5") == 1.5
    assert parse_quantity("49.500") is None


def test_normalize_datetime_value():
    assert normalize_datetime_value("15/08/2020 10:28") == "2020-08-15 10:28"
    assert normalize_datetime_value("2020-08-15 10:28") == "2020-08-15 10:28"
    assert normalize_datetime_value("invalid datetime") is None
