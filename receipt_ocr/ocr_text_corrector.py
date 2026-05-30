from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any


TEXT_REPLACEMENTS = {
    # Phrase-level corrections first
    "dau goi": "dầu gội",
    "thao dugc": "thảo dược",
    "duong am": "dưỡng ẩm",
    "hudng ca phe": "hương cà phê",
    "sudn gia": "sườn già",
    "sudn non": "sườn non",
    "ngua sau rang": "ngừa sâu răng",
    "co da": "có da",
    "bap gio": "bắp giò",
    "khong xudng": "không xương",
    "tinh luyen": "tinh luyện",
    "xuat khau": "xuất khẩu",
    "duong vang": "đường vàng",
    "drong tinh": "đường tinh",
    "tran cha": "trân châu",
    "tran chau": "trân châu",
    "duong den": "đường đen",

    # Token-level corrections
    "dugc": "dược",
    "dau": "dầu",
    "goi": "gội",
    "thao": "thảo",
    "dudng": "dưỡng",
    "hudng": "hương",
    "sudn": "sườn",
    "gia": "già",
    "rqi": "rọi",
    "xudng": "xương",
    "nudc": "nước",
    "trang": "trắng",
    "sua": "sữa",
    "de": "dê",
    "dua": "dừa",
    "vang": "vàng",
    "duong": "đường",
    "drong": "đường",
    "ca phe": "cà phê",
    "sua chua": "sữa chua",
    "xoai": "xoài",
    "mit": "mít",
    "cot": "cốt",
    "banh": "bánh",
    "thit": "thịt",
    "heo": "heo",
    "mong": "móng",
    "gio": "giò",
    "bap": "bắp",
    "khong": "không",
    "lkg": "1kg",
}


BRAND_REPLACEMENTS = {
    "vincomnerce": "VinCommerce",
    "vincommerce": "VinCommerce",
    "thuc coffee": "THỨC COFFEE",
    "the coffee house": "THE COFFEE HOUSE",
    "nha sachgd tc cam pha": "NHÀ SÁCH GD-TC CẨM PHẢ",
    "nha sach gd tc cam pha": "NHÀ SÁCH GD-TC CẨM PHẢ",
    "sieu thi minh loan": "SIÊU THỊ MINH LOAN",
    "cua hang nam oanh": "CỬA HÀNG NĂM OÁNH",
    "cua hangnamoanh": "CỬA HÀNG NĂM OÁNH",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d").replace("Đ", "D")
    return normalized


def normalize_key(text: str) -> str:
    text = strip_accents(str(text or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preserve_cp_prefix_spacing(text: str) -> str:
    text = re.sub(r"\bCP\s+", "CP_", text)
    text = re.sub(r"\bCP-", "CP_", text)
    return text


def correct_store_name(store_name: str | None) -> str | None:
    if not store_name:
        return store_name

    key = normalize_key(store_name)

    if key in BRAND_REPLACEMENTS:
        return BRAND_REPLACEMENTS[key]

    return store_name


def correct_item_name(item_name: str | None) -> str | None:
    if not item_name:
        return item_name

    corrected = str(item_name)
    corrected = preserve_cp_prefix_spacing(corrected)

    normalized = normalize_key(corrected)

    # Whole-name special cases.
    special_cases = {
        "apple teaice": "APPLE TEA ICE",
        "duakho": "DỪA KHÔ",
        "tayh01400": "Tẩy H01400",
        "tran cha": "Trân châu",
        "sua chua": "Sữa chua",
    }

    if normalized in special_cases:
        return special_cases[normalized]

    # Phrase-level corrections.
    # Work on a lowercase accent-stripped version, but preserve brand-like uppercase
    # only for known whole-name cases.
    corrected_lower = normalize_key(corrected)

    for wrong, right in sorted(TEXT_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"\b" + re.escape(wrong) + r"\b"
        corrected_lower = re.sub(pattern, right, corrected_lower, flags=re.IGNORECASE)

    # Restore common product prefix.
    corrected_lower = corrected_lower.replace("cp ", "CP_")

    # Keep common Latin brand words readable.
    corrected_lower = re.sub(r"\bvmhome\b", "VMHOME", corrected_lower, flags=re.IGNORECASE)
    corrected_lower = re.sub(r"\bclear\b", "CLEAR", corrected_lower, flags=re.IGNORECASE)
    corrected_lower = re.sub(r"\bgervenne\b", "GERVENNE", corrected_lower, flags=re.IGNORECASE)
    corrected_lower = re.sub(r"\bcolgate\b", "COLGATE", corrected_lower, flags=re.IGNORECASE)
    corrected_lower = re.sub(r"\byomost\b", "Yomost", corrected_lower, flags=re.IGNORECASE)

    return corrected_lower.strip()


def correct_extraction_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return a corrected copy of an extraction JSON payload.

    This function only adds text-correction fields.
    It does not modify numeric fields, invoice IDs, datetime, totals, or quantities.
    """
    corrected_payload = deepcopy(payload)

    original_store_name = corrected_payload.get("store_name")
    corrected_payload["corrected_store_name"] = correct_store_name(original_store_name)

    corrected_items = []

    for item in corrected_payload.get("items", []):
        corrected_item = deepcopy(item)
        corrected_item["corrected_name"] = correct_item_name(item.get("name"))
        corrected_items.append(corrected_item)

    corrected_payload["items"] = corrected_items
    corrected_payload["text_correction_version"] = "text_correction_v0.1_rule_based"

    return corrected_payload