# Dataset Strategy

## Goal

Build a small but well-structured dataset for Vietnamese receipt OCR and information extraction.

The dataset should support:

- OCR baseline testing
- Rule-based information extraction
- Manual error analysis
- Field-level evaluation
- Portfolio demonstration

## Dataset Size

The MVP dataset contains 15 receipt/invoice images.

## Data Sources

Images may come from:

- Personal receipts
- Self-captured receipts
- Public receipt images
- Anonymized sample receipts

When using public images, do not claim ownership of the original images. If the project is published, document that the sample images are used for educational/portfolio demonstration.

## Folder Layout

```text
data/raw/receipts/        # raw receipt images
data/ground_truth/        # manual JSON annotations
data/processed/images/    # preprocessed images
data/ocr_outputs/         # OCR raw text outputs
data/extracted_results/   # extracted JSON outputs
data/sample/              # anonymized demo data
```

## File Naming Convention

Each receipt has a stable receipt ID.

Example:

```text
receipt_001
receipt_002
receipt_003
```

Raw image files should be placed in:

```text
data/raw/receipts/
```

Example:

```text
data/raw/receipts/receipt_001.png
data/raw/receipts/receipt_002.png
data/raw/receipts/receipt_003.png
```

Ground truth JSON files should be placed in:

```text
data/ground_truth/
```

Example:

```text
data/ground_truth/receipt_001.json
data/ground_truth/receipt_002.json
data/ground_truth/receipt_003.json
```

The image and ground truth file must share the same ID.

## Ground Truth Schema

Each receipt image has one manually created JSON annotation.

```json
{
  "receipt_id": "receipt_001",
  "image_path": "data/raw/receipts/receipt_001.png",
  "store_name": "Example Store",
  "datetime": "2020-08-15 10:28",
  "invoice_id": "HD001234",
  "items": [
    {
      "name": "Example item",
      "quantity": 1,
      "unit_price": 10000,
      "line_total": 10000
    }
  ],
  "vat": null,
  "service_fee": 0,
  "total_amount": 10000,
  "payment_method": "unknown",
  "notes": ""
}
```

## Field Rules

- Monetary values are stored as integers in VND.
- Unknown fields are set to `null`.
- Unknown payment method is set to `"unknown"`.
- Dates should use `YYYY-MM-DD HH:MM` when possible.
- Date-only receipts may use `YYYY-MM-DD` and should be mentioned in `notes`.
- Do not guess values that are not visible.
- Keep item names as close as possible to the receipt text.
- If VAT is only stated as included but no amount is shown, set `"vat": null`.

## Dataset Manifest

The file below tracks metadata for each image:

```text
data/dataset_manifest.csv
```

Columns:

| Column | Description |
|---|---|
| `receipt_id` | Stable receipt ID |
| `split` | `development` or `held_out` |
| `image_path` | Repository-relative path to the receipt image |
| `ground_truth_path` | Repository-relative path to its annotation |
| `store_type` | `cafe`, `minimart`, `restaurant`, `supermarket`, or `other` |
| `image_quality` | `good`, `medium`, or `poor` |
| `has_vat` | `true` or `false` |
| `has_items` | `true` or `false` |
| `notes` | Short description of the receipt |

The four required columns are `receipt_id`, `split`, `image_path`, and `ground_truth_path`. The remaining metadata columns are optional.

The existing 15-receipt MVP benchmark was used to develop rules and analyze errors, so every existing row must use:

```text
split=development
```

Only newly collected receipts that have not been inspected or used to tune parser rules may use `split=held_out`. Freeze their labels before evaluation, do not change rules after inspecting held-out errors, and report development and held-out results separately.

Use the tracked example as a starting point:

```text
data/dataset_manifest.example.csv
```

Validate the private manifest structure:

```powershell
python scripts/validate_dataset_manifest.py --check-files
```

The validator rejects legacy `test` labels, duplicate receipt IDs, unsafe paths, missing required columns, and optionally missing referenced files. A valid manifest with zero `held_out` rows is acceptable and means that no held-out result is available yet.

## Git Tracking Rules

The following data should not normally be committed if copyright/privacy is unclear:

```text
data/raw/receipts/*
data/ground_truth/*
data/processed/images/*
data/ocr_outputs/*
data/extracted_results/*
data/dataset_manifest.csv
database/*.db
```

Placeholder files may be committed:

```text
data/raw/receipts/.gitkeep
data/ground_truth/.gitkeep
data/processed/images/.gitkeep
data/ocr_outputs/.gitkeep
data/extracted_results/.gitkeep
data/sample/.gitkeep
```
