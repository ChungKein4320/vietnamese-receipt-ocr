from __future__ import annotations

import re
import unicodedata


MONEY_PATTERN = re.compile(
    r"(?<![\dA-Za-z])"
    r"(?:\d{1,3}(?:[.,]\d{3})+|\d{4,})"
    r"(?:\s*(?:VND|VNĐ|D|Đ))?"
    r"(?![\dA-Za-z])",
    re.IGNORECASE,
)


def clean_line(line: str) -> str:
    """
    Remove redundant spaces from one OCR line.
    """
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line


def normalize_text(text: str) -> str:
    """
    Normalize raw OCR text while preserving line breaks.
    """
    lines = [clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def strip_vietnamese_accents(text: str) -> str:
    """
    Convert Vietnamese accented text to non-accented text.

    Example:
        "Tổng tiền phải thanh toán" -> "Tong tien phai thanh toan"
    """
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )

    without_accents = without_accents.replace("đ", "d")
    without_accents = without_accents.replace("Đ", "D")

    return without_accents


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for rule-based matching.
    """
    text = clean_line(text)
    text = strip_vietnamese_accents(text)
    text = text.upper()
    return text


def parse_money_value(value: str) -> int | None:
    """
    Convert money-like text to integer VND.

    Examples:
        "99.000" -> 99000
        "100,000" -> 100000
        "49.500 VND" -> 49500
    """
    digits = re.sub(r"[^\d]", "", value)

    if not digits:
        return None

    amount = int(digits)

    if amount > 100_000_000:
        return None

    return amount


def find_money_values(text: str) -> list[int]:
    """
    Find all money-like values in one line.
    """
    values = []

    for match in MONEY_PATTERN.findall(text):
        amount = parse_money_value(match)
        if amount is not None:
            values.append(amount)

    return values


def is_probable_barcode(text: str) -> bool:
    """
    Detect barcode-like lines.

    Example:
        "8935058962104"
    """
    compact = re.sub(r"\s+", "", text)
    digits = re.sub(r"\D", "", compact)

    if len(digits) < 8:
        return False

    digit_ratio = len(digits) / max(len(compact), 1)

    return digit_ratio >= 0.8


def parse_quantity(text: str) -> int | float | None:
    """
    Parse simple quantity lines.

    Examples:
        "2" -> 2
        "1.5" -> 1.5
        "1,5" -> 1.5

    Money-like values such as "49.500" should not be parsed as quantity.
    """
    text = clean_line(text)

    if MONEY_PATTERN.fullmatch(text):
        return None

    if re.fullmatch(r"\d{1,3}", text):
        return int(text)

    if re.fullmatch(r"\d{1,2}[,.]\d{1,2}", text):
        return float(text.replace(",", "."))

    return None


def normalize_datetime_value(text: str) -> str | None:
    """
    Extract and normalize datetime from OCR text.

    Supported examples:
        15/08/2020 10:28 -> 2020-08-15 10:28
        15-08-2020 10:28 -> 2020-08-15 10:28
        2020-08-15 10:28 -> 2020-08-15 10:28
    """
    patterns = [
        # Check ISO-like year-first dates before day-first dates.
        # Otherwise "2020-08-15 10:28" can be partially matched as
        # "20-08-15 10:28" and incorrectly normalized to 2015-08-20.
        re.compile(
            r"(?P<year>\d{4})[\/\-.](?P<month>\d{1,2})[\/\-.](?P<day>\d{1,2})"
            r"\s+(?P<hour>\d{1,2})[:hH](?P<minute>\d{2})"
        ),
        re.compile(
            r"(?P<day>\d{1,2})[\/\-.](?P<month>\d{1,2})[\/\-.](?P<year>\d{2,4})"
            r"\s+(?P<hour>\d{1,2})[:hH](?P<minute>\d{2})"
        ),
        re.compile(
            r"(?P<day>\d{1,2})[\/\-.](?P<month>\d{1,2})[\/\-.](?P<year>\d{2,4})"
        ),
    ]

    for pattern in patterns:
        match = pattern.search(text)

        if not match:
            continue

        day = int(match.group("day"))
        month = int(match.group("month"))
        year = int(match.group("year"))

        if year < 100:
            year += 2000

        if not (1 <= day <= 31 and 1 <= month <= 12):
            continue

        hour = match.groupdict().get("hour")
        minute = match.groupdict().get("minute")

        if hour is not None and minute is not None:
            hour_int = int(hour)
            minute_int = int(minute)

            if not (0 <= hour_int <= 23 and 0 <= minute_int <= 59):
                continue

            return f"{year:04d}-{month:02d}-{day:02d} {hour_int:02d}:{minute_int:02d}"

        return f"{year:04d}-{month:02d}-{day:02d}"

    return None