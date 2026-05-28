from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from receipt_ocr.ocr_engine import ocr_lines_to_text, run_ocr
from receipt_ocr.receipt_parser import parse_receipt_text


TMP_UPLOAD_DIR = PROJECT_ROOT / ".tmp_streamlit"
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg"]


def sanitize_receipt_id(file_name: str) -> str:
    """
    Convert uploaded file name to a safe receipt ID.

    Example:
        "my receipt 01.png" -> "my_receipt_01"
    """
    stem = Path(file_name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")

    if not stem:
        return "uploaded_receipt"

    return stem


def save_uploaded_file(uploaded_file) -> Path:
    """
    Save uploaded image to a temporary local folder so PaddleOCR can read it.
    """
    TMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    receipt_id = sanitize_receipt_id(uploaded_file.name)
    suffix = Path(uploaded_file.name).suffix.lower()

    if suffix not in [".png", ".jpg", ".jpeg"]:
        suffix = ".png"

    output_path = TMP_UPLOAD_DIR / f"{receipt_id}{suffix}"

    output_path.write_bytes(uploaded_file.getbuffer())

    return output_path


def result_to_json_bytes(result_dict: dict) -> bytes:
    return json.dumps(result_dict, ensure_ascii=False, indent=2).encode("utf-8")


def items_to_dataframe(items: list[dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(
            columns=["name", "quantity", "unit_price", "line_total"]
        )

    return pd.DataFrame(items)


def render_metric(label: str, value) -> None:
    display_value = value if value is not None else "Not found"
    st.metric(label=label, value=display_value)


def main() -> None:
    st.set_page_config(
        page_title="Vietnamese Receipt OCR",
        page_icon="🧾",
        layout="wide",
    )

    st.title("Vietnamese Receipt/Invoice OCR & Information Extraction")
    st.caption(
        "Upload a Vietnamese receipt image, run OCR, and extract structured fields."
    )

    with st.sidebar:
        st.header("Settings")

        lang = st.selectbox(
            "OCR language",
            options=["en"],
            index=0,
            help="Baseline uses PaddleOCR lang='en'. Vietnamese accents may not always be preserved.",
        )

        show_ocr_json = st.checkbox(
            "Show OCR JSON",
            value=False,
        )

        show_raw_lines = st.checkbox(
            "Show OCR line confidence",
            value=False,
        )

        st.divider()

        st.markdown("### Current pipeline")
        st.code(
            "image → OCR → text → rule-based parser → JSON/table",
            language="text",
        )

    uploaded_file = st.file_uploader(
        "Upload receipt image",
        type=SUPPORTED_IMAGE_TYPES,
    )

    if uploaded_file is None:
        st.info("Upload a PNG/JPG/JPEG receipt image to start.")
        return

    image_path = save_uploaded_file(uploaded_file)
    receipt_id = sanitize_receipt_id(uploaded_file.name)

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Input image")
        image = Image.open(image_path)
        st.image(image, caption=uploaded_file.name, use_container_width=True)

    with right_col:
        st.subheader("Run pipeline")

        st.write("Receipt ID:")
        st.code(receipt_id, language="text")

        run_button = st.button(
            "Run OCR + Extraction",
            type="primary",
            use_container_width=True,
        )

    if not run_button:
        return

    with st.spinner("Running PaddleOCR..."):
        ocr_lines = run_ocr(image_path=image_path, lang=lang)
        ocr_text = ocr_lines_to_text(ocr_lines)

    with st.spinner("Running rule-based extraction..."):
        extraction_result = parse_receipt_text(
            receipt_id=receipt_id,
            text=ocr_text,
            source_ocr_path=image_path,
        )

    result_dict = extraction_result.to_dict()
    items_df = items_to_dataframe(result_dict["items"])

    st.success("Pipeline completed.")

    st.divider()

    st.subheader("Extracted fields")

    metric_cols = st.columns(5)

    with metric_cols[0]:
        render_metric("Store", result_dict["store_name"])

    with metric_cols[1]:
        render_metric("Datetime", result_dict["datetime"])

    with metric_cols[2]:
        render_metric("Invoice ID", result_dict["invoice_id"])

    with metric_cols[3]:
        render_metric("Total amount", result_dict["total_amount"])

    with metric_cols[4]:
        render_metric("Payment", result_dict["payment_method"])

    if result_dict["warnings"]:
        st.warning("Parser warnings: " + ", ".join(result_dict["warnings"]))

    st.divider()

    tab_json, tab_items, tab_ocr, tab_download = st.tabs(
        ["Structured JSON", "Items table", "OCR text", "Download"]
    )

    with tab_json:
        st.json(result_dict)

    with tab_items:
        if items_df.empty:
            st.info("No items extracted.")
        else:
            st.dataframe(items_df, use_container_width=True)

    with tab_ocr:
        st.text_area(
            "Raw OCR text",
            value=ocr_text,
            height=400,
        )

        if show_raw_lines:
            st.markdown("### OCR lines with confidence")
            ocr_debug_df = pd.DataFrame(
                [
                    {
                        "text": line["text"],
                        "confidence": round(line["confidence"], 4),
                    }
                    for line in ocr_lines
                ]
            )
            st.dataframe(ocr_debug_df, use_container_width=True)

        if show_ocr_json:
            st.markdown("### OCR JSON")
            st.json(
                {
                    "num_lines": len(ocr_lines),
                    "lines": ocr_lines,
                }
            )

    with tab_download:
        json_bytes = result_to_json_bytes(result_dict)

        st.download_button(
            label="Download extracted JSON",
            data=json_bytes,
            file_name=f"{receipt_id}_extracted.json",
            mime="application/json",
            use_container_width=True,
        )

        csv_bytes = items_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Download items CSV",
            data=csv_bytes,
            file_name=f"{receipt_id}_items.csv",
            mime="text/csv",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()