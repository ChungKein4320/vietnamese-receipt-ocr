from __future__ import annotations

import json
import re
from pathlib import Path

from receipt_ocr.config import EXTRACTED_RESULT_DIR
from receipt_ocr.schema import ReceiptExtractionResult, ReceiptItem
from receipt_ocr.text_normalizer import (
    clean_line,
    find_money_values,
    is_probable_barcode,
    normalize_datetime_value,
    normalize_for_matching,
    normalize_text,
    parse_quantity,
)


STORE_KEYWORDS = [
    "VINCOMMERCE",
    "VINMART",
    "WINMART",
    "THE COFFEE HOUSE",
    "COFFEE",
    "HIGHLANDS",
    "PHUC LONG",
    "STARBUCKS",
    "BACH HOA",
    "CO OP",
    "CO.OP",
    "LOTTE",
    "AEON",
    "CIRCLE K",
    "GS25",
    "FAMILY MART",
    "SUA CHUA",
    "NAM OANH",
    "NĂM OÁNH",
]

STORE_REJECT_KEYWORDS = [
    "HOA DON",
    "HOA ON",
    "PHIEU",
    "NGAY",
    "DATE",
    "TIME",
    "SO ",
    "MA ",
    "QUAY",
    "NVBH",
    "THU NGAN",
    "CASHIER",
    "HOTLINE",
    "WEBSITE",
    "DIEN THOAI",
    "DT:",
    "TEL",
    "TONG",
    "THANH TOAN",
]

ADDRESS_KEYWORDS = [
    "DUONG",
    "TRAN",
    "PHU",
    "PHUONG",
    "P.",
    "TP",
    "QUAN",
    "Q.",
    "HUYEN",
    "TINH",
    "TANG",
    "SO ",
]

TOTAL_KEYWORDS = [
    "TONG THANH TOAN",
    "TONG SO THANH TOAN",
    "TONG CONG",
    "TONG",
    "TIEN THANH TOAN",
    "TONG TIEN PHAI",
    "TONG TIEN THANH TOAN",
    "PHAI T TOAN",
    "T TOAN",
    "TONG TIEN VAT",
    "CASH VND",
]

TOTAL_EXCLUDE_KEYWORDS = [
    "GIAM",
    "KHACH TRA",
    "TRA LAI",
    "TRA LGI",
    "TIEN MAT",
    "TIEN MAL",
    "THE KHACH HANG",
    "TICH",
    "DIEM",
    "CHET KHAU",
    "CHIET KHAU",
]

ITEM_SECTION_START_KEYWORDS = [
    "MAT HANG",
    "TEN HANG",
    "TEN MON",
    "SAN PHAM",
    "ITEM",
    "DESCRIPTION",
]

ITEM_SECTION_END_KEYWORDS = [
    "TONG",
    "THANH TOAN",
    "TIEN KHACH",
    "TRA LAI",
    "VAT",
    "GTGT",
    "CONG TIEN",
    "CAM ON",
]

ITEM_REJECT_KEYWORDS = [
    # Column/header lines
    "DON GIA",
    "DN GIA",
    "DONGIA",
    "D GIA",
    "SO LUONG",
    "T.TIEN",
    "T TIEN",
    "THANH TIEN",
    "MAT HANG",
    "TEN HANG",
    "TEN MON",
    "SAN PHAM",
    "ITEM",
    "BARCODE",
    "MA HANG",
]


def _looks_like_address_metadata(name: str) -> bool:
    """
    Detect address/location metadata lines that were accidentally parsed as items.
    Keep this conservative to avoid removing real product names.
    """
    normalized = _normalize_item_name_for_filter(name)

    if not normalized:
        return False

    address_patterns = [
        r"\bP\s+[A-Z0-9]+",
        r"\bQ\s+[A-Z0-9]+",
        r"\bTP\s+[A-Z0-9]+",
        r"\bDONG DA\b",
        r"\bGO VAP\b",
        r"\bHA NOI\b",
        r"\bHA NO\b",
        r"\bHA NI\b",
        r"\bCAM PHA\b",
        r"\bPHAM NGOC THACH\b",
        r"\bHUYNH VAN BANH\b",
        r"\bTRUNG TU\b",
    ]

    return any(re.search(pattern, normalized) for pattern in address_patterns)


def _has_alpha(text: str) -> bool:
    return bool(re.search(r"[A-Za-zÀ-ỹ]", text))


def _normalize_item_matching_text(line: str) -> str:
    """
    Normalize OCR text for item filtering.

    Handles common OCR mistakes:
        T8ng -> Tong
        T0ng -> Tong
        C0ng -> Cong
        mal -> mat
        lgi -> lai
    """
    normalized = normalize_for_matching(line)

    replacements = {
        "T8NG": "TONG",
        "T0NG": "TONG",
        "C0NG": "CONG",
        "T0AN": "TOAN",
        "MAL": "MAT",
        "LGI": "LAI",
    }

    for wrong, correct in replacements.items():
        normalized = normalized.replace(wrong, correct)

    return normalized


def _looks_like_receipt_metadata_code(line: str) -> bool:
    """
    Detect receipt code lines that may look like item names.

    Examples:
        So:SON55296
        S6SON55598
        H00133765
    """
    normalized = _normalize_item_matching_text(line)
    compact = re.sub(r"[^A-Z0-9]", "", normalized)

    if re.search(r"\bSO[:\s]*[A-Z0-9]{4,}\b", normalized):
        return True

    if re.fullmatch(r"S[0O6]?[A-Z]{2,}\d{4,}", compact):
        return True

    if re.fullmatch(r"H\d{5,}", compact):
        return True

    return False


