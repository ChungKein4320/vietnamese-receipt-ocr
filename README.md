# Vietnamese Receipt/Invoice OCR & Information Extraction System

An end-to-end OCR and information extraction system for Vietnamese receipts and invoices.

The system takes a receipt image as input, runs OCR, extracts structured receipt fields, displays the result in a Streamlit UI, saves records to SQLite, and supports JSON/CSV export.

## Demo

### Upload and receipt preview

![Upload and Preview](docs/screenshots/01_upload_and_preview.png)

### Extraction overview

![Extraction Overview](docs/screenshots/02_extraction_overview.png)

### Extracted item table

![Items Table](docs/screenshots/03_items_table.png)

### SQLite database view

![Database View](docs/screenshots/04_database_view.png)

### JSON/CSV export

![Download Export](docs/screenshots/05_download_export.png)

## Features

* Upload Vietnamese receipt/invoice images.
* Run OCR using PaddleOCR.
* Extract structured receipt information with a rule-based parser.
* Display raw OCR text for debugging.
* Display structured JSON output.
* Display extracted item table.
* Save extraction results to SQLite.
* Export receipt-level and item-level data to JSON/CSV.
* Evaluate extraction quality against manually created ground truth labels.

## Extracted Fields

The current parser extracts:

* store name / seller name
* date and time
* invoice ID / receipt code
* item list
* quantity
* unit price
* line total
* VAT / service fee, if available
* total amount
* payment method

## Tech Stack

| Component              | Technology                   |
| ---------------------- | ---------------------------- |
| OCR                    | PaddleOCR                    |
| Image handling         | Pillow, OpenCV               |
| Information extraction | Regex + rule-based parser    |
| UI                     | Streamlit                    |
| Database               | SQLite                       |
| Data processing        | Pandas                       |
| Evaluation             | Custom field-level evaluator |
| Language               | Python                       |

## Project Structure

```text
vietnamese-receipt-ocr/
│
├── app/
│   └── streamlit_app.py
│
├── data/
│   ├── raw/
│   │   └── receipts/
│   ├── processed/
│   │   └── images/
│   ├── ocr_outputs/
│   ├── extracted_results/
│   ├── ground_truth/
│   ├── evaluation/
│   └── sample/
│
├── database/
│
├── docs/
│   ├── screenshots/
│   ├── dataset_strategy.md
│   ├── evaluation.md
│   └── mvp_scope.md
│
├── notebooks/
│   └── 01_ocr_baseline.ipynb
│
├── receipt_ocr/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── evaluator.py
│   ├── exporter.py
│   ├── image_preprocessor.py
│   ├── ocr_engine.py
│   ├── receipt_parser.py
│   ├── schema.py
│   └── text_normalizer.py
│
├── scripts/
│   ├── evaluate_extraction.py
│   ├── export_db.py
│   ├── init_db.py
│   ├── load_extractions_to_db.py
│   ├── run_extraction.py
│   └── run_ocr.py
│
├── tests/
│   ├── test_receipt_parser.py
│   └── test_text_normalizer.py
│
├── .gitignore
├── README.md
├── pyproject.toml
└── requirements.txt
```

## Pipeline

```text
Receipt image
→ PaddleOCR
→ Raw OCR text
→ Text normalization
→ Rule-based information extraction
→ Structured JSON
→ SQLite database
→ CSV/JSON export
→ Evaluation report
```

## Installation

Create a clean Python environment:

```powershell
conda create -n receipt-ocr python=3.10 -y
conda activate receipt-ocr
```

Install dependencies:

