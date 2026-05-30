# Corrected Item Name Evaluation

## Goal

Evaluate whether OCR text correction improves item name quality without changing numeric fields.

## Summary

- Number of compared item rows: `39`
- Raw item name accuracy: `84.62%`
- Corrected item name accuracy: `84.62%`
- Average raw similarity score: `0.8463`
- Average corrected similarity score: `0.8631`
- Average score delta: `0.0169`
- Improved rows: `13`
- Regressed rows: `0`
- Unchanged rows: `26`

## Most Improved Rows

| receipt_id | item_index | gt_name | raw_name | corrected_name | raw_score | corrected_score | raw_ok | corrected_ok | score_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receipt_013 | 4 | DỪA KHÔ | DUAKHO | DỪA KHÔ | 0.9231 | 1.0 | 1 | 1 | 0.0769 |
| receipt_006 | 1 | Đường tinh luyện xuất khẩu 1kg | Drong tinh luyen xuat khau lkg | đường tinh luyện xuất khẩu 1kg | 0.9333 | 1.0 | 1 | 1 | 0.0667 |
| receipt_015 | 1 | Bút nước M&G Q7 | But nudc M&G Q7 | but nước m g q7 | 0.9333 | 1.0 | 1 | 1 | 0.0667 |
| receipt_015 | 2 | Tẩy HO1400 | TayH01400 | Tẩy H01400 | 0.8421 | 0.9 | 1 | 1 | 0.0579 |
| receipt_005 | 3 | Trân châu đường đen | Tran cha | Trân châu | 0.5926 | 0.6429 | 0 | 0 | 0.0503 |
| receipt_004 | 4 | VMHOME Sữa RT Dưỡng ẩm hương cà phê 500g | VMHOME sua RT dudng am hudng ca phe 500g | VMHOME sữa rt dưỡng am hương cà phê 500g | 0.95 | 1.0 | 1 | 1 | 0.05 |
| receipt_004 | 5 | CP_Sườn già heo 300g | CP_sudn gia heo 300g | CP_sườn già heo 300g | 0.95 | 1.0 | 1 | 1 | 0.05 |
| receipt_004 | 6 | CP_Sườn non heo 300g | CP_sudn non heo 300g | CP_sườn non heo 300g | 0.95 | 1.0 | 1 | 1 | 0.05 |
| receipt_006 | 2 | Đường vàng xuất khẩu 1kg | Duong vang xuat khau lkg | đường vàng xuất khẩu 1kg | 0.9583 | 1.0 | 1 | 1 | 0.0417 |
| receipt_004 | 7 | CP_Thịt ba rọi có da 300g | CP_Thit ba rQi co da 300g | CP_thịt ba rọi có da 300g | 0.96 | 1.0 | 1 | 1 | 0.04 |
| receipt_009 | 1 | APPLE TEA ICE | APPLE TEAICE | APPLE TEA ICE | 0.96 | 1.0 | 1 | 1 | 0.04 |
| receipt_004 | 1 | CLEAR Dầu gội thảo dược 630g | CLEAR Dau goi thao dugc 630g | CLEAR dầu gội thảo dược 630g | 0.9643 | 1.0 | 1 | 1 | 0.0357 |
| receipt_004 | 9 | CP_Bắp giò heo không xương 300g | CP_Bap gio heo khong xudng 300g | CP_bắp giò heo không xương 300g | 0.9677 | 1.0 | 1 | 1 | 0.0323 |

## Regressed Rows

_No rows._

## Notes

- This evaluator only checks item names.
- It compares `name` versus `corrected_name` against ground truth.
- Numeric fields are intentionally not modified by the correction layer.
- The current correction layer is rule-based and experimental.