def _is_invalid_item_name(line: str) -> bool:
    """
    Detect non-item lines that should be removed from extracted items.

    This function must be conservative:
    - reject obvious metadata/header/total/discount lines
    - avoid broad substring rules that may remove real product names
    """
    normalized = _normalize_item_matching_text(line)

    if not normalized:
        return True

    normalized_clean = re.sub(r"[^A-Z0-9]+", " ", normalized)
    normalized_clean = re.sub(r"\s+", " ", normalized_clean).strip()
    compact = re.sub(r"[^A-Z0-9]", "", normalized)

    # Exact or near-exact column headers.
    exact_header_lines = {
        "SL",
        "DG",
        "D GIA",
        "DON GIA",
        "DN GIA",
        "T TIEN",
        "THANH TIEN",
        "MAT HANG",
        "TEN HANG",
        "TEN MON",
        "SAN PHAM",
        "ITEM",
    }

    if normalized_clean in exact_header_lines:
        return True

    # Longer header phrases are safe to match by substring.
    if any(keyword in normalized for keyword in ITEM_REJECT_KEYWORDS):
        return True

    # Receipt title / document header.
    if re.match(r"^(HOA\s+DON|HOA\s+ON|PHIEU)\b", normalized_clean):
        return True

    # Receipt metadata.
    metadata_prefixes = [
        "QUAY",
        "NVBH",
        "THU NGAN",
        "CASHIER",
        "HOTLINE",
        "TEL",
        "FAX",
        "DT",
        "DIEN THOAI",
        "NGAY",
        "DATE",
        "TIME",
        "THOI GIAN",
        "VI TRI",
    ]

    if any(re.match(rf"^{prefix}\b", normalized_clean) for prefix in metadata_prefixes):
        return True

    # Phone/fax lines.
    if ("FAX" in normalized_clean or "DT" in normalized_clean or "TEL" in normalized_clean) and re.search(
        r"\d{7,}", normalized_clean
    ):
        return True

    # Receipt code lines.
    if re.match(r"^SO\s+[A-Z0-9]{4,}$", normalized_clean):
        return True

    if re.fullmatch(r"S[0O6]?[A-Z]{2,}\d{4,}", compact):
        return True

    if re.fullmatch(r"H\d{5,}", compact):
        return True

    # Total/payment/discount lines.
    total_or_payment_phrases = [
        "TONG",
        "TONG CONG",
        "TONG THANH TOAN",
        "TONG SO THANH TOAN",
        "THANH TOAN",
        "TIEN THANH TOAN",
        "TIEN MAT",
        "TIEN MAL",
        "KHACH TRA",
        "TRA LAI",
        "TRA LGI",
        "CHIET KHAU",
        "CHET KHAU",
        "GIAM GIA",
        "GIAM",
        "DISCOUNT",
        "CASH VND",
    ]

    if any(phrase in normalized_clean for phrase in total_or_payment_phrases):
        return True

    # Common subtotal/display artifact in OCR output.
    if normalized_clean == "QUAT CAY":
        return True

    if is_probable_barcode(line):
        return True

    if re.search(r"\d{6,}[-_]\d{3,}", line):
        return True

    return False


def _is_store_candidate(line: str) -> bool:
    normalized = normalize_for_matching(line)

    if len(normalized) < 3:
        return False

    if not _has_alpha(line):
        return False

    if any(keyword in normalized for keyword in STORE_REJECT_KEYWORDS):
        return False

    if any(keyword in normalized for keyword in ADDRESS_KEYWORDS):
        return False

    if find_money_values(line):
        return False

    if is_probable_barcode(line):
        return False

    return True


def extract_store_name(lines: list[str]) -> str | None:
    """
    Extract store name using top-of-receipt heuristics.
    """
    top_lines = lines[:12]

    for line in top_lines:
        normalized = normalize_for_matching(line)

        for keyword in STORE_KEYWORDS:
            keyword_normalized = normalize_for_matching(keyword)
            if keyword_normalized in normalized:
                return clean_line(line)

    for line in top_lines:
        if _is_store_candidate(line):
            return clean_line(line)

    return None


def _to_24h_hour(hour: int, marker: str | None) -> int:
    """
    Convert Vietnamese AM/PM markers to 24-hour format.

    Common markers:
        SA / AM : morning
        CH / PM : afternoon/evening
    """
    if marker is None:
        return hour

    normalized_marker = normalize_for_matching(marker)

    if normalized_marker in {"CH", "PM"} and 1 <= hour <= 11:
        return hour + 12

    if normalized_marker in {"SA", "AM"} and hour == 12:
        return 0

    return hour


def _format_datetime(
    year: int,
    month: int,
    day: int,
    hour: int | None = None,
    minute: int | None = None,
    marker: str | None = None,
) -> str | None:
    """
    Return normalized datetime string if the date/time is valid.

    Output format:
        YYYY-MM-DD
        YYYY-MM-DD HH:MM
    """
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
        return None

    if hour is None or minute is None:
        return f"{year:04d}-{month:02d}-{day:02d}"

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    hour = _to_24h_hour(hour, marker)

    if not (0 <= hour <= 23):
        return None

    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"


def _parse_date_parts(day_text: str, month_text: str, year_text: str) -> tuple[int, int, int] | None:
    """
    Parse date parts from OCR text.

    Supports:
        dd/mm/yyyy
        dd.mm.yyyy
        dd-mm-yyyy
    """
    try:
        day = int(day_text)
        month = int(month_text)
        year = int(year_text)

        if year < 100:
            year += 2000

        return day, month, year
    except ValueError:
        return None


def _normalize_datetime_ocr_text(line: str) -> str:
    """
    Normalize common OCR mistakes in datetime strings.

    Examples:
        15/08r2020 -> 15/08/2020
        04.10.202016.19 -> keep as-is; parser handles no-space date/time
    """
    text = clean_line(line)

    # OCR sometimes reads "/" before year as "r":
    #   15/08r2020 -> 15/08/2020
    text = re.sub(
        r"(?P<prefix>\d{1,2}[\/.\-]\d{1,2})[rR](?=\d{2,4})",
        r"\g<prefix>/",
        text,
    )

    return text


