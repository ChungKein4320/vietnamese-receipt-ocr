# Vietnamese Receipt OCR & Information Extraction

An end-to-end system for extracting structured information from Vietnamese receipts and invoices. It combines PaddleOCR, deterministic parsing, layout-aware item extraction, a Streamlit demo, SQLite persistence, JSON/CSV export, and explicit evaluation tooling.

## Highlights

- Processes receipt images into normalized JSON with receipt- and item-level fields.
- Provides a stable text parser and an optional layout-aware item parser candidate.
- Includes manual labels, split-aware evaluators, error analysis, and regression tests.
- Exposes OCR, parser selection, database storage, and export through Streamlit.
- Keeps private receipt data and generated artifacts out of Git while tracking an anonymized public sample.

## Evaluation Context

The reported numbers come from a **15-receipt / 39-item MVP development benchmark**. These receipts were used during parser development and error analysis, so the results are **not held-out test estimates**.

The private benchmark and generated artifacts are not committed. A fresh public checkout can inspect the tracked sample and evaluation code, but it cannot independently reproduce the aggregate figures below.

## Demo

| Upload and preview | Structured extraction |
| --- | --- |
| ![Upload and receipt preview](docs/screenshots/01_upload_and_preview.png) | ![Extraction overview](docs/screenshots/02_extraction_overview.png) |

| Item table | Database view |
| --- | --- |
| ![Extracted items](docs/screenshots/03_items_table.png) | ![SQLite records](docs/screenshots/04_database_view.png) |

![JSON and CSV export](docs/screenshots/05_download_export.png)

## Architecture

```text
Receipt image
    │
    ▼
PaddleOCR ──► text, confidence, bounding boxes
    │
    ├──► text normalization ──► rule-based receipt/text-item parser
    │
    └──► row grouping ────────► layout-aware item parser candidate
                                      │
                                      ▼
                           structured receipt JSON
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                     Streamlit      SQLite      JSON/CSV
                                      │
                                      ▼
                    split-aware field and item evaluation
```

## Extracted Fields

Receipt-level fields:

- Store name
- Datetime
- Invoice ID
- Total amount
- Payment method
- Item count

Item-level fields:

- Name
- Quantity
- Unit price
- Line total

## Development Results

Default receipt parser (`rule_based_v0.3`):

| Field | Accuracy |
| --- | ---: |
| Store name | 80.00% |
| Datetime | 93.33% |
| Invoice ID | 86.67% |
| Total amount | 93.33% |
| Payment method | 100.00% |
| Item count | 100.00% |
| **Overall receipt-field accuracy** | **92.22%** |

Item parser comparison on the same development benchmark:

| Parser | Item count | Name | Quantity | Unit price | Line total | Overall item-field |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Text parser `rule_based_v0.3` | 100.00% | 84.62% | 74.36% | 97.44% | 94.87% | **87.82%** |
| Layout candidate `layout_aware_item_v0.4_candidate` | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | **100.00%** |

The 100% layout-aware result is a prototype result on the **same development data**, not evidence of production generalization.

### Metric Semantics

- Receipt accuracy averages correct decisions across six fields.
- Store names pass at normalized similarity `>= 0.75`.
- Invoice IDs pass on exact normalized match or similarity `>= 0.85`.
- A datetime can pass when the date matches even if OCR misses the time.
- Item rows are aligned by receipt order, not optimal assignment.
- Item names pass at normalized similarity `>= 0.75`.
- Numeric item fields use exact equality after normalization.
- Overall item-field accuracy is the unweighted mean of name, quantity, unit-price, and line-total accuracies; item-count accuracy is reported separately.

See [Development Evaluation](docs/evaluation.md) for the full protocol, per-field tables, reproduction limits, and error discussion.

## Tech Stack

| Area | Tools |
| --- | --- |
| OCR | PaddleOCR |
| Image processing | OpenCV, Pillow |
| Parsing and evaluation | Python, pandas |
| Demo | Streamlit |
| Persistence | SQLite |
| Tests | pytest |

Python 3.10 is recommended because the pinned OCR stack may not support newer Python releases consistently.

