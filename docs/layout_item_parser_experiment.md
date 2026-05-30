# Layout-aware Item Parser Experiment

## Goal

Evaluate an experimental item parser that uses OCR layout rows generated from PaddleOCR bounding boxes.

This experiment does not replace the main `rule_based_v0.3` parser.

## Summary

- Number of receipts: `15`
- Total ground-truth items: `39`
- Total predicted items: `39`
- Items count accuracy: `100.00%`
- Overall item field accuracy: `98.72%`

## Field Accuracies

| field | accuracy |
| --- | --- |
| name_accuracy | 94.87% |
| quantity_accuracy | 100.00% |
| unit_price_accuracy | 100.00% |
| line_total_accuracy | 100.00% |

## Receipts with Item Count Errors

_No rows._

## Failed Rows

| receipt_id | item_index | gt_name | pred_name | name_score | gt_quantity | pred_quantity | gt_unit_price | pred_unit_price | gt_line_total | pred_line_total | strategy | source_row_id | value_row_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receipt_005 | 3 | Trân châu đường đen | Tran cha | 0.5926 | 1 | 1 | 10000 | 10000 | 10000 | 10000 | single_row | 15 | 15 |
| receipt_011 | 2 | Bánh Mì Gà Kim Quất (Cay) | Quat(Cay) Banh Mi Ga Kim | 0.6087 | 1 | 1 | 32000 | 32000 | 32000 | 32000 | single_row | 9 | 9 |

## Notes

- This is an experimental parser based on layout rows, not raw OCR text order.
- It is expected to perform better on name/value row pairs.
- It may still fail on highly irregular rows, merged cells, promotion rows, or OCR value corruption.
- The main parser remains `rule_based_v0.3` until this experiment outperforms it consistently.
