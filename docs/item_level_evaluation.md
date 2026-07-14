# Item-level Evaluation

## Goal

Evaluate item extraction quality beyond receipt-level `items_count`.

This report compares each ground-truth item with the predicted item at the same order index.

These results come from the 15-receipt / 39-item MVP development benchmark used during parser development and error analysis. They are not held-out test results.

## Summary

- Number of receipts: `15`
- Total ground-truth items: `39`
- Total predicted items: `39`
- Items count accuracy: `100.00%`
- Overall item field accuracy: `87.82%`

## Field Accuracies

| field | accuracy |
| --- | --- |
| name_accuracy | 84.62% |
| quantity_accuracy | 74.36% |
| unit_price_accuracy | 97.44% |
| line_total_accuracy | 94.87% |

## Receipts with Item Count Errors

_No rows._

## Failed Item Rows

| receipt_id | item_index | gt_name | pred_name | name_score | gt_quantity | pred_quantity | quantity_ok | gt_unit_price | pred_unit_price | unit_price_ok | gt_line_total | pred_line_total | line_total_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receipt_003 | 1 | bot bap TAIKY | 1Goi | 0.2353 | 1 | 0 | 0 | 9000 | 9000 | 1 | 9000 | 6 | 0 |
| receipt_003 | 2 | Bột chiên giòn meizan | 1Goi | 0.16 | 1 | 0 | 0 | 7000 | 7000 | 1 | 7000 | 7000 | 1 |
| receipt_003 | 3 | Thịt Thăn Heo Xông Khói Lifefood 200g | 1Goi | 0.1463 | 1 | 0 | 0 | 52000 | 52000 | 1 | 52000 | 52000 | 1 |
| receipt_004 | 1 | CLEAR Dầu gội thảo dược 630g | CLEAR Dau goi thao dugc 630g | 0.9643 | 1 |  | 0 | 178000 | 178000 | 1 | 178000 | 178000 | 1 |
| receipt_004 | 2 | GERVENNE ST trắng n.hoa tc Sữa dê 900g | GERVENNE sT trang n.hoa tc sua de 900g | 1.0 | 1 |  | 0 | 108000 | 108000 | 1 | 108000 | 108000 | 1 |
| receipt_005 | 2 | Sữa chua matcha | Sua chua | 0.6957 | 1 | 2 | 0 | 25000 | 25000 | 1 | 25000 | 25000 | 1 |
| receipt_005 | 3 | Trân châu đường đen | Tran cha | 0.5926 | 1 | 1 | 1 | 10000 | 10000 | 1 | 10000 | 10000 | 1 |
| receipt_008 | 2 | Sữa tươi TT Dalat milk ít đường 180ml | Sua tuoi TT Dalat milk it duong I80ml | 0.973 | 4 | 4 | 1 | 6750 | 27000 | 0 | 27000 |  | 0 |
| receipt_013 | 1 | Sữa chua xoài | KM | 0.0 | 1 |  | 0 | 35000 | 35000 | 1 | 35000 | 35000 | 1 |
| receipt_013 | 2 | Sữa chua mít | Sua chua xoai | 0.8 | 1 |  | 0 | 35000 | 35000 | 1 | 35000 | 35000 | 1 |
| receipt_013 | 3 | Trân châu cốt dừa | Tran chau cot | 0.8667 | 1 |  | 0 | 5000 | 5000 | 1 | 5000 | 5000 | 1 |
| receipt_014 | 2 | Trà Sữa Sài-Gòn | Tra Sua Sai-Gon | 1.0 | 1 |  | 0 | 39000 | 39000 | 1 | 39000 | 39000 | 1 |

## Notes

- This evaluator currently uses order-based matching. It assumes the predicted item order follows the receipt order.
- Name matching uses normalized text similarity with a threshold of `0.75`.
- Numeric fields are evaluated with exact equality after number normalization.
- This is a baseline item-level evaluator. Later versions can add fuzzy item alignment and layout-aware matching.
- The private development inputs and generated evaluation artifacts are not committed, so this aggregate report cannot be regenerated from a fresh public checkout.