## Quick Start

Create an environment and install dependencies:

```powershell
conda create -n receipt-ocr python=3.10 -y
conda activate receipt-ocr
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest -q
```

Start the Streamlit demo:

```powershell
streamlit run app/streamlit_app.py
```

Run OCR and extraction locally:

```powershell
python scripts/run_ocr.py --image data/raw/receipts/receipt_001.png
python scripts/run_extraction.py --ocr-text data/ocr_outputs/receipt_001_ocr.txt
```

For all commands, database operations, layout inspection, correction experiments, and output locations, see the [Usage Guide](docs/usage.md).

## Public Sample

`data/sample/` contains one anonymized receipt image plus OCR text/boxes, manual ground truth, default extraction, and layout-aware extraction. It is intended for code and data-flow inspection, not aggregate metric reproduction.

See [Sample Reproducible Data](data/sample/README.md).

## Split-aware Evaluation

The private `data/dataset_manifest.csv` assigns each receipt to exactly one split:

- `development`: data used to build rules or analyze errors.
- `held_out`: frozen, unseen data reserved for final evaluation.

Validate the manifest:

```powershell
python scripts/validate_dataset_manifest.py --check-files
```

Evaluate the current development split:

```powershell
python scripts/evaluate_extraction.py --all --split development
python scripts/evaluate_items.py --split development
python scripts/evaluate_layout_items.py --split development
```

Outputs are isolated by split under `data/evaluation/<split>/`. Evaluation stops instead of writing an empty report when the selected split has no records.

Do not label the existing 15 receipts as held-out. Add held-out results only after collecting and freezing new receipts that were not used to tune parser rules.

## Repository Map

```text
app/                 Streamlit interface
data/sample/         tracked anonymized sample
docs/                protocol, experiments, errors, and usage
notebooks/           OCR baseline walkthrough
receipt_ocr/         reusable OCR, parser, schema, DB, and evaluator modules
scripts/             command-line pipeline and evaluation entry points
tests/               parser, preprocessing, manifest, and evaluator tests
```

Private images, annotations, OCR outputs, predictions, evaluation artifacts, and SQLite databases are ignored by Git.

## Documentation

- [Usage Guide](docs/usage.md) — setup and all operational commands
- [Development Evaluation](docs/evaluation.md) — metrics, protocol, results, and limitations
- [Dataset Strategy](docs/dataset_strategy.md) — annotation rules and split manifest
- [Error Analysis](docs/error_analysis.md) — receipt-field failure analysis
- [Default Item Evaluation](docs/item_level_evaluation.md) — text-parser item errors
- [Layout-aware Evaluation](docs/layout_aware_item_evaluation.md) — candidate item results
- [Layout Parser Experiment](docs/layout_item_parser_experiment.md) — experiment notes
- [Correction Experiment](docs/corrected_item_evaluation.md) — normalized similarity analysis
- [MVP Scope](docs/mvp_scope.md) — project boundaries
- [Release Notes v0.4](docs/release_notes_v0.4.md) — Streamlit parser-mode milestone
- [Development Log](docs/devlog.md) — historical implementation notes

## Limitations

- The current benchmark is small, private, and development-only.
- The rule-based parser can fail on unseen layouts and OCR distortions.
- Store-name and invoice-ID extraction remain heuristic.
- Order-based item matching is weaker than assignment-based matching.
- The layout-aware candidate depends on reliable OCR bounding boxes.
- The 100% candidate result has not been validated on a held-out or external dataset.
- The tracked sample does not reproduce the aggregate metrics.
- Optional text correction improved average similarity but not thresholded item-name accuracy.

## Next Steps

1. Collect and freeze a diverse held-out receipt set.
2. Report development and held-out results separately.
3. Add assignment-based item matching and OCR recognition metrics such as CER.
4. Improve weak receipt fields and irregular-layout handling.
5. Pin and document a reproducible deployment environment.

Current parser versions:

```text
default receipt/text-item parser : rule_based_v0.3
layout-aware item candidate      : layout_aware_item_v0.4_candidate
```