def _extract_datetime_from_line(line: str) -> str | None:
    """
    Extract datetime from one OCR line.

    Supported examples:
        15/08/2020 10:28
        14/08/202020:36:00
        04.10.2020 16.21
        Thi gian:08:42:16-14/08/2020
        Ngay10/03/202008:01CH-08:01CH)
    """
    text = _normalize_datetime_ocr_text(line)

    if not text:
        return None

    # Avoid phone/contact lines.
    if _is_contact_or_phone_line(text):
        return None

    # ------------------------------------------------------------------
    # Pattern 1: time first, date later
    # Example:
    #   Thi gian:08:42:16-14/08/2020
    #   Thoi gian:09:47:04-15/08/2020
    # ------------------------------------------------------------------
    match = re.search(
        r"(?P<hour>\d{1,2})[:.](?P<minute>\d{2})(?::\d{2})?\s*[-–]\s*"
        r"(?P<day>\d{1,2})[\/.\-](?P<month>\d{1,2})[\/.\-](?P<year>\d{2,4})",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        date_parts = _parse_date_parts(
            match.group("day"),
            match.group("month"),
            match.group("year"),
        )

        if date_parts:
            day, month, year = date_parts
            return _format_datetime(
                year=year,
                month=month,
                day=day,
                hour=int(match.group("hour")),
                minute=int(match.group("minute")),
            )

    # ------------------------------------------------------------------
    # Pattern 2: date first, time later, possibly without space
    # Example:
    #   14/08/202020:36:00
    #   Ngay10/03/202008:01CH-08:01CH)
    # ------------------------------------------------------------------
    match = re.search(
        r"(?P<day>\d{1,2})[\/.\-](?P<month>\d{1,2})[\/.\-](?P<year>\d{2,4})"
        r"\s*"
        r"(?P<hour>\d{1,2})[:.](?P<minute>\d{2})"
        r"(?::\d{2})?"
        r"\s*(?P<marker>CH|SA|PM|AM)?",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        date_parts = _parse_date_parts(
            match.group("day"),
            match.group("month"),
            match.group("year"),
        )

        if date_parts:
            day, month, year = date_parts
            return _format_datetime(
                year=year,
                month=month,
                day=day,
                hour=int(match.group("hour")),
                minute=int(match.group("minute")),
                marker=match.group("marker"),
            )

    # ------------------------------------------------------------------
    # Pattern 3: date first, no time
    # Example:
    #   14/08/2020
    #   06.04.2019
    # ------------------------------------------------------------------
    match = re.search(
        r"(?P<day>\d{1,2})[\/.\-](?P<month>\d{1,2})[\/.\-](?P<year>\d{2,4})",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        date_parts = _parse_date_parts(
            match.group("day"),
            match.group("month"),
            match.group("year"),
        )

        if date_parts:
            day, month, year = date_parts
            return _format_datetime(
                year=year,
                month=month,
                day=day,
            )

    return None


def extract_datetime(lines: list[str]) -> str | None:
    """
    Extract receipt datetime from OCR lines.

    Version v0.2 improvements:
    - Supports time-first format: 08:42:16-14/08/2020
    - Supports date+time without whitespace: 14/08/202020:36:00
    - Supports Vietnamese PM marker CH: 08:01CH -> 20:01
    """
    cleaned_lines = [clean_line(line) for line in lines if clean_line(line)]

    # Pass 1: prioritize lines with explicit datetime keywords.
    datetime_keywords = [
        "NGAY",
        "THOI GIAN",
        "THDI GIAN",
        "THI GIAN",
        "GIO",
        "GID",
        "TIME",
        "DATE",
    ]

    for line in cleaned_lines:
        normalized = normalize_for_matching(line)

        if any(keyword in normalized for keyword in datetime_keywords):
            result = _extract_datetime_from_line(line)

            if result:
                return result

    # Pass 2: fallback to any line with date/time pattern.
    for line in cleaned_lines:
        result = _extract_datetime_from_line(line)

        if result:
            return result

    return None


def _extract_code_from_line(line: str) -> str | None:
    normalized = normalize_for_matching(line)

    candidates = re.findall(r"\b[A-Z]{1,8}[-_]?\d{4,}\b", normalized)

    if candidates:
        return candidates[0]

    candidates = re.findall(r"\b\d{6,}[-_]?[A-Z]{1,8}\b", normalized)

    if candidates:
        return candidates[0]

    return None


def _is_contact_or_phone_line(line: str) -> bool:
    """
    Detect phone/contact lines that should not be used as invoice IDs or datetime.

    Important:
    Numeric datetime lines such as `04.10.202016.19` must not be treated
    as phone numbers.
    """
    text = clean_line(line)

    if not text:
        return False

    # Do not classify date/datetime-like lines as phone/contact lines.
    # Examples:
    #   04.10.202016.19
    #   14/08/202020:36:00
    #   09:47:21-15/08r2020
    has_date_like_pattern = bool(
        re.search(
            r"\d{1,2}[\/.\-]\d{1,2}[\/.\-rR]\d{2,4}",
            text,
        )
    )

    if has_date_like_pattern:
        return False

    normalized = normalize_for_matching(text)

    contact_keywords = [
        "TEL",
        "DT",
        "DIEN THOAI",
        "FAX",
        "HOTLINE",
        "PHONE",
    ]

    if any(keyword in normalized for keyword in contact_keywords):
        return True

    # Standalone phone-like lines, for example:
    # 0869322496-02438765210
    compact_digits = re.sub(r"\D", "", text)

    if len(compact_digits) >= 9 and re.fullmatch(r"[\d\s().+-]+", text.strip()):
        return True

    return False


def _normalize_invoice_id_candidate(candidate: str, context_line: str = "") -> str | None:
    """
    Normalize common OCR mistakes in invoice ID candidates.

    Examples:
        S6-32              -> SO-32
        s6-31              -> SO-31
        S6SON55598         -> SON55598
        SHD:19810000682020 -> I9810000682020
    """
    if not candidate:
        return None

    raw = clean_line(candidate)
    raw = raw.strip(" :;,.|")

    if not raw:
        return None

    # Remove common labels if they were captured together with the value.
    raw = re.sub(
        r"^(?:SO\s*HOA\s*DON|SO\s*CHUNG\s*TU|SOCHUNG\s*TU|SOCHUNGTU|SOHD|S6HD|SHD|HD)\s*[:\-]?\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    raw = raw.strip(" :;,.|")

    if not raw:
        return None

    # Keep only invoice-safe characters.
    value = re.sub(r"[^A-Za-z0-9.\-]", "", raw)

    if not value:
        return None

    # S6-32 / S0-32 / SO-32 -> SO-32
    value = re.sub(r"^S[60O]-?(\d{1,6})$", r"SO-\1", value, flags=re.IGNORECASE)

    # S6SON55598 / S0SON55598 -> SON55598
    value = re.sub(r"^S[60O](SON\d{4,})$", r"\1", value, flags=re.IGNORECASE)

    # Normalize lowercase.
    value = value.upper()

    # SHD line sometimes OCRs I981... as 1981...
    # Example: SHD:19810000682020 -> I9810000682020
    context_normalized = normalize_for_matching(context_line)

    if "SHD" in context_normalized and re.fullmatch(r"1\d{10,}", value):
        value = "I" + value[1:]

    # Avoid obvious contact leftovers.
    if "FAX" in value or "TEL" in value:
        return None

    # Reject very short or label-only values.
    if value in {"SO", "S6", "S0", "HD", "SHD", "SOHD", "S6HD"}:
        return None

    if len(value) < 4:
        return None

    return value


def _has_invoice_label(line: str) -> bool:
    """
    Detect lines that indicate an invoice/receipt code may appear on
    the same line or the following line.
    """
    if _is_contact_or_phone_line(line):
        return False

    normalized = normalize_for_matching(line)
    normalized_clean = re.sub(r"[^A-Z0-9]+", " ", normalized)
    normalized_clean = re.sub(r"\s+", " ", normalized_clean).strip()

    # Exclude misleading phrases.
    excluded_phrases = [
        "SO KHACH",
        "SO CHO",
        "TONG SO",
        "SO LUONG",
    ]

    if any(phrase in normalized_clean for phrase in excluded_phrases):
        return False

    label_patterns = [
        r"\bSO HOA DON\b",
        r"\bSO CHUNG TU\b",
        r"\bSOCHUNG TU\b",
        r"\bSOCHUNGTU\b",
        r"\bSOHD\b",
        r"\bS6HD\b",
        r"\bSHD\b",
        r"\bHD\b",
        r"^SO$",
        r"^S6$",
        r"^SO[:\s]*",
        r"^S6[:\s]*",
    ]

    return any(re.search(pattern, normalized_clean) for pattern in label_patterns)


def _extract_invoice_from_labeled_line(line: str) -> str | None:
    """
    Extract invoice ID from lines that contain labels such as:
        So:2003000468
        So hoa don
        SHD:19810000682020
    """
    if _is_contact_or_phone_line(line):
        return None

    patterns = [
        r"\b(?:SO|S6)\s*HOA\s*DON\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\b(?:SO|S6)\s*CHUNG\s*TU\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\bSOCHUNG\s*TU\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\bSOCHUNGTU\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\bSHD\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\b(?:SOHD|S6HD)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
        r"\bHD\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-]{4,})",
        r"\b(?:SO|S6)\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9.\-]{2,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)

        if match:
            candidate = _normalize_invoice_id_candidate(
                match.group(1),
                context_line=line,
            )

            if candidate:
                return candidate

    return None


def _extract_direct_invoice_candidate(line: str, allow_bare_number: bool = False) -> str | None:
    """
    Extract direct invoice-like patterns from an OCR line.
    """
    if _is_contact_or_phone_line(line):
        return None

    direct_patterns = [
        # BL.200814.1.00046
        r"\bBL[.\-]\d{6}[A-Za-z0-9.\-]*\b",

        # SO-32, S6-32, s6-31
        r"\bS[O06]-\d{1,6}\b",

        # SON55296, S6SON55598
        r"\bS[O06]?SON\d{4,}\b",

        # H00133765, HD00197593
        r"\bHD?\d{5,}\b",

        # I00022-550301, I9810000682020
        r"\bI\d{4,}(?:-\d+)?\b",
    ]

    for pattern in direct_patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)

        if match:
            candidate = _normalize_invoice_id_candidate(
                match.group(0),
                context_line=line,
            )

            if candidate:
                return candidate

    # Numeric-only invoice IDs are allowed only near a label.
    # This avoids taking phone numbers as invoice IDs.
    if allow_bare_number:
        match = re.search(r"\b\d{8,}\b", line)

        if match:
            candidate = _normalize_invoice_id_candidate(
                match.group(0),
                context_line=line,
            )

            if candidate:
                return candidate

    return None


def extract_invoice_id(lines: list[str]) -> str | None:
    """
    Extract invoice / receipt ID from OCR lines.

    Version v0.2 improvements:
    - Support invoice IDs after labels such as "So hoa don".
    - Normalize OCR confusion S6/SO in receipt codes.
    - Support BL.*, SON*, H*, HD*, I* formats.
    - Avoid false positives from phone/fax/contact lines.
    """
    cleaned_lines = [clean_line(line) for line in lines if clean_line(line)]

    # Pass 1: same-line label extraction.
    for line in cleaned_lines:
        candidate = _extract_invoice_from_labeled_line(line)

        if candidate:
            return candidate

    # Pass 2: label line followed by candidate in next few lines.
    for index, line in enumerate(cleaned_lines):
        if not _has_invoice_label(line):
            continue

        for next_line in cleaned_lines[index + 1 : index + 4]:
            candidate = _extract_direct_invoice_candidate(
                next_line,
                allow_bare_number=True,
            )

            if candidate:
                return candidate

    # Pass 3: direct invoice-like patterns.
    for line in cleaned_lines:
        candidate = _extract_direct_invoice_candidate(line)

        if candidate:
            return candidate

    return None


def _normalize_total_matching_text(line: str) -> str:
    """
    Normalize OCR text for total amount matching.

    Handles common OCR mistakes:
        T8ng -> Tong
        T0ng -> Tong
        C0ng -> Cong
        T0an -> Toan
        mal -> mat
        lgi -> lai
    """
    normalized = normalize_for_matching(line)

    replacements = {
        "T8NG": "TONG",
        "T0NG": "TONG",
        "C0NG": "CONG",
        "T0AN": "TOAN",
        "MAL": "MAT",
        "LGI": "LAI",
    }

    for wrong, correct in replacements.items():
        normalized = normalized.replace(wrong, correct)

    return normalized


def _line_is_document_header(line: str) -> bool:
    """
    Avoid treating receipt document titles as total amount lines.

    Examples:
        HOA DON THANH TOAN
        PHIEU THANH TOAN
    """
    normalized = _normalize_total_matching_text(line)

    header_keywords = [
        "HOA DON THANH TOAN",
        "HOA ON THANH TOAN",
        "PHIEU THANH TOAN",
    ]

    return any(keyword in normalized for keyword in header_keywords)


def _line_has_datetime_like_value(line: str) -> bool:
    """
    Detect date/time-like lines to avoid extracting years as money.

    Examples:
        08/08/2020
        04.10.2020
        2020 08
    """
    if re.search(r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}", line):
        return True

    normalized = _normalize_total_matching_text(line)

    if ("NGAY" in normalized or "DATE" in normalized or "GIO" in normalized) and re.search(
        r"20\d{2}", line
    ):
        return True

    return False


def _line_is_total_stop(line: str) -> bool:
    """
    Stop scanning after total when payment/change/thank-you sections begin.
    """
    normalized = _normalize_total_matching_text(line)

    stop_keywords = [
        "TIEN MAT",
        "TIEN MAL",
        "KHACH TRA",
        "TRA LAI",
        "TRA LGI",
        "CHET KHAU",
        "CHIET KHAU",
        "CAM ON",
        "THANK",
        "HOTLINE",
        "WEBSITE",
    ]

    return any(keyword in normalized for keyword in stop_keywords)


def _line_is_noise_for_total_amount(line: str) -> bool:
    """
    Exclude lines that commonly contain non-total numbers:
        - dates
        - phone/fax
        - document codes
        - barcodes
    """
    normalized = _normalize_total_matching_text(line)

    if _line_has_datetime_like_value(line):
        return True

    if is_probable_barcode(line):
        return True

    if re.search(r"\d{5,}[-_]\d{5,}", line):
        return True

    noise_keywords = [
        "HOTLINE",
        "TEL",
        "FAX",
        "DT",
        "PHONE",
        "WEBSITE",
        "SO CHUNG TU",
        "SOCHUNG TU",
        "SO CHO",
        "SOCHO",
        "THOI GIAN",
        "NGAY",
        "GIO",
    ]

    return any(keyword in normalized for keyword in noise_keywords)


def _valid_total_amounts_from_line(line: str) -> list[int]:
    """
    Extract plausible total amount candidates from a line.
    """
    if _line_is_noise_for_total_amount(line):
        return []

    values = find_money_values(line)

    plausible_values = []

    for value in values:
        if 1_000 <= value <= 20_000_000:
            plausible_values.append(value)

    return plausible_values


def _line_has_total_keyword(line: str) -> bool:
    normalized = _normalize_total_matching_text(line)

    if _line_is_document_header(line):
        return False

    has_total_keyword = any(keyword in normalized for keyword in TOTAL_KEYWORDS)
    has_excluded_keyword = any(keyword in normalized for keyword in TOTAL_EXCLUDE_KEYWORDS)

    return has_total_keyword and not has_excluded_keyword


def _collect_following_total_amounts(lines: list[str], start_index: int) -> list[int]:
    """
    Collect money values after a total-related line.

    Example:
        Tong thanh toan
        70.000d
    """
    candidates = []

    for next_line in lines[start_index + 1 : start_index + 6]:
        if _line_is_total_stop(next_line):
            break

        values = _valid_total_amounts_from_line(next_line)

        if values:
            candidates.extend(values)

    return candidates


def extract_total_amount(lines: list[str]) -> int | None:
    """
    Extract final payable amount.

    Priority:
        1. Strong total-related lines and nearby amount
        2. CASH(VND)-amount line
        3. Conservative fallback
    """
    for index, line in enumerate(lines):
        if not _line_has_total_keyword(line):
            continue

        same_line_values = _valid_total_amounts_from_line(line)

        if same_line_values:
            return same_line_values[-1]

        following_values = _collect_following_total_amounts(lines, index)

        if following_values:
            return max(following_values)

    fallback_values = []

    for line in lines:
        if _line_is_total_stop(line):
            continue

        values = _valid_total_amounts_from_line(line)

        if values:
            fallback_values.extend(values)

    if not fallback_values:
        return None

    return max(fallback_values)


def extract_vat(lines: list[str]) -> int | None:
    """
    Extract VAT/GTGT amount if explicitly shown.
    """
    for index, line in enumerate(lines):
        normalized = normalize_for_matching(line)

        if "VAT" not in normalized and "GTGT" not in normalized and "THUE" not in normalized:
            continue

        values = find_money_values(line)

        if values:
            return values[-1]

        for next_line in lines[index + 1 : index + 3]:
            next_values = find_money_values(next_line)

            if next_values:
                return next_values[-1]

    return None


def extract_service_fee(lines: list[str]) -> int | None:
    """
    Extract service fee if explicitly shown.
    """
    fee_keywords = [
        "PHI DICH VU",
        "SERVICE FEE",
        "PHU THU",
    ]

    for index, line in enumerate(lines):
        normalized = normalize_for_matching(line)

        if not any(keyword in normalized for keyword in fee_keywords):
            continue

        values = find_money_values(line)

        if values:
            return values[-1]

        for next_line in lines[index + 1 : index + 3]:
            next_values = find_money_values(next_line)

            if next_values:
                return next_values[-1]

    return None


def extract_payment_method(lines: list[str]) -> str:
    """
    Extract payment method from OCR lines.

    Supported normalized values:
        cash
        card
        bank_transfer
        e_wallet
        unknown

    Version v0.2 improvements:
    - Detect OCR variants of "tien mat", such as "tien mal".
    - Infer cash from "khach dua" / "tien thua" / "tra lai" patterns.
    - Avoid false card detection from store names such as "THE COFFEE HOUSE".
    - Avoid false bank transfer detection from discount column "CK".
    """
    cleaned_lines = [clean_line(line) for line in lines if clean_line(line)]
    normalized_lines = [normalize_for_matching(line) for line in cleaned_lines]

    full_text = " ".join(normalized_lines)
    compact_text = re.sub(r"[^A-Z0-9]+", " ", full_text)
    compact_text = re.sub(r"\s+", " ", compact_text).strip()

    # ------------------------------------------------------------
    # 1. Cash payment should be detected early.
    #
    # This avoids false positives such as:
    #   THE COFFEE HOUSE -> "THE" should not mean card payment.
    # ------------------------------------------------------------
    cash_keywords = [
        "TIEN MAT",
        "TIEN MAL",
        "TIEN MAT VND",
        "CASH",
        "CASH VND",
    ]

    if any(keyword in compact_text for keyword in cash_keywords):
        return "cash"

    cash_inference_keywords = [
        "KHACH DUA",
        "KHACH TRA",
        "TIEN THUA",
        "TIEN TRA LAI",
        "TRA LAI",
        "TRA LAI KHACH",
        "TRA LGI KHACH",
    ]

    if any(keyword in compact_text for keyword in cash_inference_keywords):
        return "cash"

    # ------------------------------------------------------------
    # 2. E-wallet / QR payment.
    # ------------------------------------------------------------
    e_wallet_keywords = [
        "MOMO",
        "ZALOPAY",
        "ZALO PAY",
        "VNPAY",
        "VN PAY",
        "VI DIEN TU",
        "E WALLET",
        "QUET MA",
        "QUET QR",
        "MA QR",
        "QR CODE",
    ]

    if any(keyword in compact_text for keyword in e_wallet_keywords):
        return "e_wallet"

    # ------------------------------------------------------------
    # 3. Bank transfer.
    #
    # Do NOT use bare "CK" because in receipts it often means
    # "chiet khau", not "chuyen khoan".
    # ------------------------------------------------------------
    bank_transfer_keywords = [
        "CHUYEN KHOAN",
        "THANH TOAN CHUYEN KHOAN",
        "BANK TRANSFER",
        "TRANSFER",
        "NGAN HANG",
        "TAI KHOAN NGAN HANG",
    ]

    if any(keyword in compact_text for keyword in bank_transfer_keywords):
        return "bank_transfer"

    # ------------------------------------------------------------
    # 4. Card payment.
    #
    # Do NOT use bare "THE" because it causes false positives:
    #   THE COFFEE HOUSE
    #   THE KHACH HANG
    #
    # Only use card-specific contexts.
    # ------------------------------------------------------------
    card_keywords = [
        "QUET THE",
        "THANH TOAN THE",
        "TRA THE",
        "THE ATM",
        "THE VISA",
        "THE NAPAS",
        "VISA",
        "MASTERCARD",
        "MASTER CARD",
        "NAPAS",
        "POS",
    ]

    card_exclusion_keywords = [
        "THE COFFEE HOUSE",
        "THE KHACH HANG",
        "ID THE KHACH HANG",
        "THE THANH VIEN",
    ]

    has_card_keyword = any(keyword in compact_text for keyword in card_keywords)
    has_card_exclusion = any(keyword in compact_text for keyword in card_exclusion_keywords)

    if has_card_keyword and not has_card_exclusion:
        return "card"

    return "unknown"


def _find_item_section(lines: list[str]) -> list[str]:
    start_index = 0

    for index, line in enumerate(lines):
        normalized = normalize_for_matching(line)

        if any(keyword in normalized for keyword in ITEM_SECTION_START_KEYWORDS):
            start_index = index + 1
            break

    end_index = len(lines)

    for index in range(start_index, len(lines)):
        normalized = normalize_for_matching(lines[index])

        if any(keyword in normalized for keyword in ITEM_SECTION_END_KEYWORDS):
            end_index = index
            break

    return lines[start_index:end_index]


def _is_item_name_candidate(line: str) -> bool:
    normalized = _normalize_item_matching_text(line)

    if len(normalized) < 2:
        return False

    if not _has_alpha(line):
        return False

    if _is_invalid_item_name(line):
        return False

    if any(keyword in normalized for keyword in ITEM_SECTION_END_KEYWORDS):
        return False

    if find_money_values(line):
        return False

    return True

def _parse_item_from_single_line(line: str) -> ReceiptItem | None:
    """
    Parse item if OCR kept name, quantity, unit price, and total in one line.

    Example:
        "Cafe sua da 2 29000 58000"
    """
    pattern = re.compile(
        r"^(?P<name>.+?)\s+"
        r"(?P<quantity>\d{1,3}(?:[,.]\d{1,3})?)\s+"
        r"(?P<unit_price>\d{1,3}(?:[.,]\d{3})+|\d{4,})\s+"
        r"(?P<line_total>\d{1,3}(?:[.,]\d{3})+|\d{4,})$"
    )

    match = pattern.match(clean_line(line))

    if not match:
        return None

    name = clean_line(match.group("name"))
    quantity = parse_quantity(match.group("quantity"))
    unit_price = find_money_values(match.group("unit_price"))
    line_total = find_money_values(match.group("line_total"))

    if not name:
        return None

    return ReceiptItem(
        name=name,
        quantity=quantity,
        unit_price=unit_price[0] if unit_price else None,
        line_total=line_total[0] if line_total else None,
    )


def filter_invalid_items(items: list[ReceiptItem]) -> list[ReceiptItem]:
    """
    Remove false-positive items caused by receipt metadata, totals, discounts,
    and payment sections.

    This filter should not remove valid items just because their name contains
    short substrings such as SO, SL, DT, or CK.
    """
    filtered_items = []

    for item in items:
        name = clean_line(item.name)

        if _is_invalid_item_name(name):
            continue

        # A valid item should usually have at least one price-related value.
        if item.unit_price is None and item.line_total is None:
            continue

        filtered_items.append(item)

    return filtered_items


def _get_item_field(item, field_name: str):
    """
    Safely get a field from either a dataclass-like item or a dict item.
    """
    if isinstance(item, dict):
        return item.get(field_name)

    return getattr(item, field_name, None)


def _is_empty_value(value) -> bool:
    return value is None or str(value).strip() == ""


def _is_year_like_number(value) -> bool:
    """
    Detect values like 2019/2020 being accidentally parsed as prices.
    """
    if value is None:
        return False

    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return False

    return 1900 <= number <= 2100


def _normalize_item_name_for_filter(name: str) -> str:
    normalized = normalize_for_matching(name)
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_non_item_name(name: str) -> bool:
    """
    Detect OCR lines that should not be treated as receipt items.

    Conservative rule:
    - Remove obvious metadata/summary/noise lines.
    - Do NOT remove broad address-like words such as TP, TINH, XA, THON,
      because OCR product names can contain similar tokens.
    """
    if not name:
        return True

    normalized = _normalize_item_name_for_filter(name)

    if not normalized:
        return True

    # Very short OCR fragments such as "Od", "0d", "C".
    if normalized in {"OD", "0D", "O D", "C", "O", "D"}:
        return True

    # Receipt metadata / document labels.
    metadata_keywords = [
        "HOA DON",
        "PHIEU",
        "SO HOA DON",
        "SO CHUNG TU",
        "SOCHUNG TU",
        "SOCHUNGTU",
        "SOHD",
        "SHD",
        "NHAN VIEN",
        "THU NGAN",
        "NHAN VIEN THU NGAN",
        "CAISSIER",
        "CASHIER",
        "QUAY",
        "MAY POS",
        "VI TRI",
        "AN TAI CHO",
        "MANGVE",
        "MANG VE",
        "KHACH HANG",
        "KHACH LE",
        "PASS WIFI",
        "WIFI",
        "HOTLINE",
        "TEL",
        "FAX",
        "DIEN THOAI",
        "PHONE",
        "CAM ON",
        "XIN CAM ON",
        "THANK YOU",
        "SAMSUNG",
        "TRIPLE CAMERA",
        "GALAXY",
        "CHUP BANG",
    ]

    if any(keyword in normalized for keyword in metadata_keywords):
        return True

    # Totals / discounts / payment summary lines.
    summary_keywords = [
        "TONG",
        "T8NG",
        "CONG",
        "TONG CONG",
        "TONG TIEN",
        "TONG THANH TOAN",
        "THANH TOAN",
        "TONG SO",
        "TONG SL",
        "TONG SO LUONG",
        "TIEN THANH TOAN",
        "TIEN KHACH TRA",
        "KHACH TRA",
        "KHACH DUA",
        "TIEN THUA",
        "TRA KHACH",
        "TRA LAI",
        "CHIET KHAU",
        "GIAM GIA",
        "VAT",
        "PHI",
        "SERVICE",
    ]

    if any(keyword in normalized for keyword in summary_keywords):
        return True

    # Store names only when the line is clearly a store header.
    store_header_keywords = [
        "CUA HANG",
        "NHA SACH",
        "SIEU THI",
        "VINCOMMERCE",
    ]

    if any(keyword in normalized for keyword in store_header_keywords):
        return True

    # Lines containing explicit year/date are usually metadata, not item names.
    if re.search(r"\b20\d{2}\b", normalized):
        return True

    return False


def _should_keep_item_candidate(item) -> bool:
    """
    Decide whether a parsed item candidate is likely to be a real receipt item.
    """
    name = _get_item_field(item, "name")
    quantity = _get_item_field(item, "quantity")
    unit_price = _get_item_field(item, "unit_price")
    line_total = _get_item_field(item, "line_total")

    name_text = str(name or "")

    if _is_non_item_name(name_text):
        return False

    # Address line false positive:
    # Example receipt_007:
    #   P Trung TuQ Dong DaTP Ha No | unit_price=2020 | line_total=9017432
    if _looks_like_address_metadata(name_text):
        return False

    # Strong false-positive pattern:
    # metadata line + year parsed as unit_price.
    if _is_year_like_number(unit_price) and _is_empty_value(quantity):
        return False

    # Another weak candidate: no quantity and no line total.
    # Real receipt items usually have at least quantity or line total.
    if _is_empty_value(quantity) and _is_empty_value(line_total):
        return False

    return True


def _filter_item_candidates(items: list) -> list:
    """
    Remove non-item candidates after the parser creates item objects.
    """
    return [item for item in items if _should_keep_item_candidate(item)]


def _parse_reversed_temp_bill_items(section_lines: list[str]) -> list[ReceiptItem]:
    """
    Parse temporary-bill layouts where OCR order is reversed or column-like.

    Example receipt_009 OCR:
        35000
        35000
        1,00
        1 APPLE TEAICE
        35000

    Expected item:
        name=APPLE TEAICE
        quantity=1
        unit_price=35000
        line_total=35000
    """
    items: list[ReceiptItem] = []

    for index, raw_line in enumerate(section_lines):
        line = clean_line(raw_line)

        if not line:
            continue

        # Match item lines such as:
        #   1 APPLE TEAICE
        #   1 COCONUT
        match = re.match(r"^(?P<quantity>\d+(?:[,.]\d+)?)\s+(?P<name>[A-Za-zÀ-ỹ].+)$", line)

        if not match:
            continue

        name = clean_line(match.group("name"))
        quantity = parse_quantity(match.group("quantity"))

        if _is_non_item_name(name):
            continue

        # Look backward for prices.
        previous_lines = section_lines[max(0, index - 5):index]
        previous_money_values: list[int] = []

        for previous_line in previous_lines:
            previous_money_values.extend(find_money_values(previous_line))

        # Look forward as fallback.
        next_lines = section_lines[index + 1:min(index + 4, len(section_lines))]
        next_money_values: list[int] = []

        for next_line in next_lines:
            next_money_values.extend(find_money_values(next_line))

        money_values = previous_money_values or next_money_values

        if not money_values:
            continue

        unit_price = money_values[0]
        line_total = money_values[-1]

        items.append(
            ReceiptItem(
                name=name,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    return _filter_item_candidates(filter_invalid_items(items))


def _finalize_item_candidates(items: list[ReceiptItem]) -> list[ReceiptItem]:
    """
    Apply existing invalid-item filtering and the newer metadata/noise filter.
    """
    return _filter_item_candidates(filter_invalid_items(items))


def _score_item_candidate_list(items: list[ReceiptItem]) -> tuple[int, int]:
    """
    Score candidate item lists.

    Priority:
        1. More valid items.
        2. More complete item fields.
    """
    completeness_score = 0

    for item in items:
        if not _is_empty_value(_get_item_field(item, "quantity")):
            completeness_score += 1

        if not _is_empty_value(_get_item_field(item, "unit_price")):
            completeness_score += 1

        if not _is_empty_value(_get_item_field(item, "line_total")):
            completeness_score += 1

    return len(items), completeness_score


def extract_items(lines: list[str]) -> list[ReceiptItem]:
    """
    Item extraction.

    Strategy:
        1. Try parsing reversed temporary-bill item rows.
        2. Try parsing single-line item rows.
        3. Try parsing split OCR rows:
           item_name -> barcode(optional) -> unit_price -> quantity -> line_total
        4. Choose the best filtered candidate list.
    """
    section_lines = _find_item_section(lines)

    candidate_lists: list[list[ReceiptItem]] = []

    # Candidate 1: reversed temporary bill layout.
    reversed_items = _parse_reversed_temp_bill_items(section_lines)

    if reversed_items:
        candidate_lists.append(reversed_items)

    # Candidate 2: single-line item parser.
    single_line_items = []

    for line in section_lines:
        item = _parse_item_from_single_line(line)

        if item is not None:
            single_line_items.append(item)

    finalized_single_line_items = _finalize_item_candidates(single_line_items)

    if finalized_single_line_items:
        candidate_lists.append(finalized_single_line_items)

    # Candidate 3: split OCR row parser.
    split_items = []
    index = 0

    while index < len(section_lines):
        line = section_lines[index]

        if not _is_item_name_candidate(line):
            index += 1
            continue

        name = clean_line(line)
        quantity = None
        unit_price = None
        line_total = None
        consumed_until = index

        for lookahead_index in range(index + 1, min(index + 8, len(section_lines))):
            lookahead_line = section_lines[lookahead_index]

            if is_probable_barcode(lookahead_line):
                consumed_until = lookahead_index
                continue

            if _is_item_name_candidate(lookahead_line):
                break

            money_values = find_money_values(lookahead_line)

            if money_values:
                if unit_price is None:
                    unit_price = money_values[0]
                elif line_total is None:
                    line_total = money_values[-1]

                consumed_until = lookahead_index
                continue

            quantity_candidate = parse_quantity(lookahead_line)

            if quantity_candidate is not None and quantity is None:
                quantity = quantity_candidate
                consumed_until = lookahead_index
                continue

        if unit_price is not None or line_total is not None:
            split_items.append(
                ReceiptItem(
                    name=name,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

            index = max(consumed_until + 1, index + 1)
            continue

        index += 1

    finalized_split_items = _finalize_item_candidates(split_items)

    if finalized_split_items:
        candidate_lists.append(finalized_split_items)

    if not candidate_lists:
        return []

    return max(candidate_lists, key=_score_item_candidate_list)


def parse_receipt_text(
    receipt_id: str,
    text: str,
    source_ocr_path: str | Path | None = None,
) -> ReceiptExtractionResult:
    """
    Parse OCR text into structured receipt fields.
    """
    normalized_text = normalize_text(text)
    lines = [clean_line(line) for line in normalized_text.splitlines() if clean_line(line)]

    result = ReceiptExtractionResult(
        receipt_id=receipt_id,
        source_ocr_path=str(source_ocr_path).replace("\\", "/") if source_ocr_path else None,
        num_ocr_lines=len(lines),
    )

    result.store_name = extract_store_name(lines)
    result.datetime = extract_datetime(lines)
    result.invoice_id = extract_invoice_id(lines)
    result.items = extract_items(lines)
    result.vat = extract_vat(lines)
    result.service_fee = extract_service_fee(lines)
    result.total_amount = extract_total_amount(lines)
    result.payment_method = extract_payment_method(lines)

    if result.store_name is None:
        result.warnings.append("store_name_not_found")

    if result.datetime is None:
        result.warnings.append("datetime_not_found")

    if result.total_amount is None:
        result.warnings.append("total_amount_not_found")

    if not result.items:
        result.warnings.append("items_not_found")

    return result


def save_extraction_result(result: ReceiptExtractionResult) -> Path:
    """
    Save structured extraction result to data/extracted_results/.
    """
    EXTRACTED_RESULT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = EXTRACTED_RESULT_DIR / f"{result.receipt_id}_extracted.json"

    output_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path