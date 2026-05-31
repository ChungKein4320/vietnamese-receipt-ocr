# Layout-aware Item Evaluation

## Goal

Evaluate item extraction quality from `data/layout_extracted_results`, where receipt-level fields come from the rule-based parser and item rows come from the layout-aware item parser candidate.

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

## Failed Item Rows

_No rows._

## Notes

- This evaluator checks the production-like layout-aware JSON outputs.
- It does not evaluate receipt-level fields such as store name, datetime, invoice ID, total amount, or payment method.
- Current layout-aware item parsing still depends on OCR layout CSV files generated from PaddleOCR bounding boxes.
- The main parser remains `rule_based_v0.3` until the layout-aware parser is fully integrated into the OCR pipeline.
