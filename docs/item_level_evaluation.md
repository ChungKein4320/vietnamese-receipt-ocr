# Item-level Evaluation

## Goal

Evaluate item extraction quality beyond receipt-level `items_count`.

This report compares each ground-truth item with the predicted item at the same order index.

## Summary

- Number of receipts: `15`
- Total ground-truth items: `39`
- Total predicted items: `44`
- Items count accuracy: `66.67%`
- Overall item field accuracy: `62.82%`

## Field Accuracies

| field | accuracy |
| --- | --- |
| name_accuracy | 51.28% |
| quantity_accuracy | 56.41% |
| unit_price_accuracy | 74.36% |
| line_total_accuracy | 69.23% |

## Receipts with Item Count Errors

| receipt_id | gt_items_count | pred_items_count | items_count_ok |
| --- | --- | --- | --- |
| receipt_006 | 2 | 3 | 0 |
| receipt_007 | 1 | 2 | 0 |
| receipt_008 | 5 | 6 | 0 |
| receipt_012 | 1 | 2 | 0 |
| receipt_015 | 2 | 3 | 0 |

## Failed Item Rows

| receipt_id | item_index | gt_name | pred_name | name_score | gt_quantity | pred_quantity | quantity_ok | gt_unit_price | pred_unit_price | unit_price_ok | gt_line_total | pred_line_total | line_total_ok |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| receipt_003 | 1 | bot bap TAIKY | 1Goi | 0.2353 | 1 | 0 | 0 | 9000 | 9000 | 1 | 9000 | 6 | 0 |
| receipt_003 | 2 | Bột chiên giòn meizan | 1Goi | 0.16 | 1 | 0 | 0 | 7000 | 7000 | 1 | 7000 | 7000 | 1 |
| receipt_003 | 3 | Thịt Thăn Heo Xông Khói Lifefood 200g | 1Goi | 0.1463 | 1 | 0 | 0 | 52000 | 52000 | 1 | 52000 | 52000 | 1 |
| receipt_004 | 1 | CLEAR Dầu gội thảo dược 630g | CLEAR Dau goi thao dugc 630g | 0.9643 | 1 |  | 0 | 178000 | 178000 | 1 | 178000 | 178000 | 1 |
| receipt_004 | 2 | GERVENNE ST trắng n.hoa tc Sữa dê 900g | KM | 0.0 | 1 |  | 0 | 108000 | 46000 | 0 | 108000 |  | 0 |
| receipt_004 | 3 | COLGATE KR ngừa sâu răng 250g+bc | GERVENNE sT trang n.hoa tc sua de 900g | 0.3143 | 1 |  | 0 | 35000 | 108000 | 0 | 35000 | 108000 | 0 |
| receipt_004 | 4 | VMHOME Sữa RT Dưỡng ẩm hương cà phê 500g | COLGATE KR ngua sau rang 250g+bc | 0.3611 | 1 | 1 | 1 | 39000 | 35000 | 0 | 39000 | 35000 | 0 |
| receipt_004 | 5 | CP_Sườn già heo 300g | VMHOME sua RT dudng am hudng ca phe 500g | 0.3667 | 1 | 1 | 1 | 39900 | 39000 | 0 | 39900 | 39000 | 0 |
| receipt_005 | 2 | Sữa chua matcha | Sua chua | 0.6957 | 1 | 2 | 0 | 25000 | 25000 | 1 | 25000 | 25000 | 1 |
| receipt_005 | 3 | Trân châu đường đen | Tran cha | 0.5926 | 1 | 1 | 1 | 10000 | 10000 | 1 | 10000 | 10000 | 1 |
| receipt_006 | 1 | Đường tinh luyện xuất khẩu 1kg | CUA HANG NAM OANH | 0.2553 | 30 |  | 0 | 14000 | 2020 | 0 | 420000 |  | 0 |
| receipt_006 | 2 | Đường vàng xuất khẩu 1kg | Drong tinh luyen xuat khau lkg | 0.7037 | 30 | 30 | 1 | 14000 | 14000 | 1 | 420000 | 420000 | 1 |
| receipt_007 | 1 | Cà phê tan cao cấp Family Tchibo lọ 200g | P Trung TuQ Dong DaTP Ha No | 0.1194 | 1 |  | 0 | 184500 | 2020 | 0 | 184500 | 9017432 | 0 |
| receipt_008 | 1 | SC nha đam VNM 100g | Thon Phu ThuyXa Phn Thj Huycn Gia Lam TP Ha Ni | 0.1846 | 20 |  | 0 | 6250 | 2020 | 0 | 125000 |  | 0 |
| receipt_008 | 2 | Sữa tươi TT Dalat milk ít đường 180ml | SC nha dam VNM 100g | 0.3571 | 4 | 20 | 0 | 6750 | 6250 | 0 | 27000 | 125000 | 0 |
| receipt_008 | 3 | Yomost Bạc hà Việt quất 170ml | Sua tuoi TT Dalat milk it duong I80ml | 0.303 | 4 | 4 | 1 | 6250 | 27000 | 0 | 25000 |  | 0 |
| receipt_008 | 4 | Sữa Yomost dâu 180ml/48 | Yomost Bac ha Viet quat 170ml | 0.5385 | 4 | 4 | 1 | 6250 | 6250 | 1 | 25000 | 25000 | 1 |
| receipt_008 | 5 | Sữa Yomost cam 170ml | Sira Yomost dau 180ml/48 | 0.7273 | 4 | 4 | 1 | 6250 | 6250 | 1 | 25000 | 25000 | 1 |
| receipt_009 | 1 | APPLE TEA ICE | 1 APPLE TEAICE | 0.8889 | 1 |  | 0 | 35000 | 35000 | 1 | 35000 |  | 0 |
| receipt_012 | 1 | Búp bê trang điểm | Nhan vien thu ngan | 0.3429 | 1 |  | 0 | 95000 | 2020 | 0 | 95000 |  | 0 |
| receipt_013 | 1 | Sữa chua xoài | KM | 0.0 | 1 |  | 0 | 35000 | 35000 | 1 | 35000 | 35000 | 1 |
| receipt_013 | 2 | Sữa chua mít | Sua chua xoai | 0.8 | 1 |  | 0 | 35000 | 35000 | 1 | 35000 | 35000 | 1 |
| receipt_013 | 3 | Trân châu cốt dừa | Tran chau cot | 0.8667 | 1 |  | 0 | 5000 | 5000 | 1 | 5000 | 5000 | 1 |
| receipt_014 | 2 | Trà Sữa Sài-Gòn | Tra Sua Sai-Gon | 1.0 | 1 |  | 0 | 39000 | 39000 | 1 | 39000 | 39000 | 1 |

## Notes

- This evaluator currently uses order-based matching. It assumes the predicted item order follows the receipt order.
- Name matching uses normalized text similarity with a threshold of `0.75`.
- Numeric fields are evaluated with exact equality after number normalization.
- This is a baseline item-level evaluator. Later versions can add fuzzy item alignment and layout-aware matching.
