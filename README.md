# Vietnamese Receipt/Invoice OCR & Information Extraction System

An end-to-end OCR and information extraction system for Vietnamese receipts and invoices.

The system takes a receipt image as input, runs OCR, extracts structured fields, displays the result in a Streamlit UI, saves records to SQLite, and supports CSV/JSON export.

## Features

* Upload receipt/invoice images
* Run OCR using PaddleOCR
* Extract structured receipt fields using a rule-based parser
* Display raw OCR text
* Display structured JSON output
* Display extracted item table
* Save extraction results to SQLite
* Export receipt-level and item-level data to CSV
* Evaluate extraction quality against ground truth annotations

## Extracted Fields

The current parser extracts:

* Store name / seller name
* Date and time
* Invoice ID / receipt code
* Item list
* Quantity
* Unit price
* Line total
* VAT / service fee, if available
* Total amount
* Payment method

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

Verify installation:

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
* extraction execution
* JSON display
* item table display
* raw OCR text display
* saving results to SQLite
* downloading extracted JSON and item CSV

## Streamlit Demo

The Streamlit UI provides an end-to-end demo flow:

```text
Upload image
→ Run OCR + Extraction
→ Review extracted fields
→ Review item table
→ Save result to SQLite
→ Download JSON/CSV
```

## Evaluation

The current evaluation set contains 15 Vietnamese receipt/invoice images with manually created ground truth JSON files.

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

`total_amount` performs best after improving money normalization. The parser can handle Vietnamese-style currency formats such as:

```text
70.000d
80.000d
20.000d
CASH(VND)-88000
```

`invoice_id` remains the weakest field because receipt codes have inconsistent formats and are often confused with phone numbers, cashier IDs, or transaction codes.

`items_count` is challenging because different receipt layouts split item names, quantities, unit prices, and line totals across different OCR lines.

## Data Privacy and Git Tracking

Private receipt images, ground truth labels, OCR outputs, extracted outputs, evaluation reports, and SQLite databases are ignored by Git.

Ignored local data includes:

```text
data/raw/receipts/*
data/ground_truth/*
data/ocr_outputs/*
data/extracted_results/*
data/evaluation/*
database/*.db
```

Only placeholder `.gitkeep` files are committed to preserve folder structure.

## Limitations

* OCR errors propagate into the parser.
* The parser is rule-based and sensitive to layout variation.
* Item-level evaluation is not implemented yet.
* Invoice ID extraction is still weak.
* Payment method extraction depends on keyword matching.
* The current evaluation dataset is small and intended for MVP evaluation, not production benchmarking.
* The system does not currently use layout-aware models or document understanding models.

## Future Improvements

Planned improvements:

1. Add item-level evaluation.
2. Improve invoice ID extraction.
3. Add layout-aware item parsing using OCR bounding boxes.
4. Add image preprocessing with OpenCV.
5. Compare PaddleOCR with VietOCR.
6. Add optional LLM-based parser for difficult receipts.
7. Add FastAPI backend for API serving.
8. Add Docker support.
9. Expand the evaluation dataset.
10. Add synthetic/anonymized public sample receipts.

## Project Status

Current status:

```text
MVP completed
```

Implemented:

* OCR baseline
* Rule-based extraction pipeline
* Streamlit UI
* SQLite storage
* CSV/JSON export
* Field-level evaluation
* Documentation