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

from receipt_ocr.database import count_receipts, fetch_all_receipts, save_extraction_to_db
from receipt_ocr.ocr_engine import ocr_lines_to_text, run_ocr
from receipt_ocr.receipt_parser import parse_receipt_text


TMP_UPLOAD_DIR = PROJECT_ROOT / ".tmp_streamlit"
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg"]


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        /* ── Global ── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .block-container {
            padding-top: 1.75rem;
            padding-bottom: 3rem;
            max-width: 1300px;
        }

        /* ── Hero ── */
        .hero-card {
            padding: 2.25rem 2.5rem;
            border-radius: 20px;
            background: linear-gradient(135deg, #0a0f1e 0%, #0d1b35 40%, #0f2a4a 75%, #0a3a4a 100%);
            border: 1px solid rgba(6, 182, 212, 0.18);
            color: #f0f6ff;
            margin-bottom: 1.75rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255,255,255,0.06);
            position: relative;
            overflow: hidden;
        }

        .hero-card::before {
            content: "";
            position: absolute;
            top: -60px; right: -60px;
            width: 260px; height: 260px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(6,182,212,0.12) 0%, transparent 70%);
            pointer-events: none;
        }

        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.3rem 0.85rem;
            border-radius: 999px;
            background: rgba(6, 182, 212, 0.12);
            border: 1px solid rgba(6, 182, 212, 0.35);
            color: #67e8f9;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.03em;
            margin-bottom: 0.9rem;
        }

        .hero-title {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 0.55rem;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            font-size: 0.97rem;
            color: #94a3b8;
            max-width: 780px;
            line-height: 1.65;
        }

        /* ── Section Card ── */
        .section-card {
            padding: 1.35rem 1.5rem;
            border-radius: 16px;
            background: #0d1117;
            border: 1px solid #1e2d3d;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            margin-bottom: 1rem;
            color: #e2e8f0;
            transition: border-color 0.2s ease;
        }

        .section-card:hover {
            border-color: rgba(6, 182, 212, 0.25);
        }

        .section-card h1, .section-card h2,
        .section-card h3, .section-card h4,
        .section-card p, .section-card li,
        .section-card span { color: #e2e8f0 !important; }

        .section-card h4 {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }

        .small-muted {
            color: #64748b !important;
            font-size: 0.875rem;
            line-height: 1.6;
        }

        /* ── Badges ── */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            background: rgba(16, 185, 129, 0.1);
            color: #6ee7b7 !important;
            font-weight: 600;
            font-size: 0.8rem;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-pill::before {
            content: "●";
            font-size: 0.55rem;
            color: #10b981;
        }

        .warning-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            background: rgba(245, 158, 11, 0.1);
            color: #fcd34d !important;
            font-weight: 600;
            font-size: 0.8rem;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .warning-pill::before {
            content: "⚠";
            font-size: 0.75rem;
        }

        /* ── Metric Card ── */
        .metric-card {
            padding: 1.1rem 1.25rem;
            border-radius: 14px;
            background: #0d1117;
            border: 1px solid #1e2d3d;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
            height: 100%;
            transition: border-color 0.2s, transform 0.15s;
        }

        .metric-card:hover {
            border-color: rgba(6, 182, 212, 0.3);
            transform: translateY(-1px);
        }

        .metric-label {
            color: #475569;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 0.45rem;
        }

        .metric-value {
            color: #f1f5f9;
            font-size: 1rem;
            font-weight: 700;
            word-break: break-word;
            line-height: 1.35;
        }

        /* ── Pipeline Steps ── */
        .pipeline-step {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding: 0.7rem 1rem;
            border-radius: 12px;
            background: #0d1117;
            border: 1px solid #1e2d3d;
            margin-bottom: 0.45rem;
            color: #cbd5e1;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background 0.15s, border-color 0.15s;
        }

        .pipeline-step:hover {
            background: #111827;
            border-color: rgba(6, 182, 212, 0.2);
        }

        .pipeline-step-num {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: rgba(6, 182, 212, 0.12);
            border: 1px solid rgba(6, 182, 212, 0.3);
            color: #67e8f9;
            font-size: 0.7rem;
            font-weight: 800;
            flex-shrink: 0;
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            min-height: 2.75rem !important;
            letter-spacing: 0.01em;
            transition: opacity 0.15s, transform 0.1s !important;
        }

        .stButton > button:hover { transform: translateY(-1px); }
        .stButton > button:active { transform: translateY(0); }

        .stDownloadButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            min-height: 2.75rem !important;
        }

        /* ── Native Metric ── */
        div[data-testid="stMetric"] {
            background: #0d1117 !important;
            padding: 1rem 1.25rem !important;
            border-radius: 14px !important;
            border: 1px solid #1e2d3d !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        }

        div[data-testid="stMetric"] label { color: #475569 !important; font-size: 0.78rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.06em; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 700 !important; }

        /* ── Tabs ── */
        div[data-testid="stTabs"] [role="tablist"] {
            gap: 0.25rem;
            border-bottom: 1px solid #1e2d3d;
        }

        div[data-testid="stTabs"] button {
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            border-radius: 8px 8px 0 0 !important;
            padding: 0.5rem 1rem !important;
            color: #64748b !important;
            transition: color 0.15s !important;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #67e8f9 !important;
            border-bottom: 2px solid #06b6d4 !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: #080c14 !important;
            border-right: 1px solid #1a2332 !important;
        }

        [data-testid="stSidebar"] .stMarkdown p { color: #94a3b8 !important; font-size: 0.875rem; }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: #e2e8f0 !important; font-size: 0.8rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.06em; }

        .sidebar-status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.45rem 0;
            border-bottom: 1px solid #1a2332;
            font-size: 0.83rem;
        }

        .sidebar-status-label { color: #64748b; }
        .sidebar-status-value { color: #e2e8f0; font-weight: 600; }
        .sidebar-status-value.ok { color: #6ee7b7; }

        /* ── File Uploader ── */
        [data-testid="stFileUploader"] {
            border-radius: 12px;
        }

        [data-testid="stFileUploader"] > div {
            border: 2px dashed #1e2d3d !important;
            border-radius: 12px !important;
            background: #0d1117 !important;
            transition: border-color 0.2s;
        }

        [data-testid="stFileUploader"] > div:hover {
            border-color: rgba(6, 182, 212, 0.4) !important;
        }

        /* ── Dataframe ── */
        [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

        /* ── Divider ── */
        hr { border-color: #1e2d3d !important; }

        /* ── Code block ── */
        .stCode { border-radius: 10px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sanitize_receipt_id(file_name: str) -> str:
    """
    Convert uploaded file name to a safe receipt ID.

    Example:
        "Receipt 001.png" -> "receipt_001"
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
        return pd.DataFrame(columns=["name", "quantity", "unit_price", "line_total"])

    return pd.DataFrame(items)


def format_value(value) -> str:
    if value is None or value == "":
        return "Not found"

    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")

    return str(value)


def format_money(value) -> str:
    if value is None:
        return "Not found"

    try:
        return f"{int(value):,} VND".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_card() -> None:
    steps = [
        ("📤", "Upload receipt image"),
        ("🔍", "Run PaddleOCR"),
        ("✏️", "Normalize OCR text"),
        ("🗂️", "Extract structured fields"),
        ("💾", "Save to SQLite or export JSON / CSV"),
    ]
    steps_html = "".join(
        f'<div class="pipeline-step">'
        f'<span class="pipeline-step-num">{i+1}</span>'
        f'<span style="font-size:1rem">{icon}</span>'
        f'<span>{label}</span>'
        f'</div>'
        for i, (icon, label) in enumerate(steps)
    )
    st.markdown(
        f"""
        <div class="section-card">
            <h4 style="margin-top:0; color:#67e8f9 !important; font-size:0.8rem;
                       text-transform:uppercase; letter-spacing:0.07em;">
                Pipeline
            </h4>
            {steps_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_state_for_new_upload(uploaded_file_name: str) -> None:
    previous_file_name = st.session_state.get("uploaded_file_name")

    if previous_file_name != uploaded_file_name:
        st.session_state["uploaded_file_name"] = uploaded_file_name
        st.session_state.pop("ocr_lines", None)
        st.session_state.pop("ocr_text", None)
        st.session_state.pop("result_dict", None)
        st.session_state.pop("items_df", None)
        st.session_state.pop("image_path", None)
        st.session_state.pop("receipt_id", None)


def run_pipeline(image_path: Path, receipt_id: str, lang: str) -> None:
    with st.status("Running OCR and information extraction...", expanded=True) as status:
        st.write("Loading PaddleOCR model and reading receipt image...")
        ocr_lines = run_ocr(image_path=image_path, lang=lang)

        st.write("Converting OCR lines to raw text...")
        ocr_text = ocr_lines_to_text(ocr_lines)

        st.write("Running rule-based information extraction...")
        extraction_result = parse_receipt_text(
            receipt_id=receipt_id,
            text=ocr_text,
            source_ocr_path=image_path,
        )

        result_dict = extraction_result.to_dict()
        items_df = items_to_dataframe(result_dict["items"])

        st.session_state["ocr_lines"] = ocr_lines
        st.session_state["ocr_text"] = ocr_text
        st.session_state["result_dict"] = result_dict
        st.session_state["items_df"] = items_df

        status.update(label="Pipeline completed.", state="complete", expanded=False)


def render_overview(result_dict: dict, items_df: pd.DataFrame) -> None:
    st.markdown("#### 📊 Extraction overview")

    metric_cols = st.columns(5)

    with metric_cols[0]:
        render_metric_card("Store", format_value(result_dict.get("store_name")))

    with metric_cols[1]:
        render_metric_card("Datetime", format_value(result_dict.get("datetime")))

    with metric_cols[2]:
        render_metric_card("Invoice ID", format_value(result_dict.get("invoice_id")))

    with metric_cols[3]:
        render_metric_card("Total amount", format_money(result_dict.get("total_amount")))

    with metric_cols[4]:
        render_metric_card("Payment", format_value(result_dict.get("payment_method")))

    st.write("")

    detail_cols = st.columns(4)

    with detail_cols[0]:
        st.metric("OCR lines", result_dict.get("num_ocr_lines", 0))

    with detail_cols[1]:
        st.metric("Extracted items", len(result_dict.get("items", [])))

    with detail_cols[2]:
        st.metric("VAT", format_money(result_dict.get("vat")))

    with detail_cols[3]:
        st.metric("Service fee", format_money(result_dict.get("service_fee")))

    warnings = result_dict.get("warnings", [])

    if warnings:
        st.markdown(
            f"""
            <div class="section-card">
                <span class="warning-pill">Parser warnings</span>
                <p style="margin-top:0.8rem; margin-bottom:0;">{", ".join(warnings)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="section-card">
                <span class="status-pill">No parser warnings</span>
                <p class="small-muted" style="margin-top:0.8rem; margin-bottom:0;">
                    The rule-based parser found the main receipt fields without internal warnings.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not items_df.empty:
        st.markdown("#### 🛒 Item preview")
        st.dataframe(items_df, use_container_width=True, hide_index=True)


def render_database_tab(result_dict: dict) -> None:
    st.markdown("#### 💾 SQLite database")

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown(
            """
            <div class="section-card">
                <h4 style="margin-top:0;">Save current result</h4>
                <p class="small-muted">
                    Save the current extraction result into the local SQLite database.
                    Existing records with the same receipt ID will be replaced.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Save to SQLite", type="primary", use_container_width=True):
            receipt_db_id = save_extraction_to_db(result_dict, replace=True)
            st.success(f"Saved with database id={receipt_db_id}")

        st.metric("Saved receipts", count_receipts())

    with right_col:
        saved_receipts = fetch_all_receipts()

        if saved_receipts:
            st.dataframe(pd.DataFrame(saved_receipts), use_container_width=True, hide_index=True)
        else:
            st.info("No receipts saved yet.")


def render_download_tab(result_dict: dict, items_df: pd.DataFrame, receipt_id: str) -> None:
    st.markdown("#### 📥 Export current extraction")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            """
            <div class="section-card">
                <h4 style="margin-top:0; color:#67e8f9 !important;">
                    { } &nbsp;Structured JSON
                </h4>
                <p class="small-muted">Download all extracted fields and parser metadata.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.download_button(
            label="⬇ Download JSON",
            data=result_to_json_bytes(result_dict),
            file_name=f"{receipt_id}_extracted.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_b:
        st.markdown(
            """
            <div class="section-card">
                <h4 style="margin-top:0; color:#67e8f9 !important;">
                    ⊞ &nbsp;Items CSV
                </h4>
                <p class="small-muted">Download the extracted item table as a spreadsheet.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        csv_bytes = items_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="⬇ Download CSV",
            data=csv_bytes,
            file_name=f"{receipt_id}_items.csv",
            mime="text/csv",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Vietnamese Receipt OCR",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-badge">🧾 &nbsp;AI-Powered &middot; PaddleOCR &middot; SQLite</div>
            <div class="hero-title">Vietnamese Receipt OCR<br>&amp; Information Extraction</div>
            <div class="hero-subtitle">
                End-to-end pipeline: upload a receipt image &rarr; OCR with PaddleOCR &rarr; rule-based extraction
                &rarr; structured JSON &middot; item table &middot; SQLite storage &middot; CSV export.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Configuration")

        lang = st.selectbox(
            "OCR language",
            options=["en"],
            index=0,
            help="Current MVP baseline uses PaddleOCR lang='en'.",
        )

        st.divider()

        st.header("Debug options")

        show_ocr_confidence = st.checkbox("Show OCR confidence table", value=False)
        show_ocr_json = st.checkbox("Show OCR JSON", value=False)

        st.divider()

        st.header("Project status")
        st.markdown(
            """
            <div style="margin-top:0.5rem;">
                <div class="sidebar-status-row">
                    <span class="sidebar-status-label">MVP pipeline</span>
                    <span class="sidebar-status-value ok">✓ completed</span>
                </div>
                <div class="sidebar-status-row">
                    <span class="sidebar-status-label">OCR engine</span>
                    <span class="sidebar-status-value">PaddleOCR</span>
                </div>
                <div class="sidebar-status-row">
                    <span class="sidebar-status-label">Parser</span>
                    <span class="sidebar-status-value">rule-based v0.1</span>
                </div>
                <div class="sidebar-status-row" style="border-bottom:none;">
                    <span class="sidebar-status-label">Database</span>
                    <span class="sidebar-status-value">SQLite</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    upload_col, pipeline_col = st.columns([1.15, 0.85], gap="large")

    with upload_col:
        with st.container(border=True):
            st.markdown("#### 📂 Upload receipt image")

            uploaded_file = st.file_uploader(
                "Supported formats: PNG, JPG, JPEG",
                type=SUPPORTED_IMAGE_TYPES,
                label_visibility="visible",
            )

        if uploaded_file is not None:
            reset_state_for_new_upload(uploaded_file.name)

            image_path = save_uploaded_file(uploaded_file)
            receipt_id = sanitize_receipt_id(uploaded_file.name)

            st.session_state["image_path"] = image_path
            st.session_state["receipt_id"] = receipt_id

            image = Image.open(image_path)

            with st.container(border=True):
                st.markdown("#### 🖼️ Input preview")
                st.image(image, caption=uploaded_file.name, use_container_width=True)

                file_cols = st.columns(3)

                with file_cols[0]:
                    st.metric("Receipt ID", receipt_id)

                with file_cols[1]:
                    st.metric(
                        "File type",
                        Path(uploaded_file.name).suffix.lower().replace(".", "").upper(),
                    )

                with file_cols[2]:
                    st.metric("Image size", f"{image.width} × {image.height}")

    with pipeline_col:
        render_pipeline_card()

        with st.container(border=True):
            st.markdown("#### ⚡ Run extraction")

            if uploaded_file is None:
                st.info("Upload a receipt image to enable the pipeline.")
                run_button = False
            else:
                st.markdown(
                    f'<p class="small-muted" style="margin-bottom:0.4rem;">Current receipt</p>'
                    f'<p style="color:#67e8f9;font-weight:700;font-size:0.95rem;margin-bottom:0.75rem;">'
                    f'🗒️ {st.session_state["receipt_id"]}</p>',
                    unsafe_allow_html=True,
                )

                run_button = st.button(
                    "▶ Run OCR + Extraction",
                    type="primary",
                    use_container_width=True,
                )

    if uploaded_file is None:
        st.stop()

    if run_button:
        run_pipeline(
            image_path=st.session_state["image_path"],
            receipt_id=st.session_state["receipt_id"],
            lang=lang,
        )

    if "result_dict" not in st.session_state:
        st.markdown(
            """
            <div class="section-card">
                <span class="status-pill">Ready</span>
                <p class="small-muted" style="margin-top:0.8rem; margin-bottom:0;">
                    Click <strong>Run OCR + Extraction</strong> to process the uploaded receipt.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    result_dict = st.session_state["result_dict"]
    items_df = st.session_state["items_df"]
    ocr_text = st.session_state["ocr_text"]
    ocr_lines = st.session_state["ocr_lines"]
    receipt_id = st.session_state["receipt_id"]

    st.divider()

    overview_tab, items_tab, ocr_tab, json_tab, database_tab, download_tab = st.tabs(
        [
            "Overview",
            "Items",
            "OCR Debug",
            "JSON",
            "Database",
            "Download",
        ]
    )

    with overview_tab:
        render_overview(result_dict, items_df)

    with items_tab:
        st.markdown("#### 🛒 Extracted item table")

        if items_df.empty:
            st.info("No items extracted.")
        else:
            st.dataframe(items_df, use_container_width=True, hide_index=True)

            st.markdown("#### 📈 Item statistics")

            stat_cols = st.columns(3)

            with stat_cols[0]:
                st.metric("Items", len(items_df))

            with stat_cols[1]:
                numeric_total = pd.to_numeric(items_df["line_total"], errors="coerce").sum()
                st.metric(
                    "Sum of line totals",
                    format_money(int(numeric_total)) if numeric_total else "N/A",
                )

            with stat_cols[2]:
                numeric_quantity = pd.to_numeric(items_df["quantity"], errors="coerce").sum()
                st.metric(
                    "Total quantity",
                    round(float(numeric_quantity), 2) if numeric_quantity else "N/A",
                )

    with ocr_tab:
        st.markdown("#### 🔤 Raw OCR text")

        st.text_area(
            "OCR output",
            value=ocr_text,
            height=420,
            label_visibility="collapsed",
        )

        if show_ocr_confidence:
            st.markdown("#### 📉 OCR line confidence")

            confidence_df = pd.DataFrame(
                [
                    {
                        "line_no": index + 1,
                        "text": line["text"],
                        "confidence": round(line["confidence"], 4),
                    }
                    for index, line in enumerate(ocr_lines)
                ]
            )

            st.dataframe(confidence_df, use_container_width=True, hide_index=True)

        if show_ocr_json:
            st.markdown("#### 🗃️ OCR JSON")
            st.json({"num_lines": len(ocr_lines), "lines": ocr_lines})

    with json_tab:
        st.markdown("#### 🗂️ Structured extraction JSON")
        st.json(result_dict)

    with database_tab:
        render_database_tab(result_dict)

    with download_tab:
        render_download_tab(result_dict, items_df, receipt_id)


if __name__ == "__main__":
    main()