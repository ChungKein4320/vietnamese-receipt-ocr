# Layout-aware Item Parser Experiment

## Goal

Evaluate an experimental item parser that uses OCR layout rows generated from PaddleOCR bounding boxes.

This experiment does not replace the main `rule_based_v0.3` parser.

## Summary

- Number of receipts: `15`
- Total ground-truth items: `39`
- Total predicted items: `39`
- Items count accuracy: `100.00%`
- Overall item field accuracy: `88.46%`

## Field Accuracies

| field | accuracy |
| --- | --- |
| name_accuracy | 89.74% |
| quantity_accuracy | 69.23% |
| unit_price_accuracy | 97.44% |
| line_total_accuracy | 97.44% |

## Receipts with Item Count Errors

_No rows._

## Failed Rows

| receipt_id | item_index | gt_name | pred_name | name_score | gt_quantity | pred_quantity | gt_unit_price | pred_unit_price | gt_line_total | pred_line_total | strategy | source_row_id | value_row_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receipt_003 | 1 | bot bap TAIKY | bot bap TAIKY | 1.0 | 1 | 0 | 9000 | 9000 | 9000 | 6 | name_value_pair | 10 | 11 |
| receipt_003 | 2 | Bột chiên giòn meizan | Bot chien gion meizan | 1.0 | 1 | 0 | 7000 | 7000 | 7000 | 7000 | name_value_pair | 12 | 13 |
| receipt_003 | 3 | Thịt Thăn Heo Xông Khói Lifefood 200g | Thit Th an Heo Xong Khoi Lifefood 200g | 0.9867 | 1 | 0 | 52000 | 52000 | 52000 | 52000 | name_value_pair | 14 | 15 |
| receipt_004 | 1 | CLEAR Dầu gội thảo dược 630g | CLEAR Dau goi thao dugc 630g | 0.9643 | 1 |  | 178000 | 178000 | 178000 | 178000 | name_value_pair | 9 | 10 |
| receipt_004 | 2 | GERVENNE ST trắng n.hoa tc Sữa dê 900g | GERVENNE sT trang n.hoa tc sua de 900g | 1.0 | 1 |  | 108000 | 108000 | 108000 | 108000 | name_value_pair | 12 | 13 |
| receipt_005 | 2 | Sữa chua matcha | jenb | 0.0 | 1 | 2 | 25000 | 25000 | 25000 | 25000 | name_value_pair | 13 | 14 |
| receipt_005 | 3 | Trân châu đường đen | Tran cha | 0.5926 | 1 | 1 | 10000 | 10000 | 10000 | 10000 | single_row | 15 | 15 |
| receipt_008 | 2 | Sữa tươi TT Dalat milk ít đường 180ml | Sua tuoi TT Dalat milk it duong I80ml | 0.973 | 4 | 4 | 6750 | 27000 | 27000 | 27000 | name_value_pair | 9 | 10 |
| receipt_009 | 1 | APPLE TEA ICE | APPLE TEAICE | 0.96 | 1 |  | 35000 | 35000 | 35000 | 35000 | name_value_pair | 16 | 17 |
| receipt_011 | 2 | Bánh Mì Gà Kim Quất (Cay) | Quat(Cay) Banh Mi Ga Kim | 0.6087 | 1 | 2 | 32000 | 32000 | 32000 | 32000 | single_row | 9 | 9 |
| receipt_013 | 1 | Sữa chua xoài | Sua chua xoai | 1.0 | 1 |  | 35000 | 35000 | 35000 | 35000 | single_row | 11 | 11 |
| receipt_013 | 3 | Trân châu cốt dừa | Tran chau cot | 0.8667 | 1 |  | 5000 | 5000 | 5000 | 5000 | single_row | 13 | 13 |
| receipt_013 | 4 | DỪA KHÔ | dia | 0.4 | 1 | 4 | 5000 | 5000 | 5000 | 5000 | name_value_pair | 14 | 15 |
| receipt_014 | 2 | Trà Sữa Sài-Gòn | Tra Sua Sai-Gon | 1.0 | 1 |  | 39000 | 39000 | 39000 | 39000 | single_row | 14 | 14 |

## Notes

- This is an experimental parser based on layout rows, not raw OCR text order.
- It is expected to perform better on name/value row pairs.
- It may still fail on highly irregular rows, merged cells, promotion rows, or OCR value corruption.
- The main parser remains `rule_based_v0.3` until this experiment outperforms it consistently.
