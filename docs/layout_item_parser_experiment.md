# Layout-aware Item Parser Experiment

## Goal

Evaluate an experimental item parser that uses OCR layout rows generated from PaddleOCR bounding boxes.

This experiment does not replace the main `rule_based_v0.3` parser.

## Summary

- Number of receipts: `15`
- Total ground-truth items: `39`
- Total predicted items: `39`
- Items count accuracy: `100.00%`
- Overall item field accuracy: `100.00%`

## Field Accuracies

| field | accuracy |
| --- | --- |
| name_accuracy | 100.00% |
| quantity_accuracy | 100.00% |
| unit_price_accuracy | 100.00% |
| line_total_accuracy | 100.00% |

## Receipts with Item Count Errors

_No rows._

## Failed Rows

_No rows._

## Notes

- This is an experimental parser based on layout rows, not raw OCR text order.
- It is expected to perform better on name/value row pairs.
- It may still fail on highly irregular rows, merged cells, promotion rows, or OCR value corruption.
- The main parser remains `rule_based_v0.3` until this experiment outperforms it consistently.
