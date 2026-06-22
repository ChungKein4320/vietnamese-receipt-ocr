# Sample Reproducible Data

This folder contains a small public sample that makes the repository easier to inspect without requiring the full local dataset.

The sample is based on `receipt_001` from the MVP evaluation set.

## Files

| File | Description |
| --- | --- |
| `receipt_001.png` | Sample receipt image used for the demo pipeline. |
| `receipt_001_ocr.txt` | OCR text output generated from the sample receipt. |
| `receipt_001_ocr.json` | OCR output with text confidence scores and bounding boxes. |
| `receipt_001_ground_truth.json` | Manually created ground-truth labels for the sample receipt. |
| `receipt_001_extracted.json` | Default parser output using `rule_based_v0.3`. |
| `receipt_001_layout_extracted.json` | Layout-aware item parser candidate output. |

## What this sample is for

Use this folder to quickly understand the project data flow:

```text
receipt image
→ OCR text / OCR boxes
→ structured extraction JSON
→ ground-truth comparison
```

The full MVP evaluation set contains 15 receipts and 39 item rows. This folder includes only one sample to keep the public repository lightweight and easy to review.

## Notes

* The sample output files are provided as reproducible artifacts for portfolio review.
* The current metrics in the main README are computed on the full 15-receipt MVP evaluation set, not only this single sample.
* Some OCR text is imperfect because it reflects real OCR behavior on Vietnamese receipts.
