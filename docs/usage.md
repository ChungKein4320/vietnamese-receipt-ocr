# Usage Guide

This guide contains the detailed local commands for the OCR, extraction, evaluation, database, and debugging workflows. See the main [README](../README.md) for the project overview and headline results.

## Environment Setup

Create and activate a Python 3.10 environment:

```powershell
conda create -n receipt-ocr python=3.10 -y
conda activate receipt-ocr
```

Install dependencies:

```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Verify PaddleOCR:

```powershell
python -c "import paddle; print('paddle:', paddle.__version__)"
python -c "from paddleocr import PaddleOCR; print('paddleocr import ok')"
```

Run tests:

```powershell
python -m pytest -q
```

## Dataset Manifest

Copy the tracked example and add only data that you are authorized to use:

```powershell
Copy-Item data/dataset_manifest.example.csv data/dataset_manifest.csv
```

Validate IDs, split labels, safe paths, and referenced files:

```powershell
python scripts/validate_dataset_manifest.py --check-files
```

Receipts used while developing rules belong to `development`. Use `held_out` only for newly collected, frozen receipts that were not inspected while tuning the parser. See [Dataset Strategy](dataset_strategy.md).

## OCR and Extraction

Run OCR for one image:

```powershell
python scripts/run_ocr.py --image data/raw/receipts/receipt_001.png
```

Run OCR for all local images:

```powershell
python scripts/run_ocr.py --all
```

Extract structured fields from one OCR text file:

```powershell
python scripts/run_extraction.py --ocr-text data/ocr_outputs/receipt_001_ocr.txt
```

Extract all OCR outputs:

```powershell
python scripts/run_extraction.py --all
```

Default outputs are written under `data/ocr_outputs/` and `data/extracted_results/`.

## Split-aware Evaluation

Evaluate receipt-level fields:

```powershell
python scripts/evaluate_extraction.py --all --split development
```

Evaluate default text-parser items:

```powershell
python scripts/evaluate_items.py --split development
```

Evaluate layout-aware items:

```powershell
python scripts/evaluate_layout_items.py --split development
```

Replace `development` with `held_out` only when the manifest contains frozen held-out rows. Each split writes to its own directory:

```powershell
python scripts/evaluate_extraction.py --all --split held_out
python scripts/evaluate_items.py --split held_out
python scripts/evaluate_layout_items.py --split held_out
```

```text
data/evaluation/development/
data/evaluation/held_out/
```

A single receipt-level run is also isolated from the full report:

```powershell
python scripts/evaluate_extraction.py --receipt-id receipt_001 --split development
```

Its reports are written under `data/evaluation/development/single/receipt_001/`.

## Layout-aware Item Workflow

Generate layout rows and annotated debug images:

```powershell
python scripts/batch_inspect_ocr_layout.py
```

Run layout-aware extraction:

```powershell
python scripts/run_layout_item_extraction.py --all
```

Evaluate the selected split:

```powershell
python scripts/evaluate_layout_items.py --split development
```

Inspect one receipt instead of the full batch:

```powershell
python scripts/inspect_ocr_layout.py --receipt-id receipt_004
```

Summarize grouped layout rows:

```powershell
python scripts/summarize_layout_rows.py
```

## Optional Text-correction Experiment

Apply deterministic item-name correction:

```powershell
python scripts/apply_text_correction.py --all
```

Evaluate corrected names:

```powershell
python scripts/evaluate_corrected_items.py
```

This experiment improved average text similarity on the development benchmark but did not improve thresholded item-name accuracy. See [Corrected Item Evaluation](corrected_item_evaluation.md).

## Streamlit Demo

Start the local app:

```powershell
streamlit run app/streamlit_app.py
```

The sidebar supports the stable text parser and the layout-aware candidate. The app can preview OCR, structured fields, item rows, raw JSON, save records to SQLite, and export JSON/CSV.

## SQLite and Export

Initialize the local database:

```powershell
python scripts/init_db.py
```

Load extracted JSON files:

```powershell
python scripts/load_extractions_to_db.py --all
```

Export database records:

```powershell
python scripts/export_db.py
```

Exports are written under `data/extracted_results/`.

## Error Analysis

Generate the error analysis report from local evaluation artifacts:

```powershell
python scripts/analyze_errors.py
```

The report documents field-level failures and recommended parser improvements. See [Error Analysis](error_analysis.md).

## Local-only Data

Receipt images, annotations, generated OCR, predictions, evaluation artifacts, SQLite databases, and temporary debug files are ignored by Git unless explicitly provided as anonymized samples. Do not commit private receipts or personally identifying information.