```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Verify the OCR installation:

```powershell
python -c "import paddle; print('paddle:', paddle.__version__)"
python -c "from paddleocr import PaddleOCR; print('paddleocr import ok')"
```

## Usage

### 1. Run OCR on one image

```powershell
python scripts/run_ocr.py --image data/raw/receipts/receipt_001.png
```

Output:

```text
data/ocr_outputs/receipt_001_ocr.txt
data/ocr_outputs/receipt_001_ocr.json
```

### 2. Run OCR on all images

```powershell
python scripts/run_ocr.py --all
```

### 3. Run information extraction on one OCR text file

```powershell
python scripts/run_extraction.py --ocr-text data/ocr_outputs/receipt_001_ocr.txt
```

Output:

```text
data/extracted_results/receipt_001_extracted.json
```

### 4. Run information extraction on all OCR outputs

```powershell
python scripts/run_extraction.py --all
```

### 5. Initialize SQLite database

```powershell
python scripts/init_db.py
```

### 6. Load extracted JSON files into SQLite

```powershell
python scripts/load_extractions_to_db.py --all
```

### 7. Export database records to CSV

```powershell
python scripts/export_db.py
```

Output:

```text
data/extracted_results/receipts_export.csv
data/extracted_results/items_export.csv
```

### 8. Run evaluation

```powershell
python scripts/evaluate_extraction.py --all
```

Output:

```text
data/evaluation/evaluation_report.csv
data/evaluation/evaluation_summary.json
```

### 9. Run Streamlit app

```powershell
streamlit run app/streamlit_app.py
```

The app supports:

* receipt image upload
* OCR execution
* rule-based extraction
* JSON preview
* item table preview
* raw OCR text debugging
* SQLite save
* JSON/CSV download

## Streamlit App Flow

```text
Upload image
→ Run OCR + Extraction
→ Review extracted fields
→ Review item table
→ Save result to SQLite
→ Download JSON/CSV
```

## Evaluation

The current evaluation set contains:

* 15 Vietnamese receipt/invoice images
* 15 manually created ground truth JSON files
* multiple receipt layouts, including retail, coffee shop, bookstore, restaurant, and small shop receipts

Current parser version:

```text
rule_based_v0.1
```

Current field-level results:

| Field          | Accuracy |
| -------------- | -------: |
| Store name     |   80.00% |
| Datetime       |   80.00% |
| Invoice ID     |   40.00% |
| Total amount   |   93.33% |
| Payment method |   73.33% |
| Items count    |   66.67% |
| Overall        |   72.22% |

## Key Findings

`total_amount` is currently the strongest field after improving money normalization. The parser can handle Vietnamese-style currency formats such as:

```text
70.000d
80.000d
20.000d
CASH(VND)-88000
```

`invoice_id` remains the weakest field because receipt IDs have inconsistent formats and are often confused with phone numbers, cashier IDs, transaction IDs, or store metadata.

`items_count` is challenging because receipt layouts differ significantly. Some receipts split item names, quantities, unit prices, and line totals across separate OCR lines.

## Data Privacy and Git Tracking

Private or local data is ignored by Git.

Ignored local data includes:

```text
data/raw/receipts/*
data/processed/images/*
data/ocr_outputs/*
data/extracted_results/*
data/ground_truth/*
data/evaluation/*
data/dataset_manifest.csv
database/*.db
.tmp_streamlit/
```

Only placeholder `.gitkeep` files and documentation screenshots are committed.

## Limitations

* OCR errors propagate into the parser.
* The parser is rule-based and sensitive to layout variation.
* Invoice ID extraction is still weak.
* Item extraction is layout-sensitive.
* Current item evaluation only checks item count, not item-level correctness.
* Payment method extraction depends on keyword matching.
* The current dataset is small and intended for MVP evaluation, not production benchmarking.
* The system does not currently use layout-aware document understanding models.

## Roadmap

This project is not finished at the MVP stage. The current version is a working baseline, and future improvements should focus on extraction quality.

Planned improvements:

1. Add detailed item-level evaluation.
2. Improve invoice ID extraction.
3. Improve payment method detection.
4. Add layout-aware item parsing using OCR bounding boxes.
5. Add OpenCV preprocessing experiments.
6. Compare PaddleOCR with VietOCR.
7. Add optional LLM-based parser for difficult receipts.
8. Expand the evaluation dataset.
9. Add FastAPI backend for API serving.
10. Add Docker support.

## Project Status

Current status:

```text
MVP v1 completed
```

Implemented:

* OCR baseline
* rule-based extraction pipeline
* Streamlit UI
* SQLite storage
* JSON/CSV export
* field-level evaluation
* documentation
* demo screenshots

Next phase:

```text
Improve extraction accuracy and add layout-aware parsing
```
