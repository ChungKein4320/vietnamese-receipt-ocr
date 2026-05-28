# Error Analysis

## Goal

Analyze the remaining errors of the OCR + rule-based extraction pipeline after the MVP v1 implementation.

This report is generated from:

```text
data/evaluation/evaluation_report.csv
data/evaluation/evaluation_summary.json
```

## Current Evaluation Summary

- Number of receipts: `15`
- Overall accuracy: `72.22%`

### Field-level error buckets

| field | accuracy | accuracy_percent | num_errors | num_receipts | error_rate |
| --- | --- | --- | --- | --- | --- |
| store_name | 0.8 | 80.00% | 3 | 15 | 0.2 |
| datetime | 0.8 | 80.00% | 3 | 15 | 0.2 |
| invoice_id | 0.4 | 40.00% | 9 | 15 | 0.6 |
| total_amount | 0.9333 | 93.33% | 1 | 15 | 0.0667 |
| payment_method | 0.7333 | 73.33% | 4 | 15 | 0.2667 |
| items_count | 0.6667 | 66.67% | 5 | 15 | 0.3333 |

## Field-level Error Details

### store_name

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_005 | SCTC CÔ THỎ 104 TRẦN PHÚ - CẨM PHẢ | PHA | 0.171 |
| receipt_013 | SCTC CÔ THỎ 104 TRẦN PHÚ - CẨM PHẢ | PHA | 0.171 |
| receipt_014 | Tiệm ăn Thanh Xuân | Tim ita | 0.4 |

### datetime

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_012 | 2020-08-14 08:42 |  | 0.0 |
| receipt_013 | 2020-08-10 20:01 | 2020-03-10 | 0.0 |
| receipt_015 | 2020-08-15 09:47 |  | 0.0 |

### invoice_id

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_002 | SO-32 |  | 0.0 |
| receipt_003 | BL.200814.1.00046 |  | 0.0 |
| receipt_005 | 2003000468 |  | 0.0 |
| receipt_008 | SON55598 |  | 0.0 |
| receipt_009 | SO-31 |  | 0.0 |
| receipt_011 | I9810000682020 |  | 0.0 |
| receipt_012 |  | 0333863328-FAX | 0.0 |
| receipt_014 | I00022-550301 |  | 0.0 |
| receipt_015 |  | 0333363328-FAX | 0.0 |

### total_amount

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_011 | 49000 | 67000 | 0.0 |

### payment_method

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_002 | cash | unknown | 0.0 |
| receipt_005 | cash | unknown | 0.0 |
| receipt_009 | cash | unknown | 0.0 |
| receipt_013 | cash | unknown | 0.0 |

### items_count

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_006 | 2 | 3 | 0.5 |
| receipt_007 | 1 | 2 | 0.0 |
| receipt_008 | 5 | 6 | 0.8 |
| receipt_012 | 1 | 2 | 0.0 |
| receipt_015 | 2 | 3 | 0.5 |

## Parser Warnings

| warning | count |
| --- | --- |
| datetime_not_found | 2 |

## Observations

### Strongest field

`total_amount` is currently the strongest field. The main improvement came from normalizing Vietnamese money formats such as `70.000d`, `80.000d`, `20.000d`, and `CASH(VND)-88000`.

### Weakest field

`invoice_id` is currently the weakest field. Receipt IDs appear in many inconsistent formats and can be confused with phone numbers, cashier IDs, receipt titles, or transaction codes.

### Item extraction

`items_count` is still unstable because item names, quantities, unit prices, and line totals are often split across multiple OCR lines. A pure text-based parser has limited layout awareness.

### Payment method

`payment_method` is rule-based and depends on keyword matching. It can fail when OCR misses or corrupts words such as `tien mat`, `cash`, or card-related terms.

## Parser v0.2 Improvement Plan

Recommended priority order:

1. Improve `invoice_id` extraction with stricter receipt-code patterns.
2. Improve `datetime` parsing for split date/time lines and OCR-corrupted separators.
3. Improve `payment_method` keyword normalization.
4. Add item-level evaluation beyond `items_count`.
5. Start layout-aware item parsing using PaddleOCR bounding boxes.

## Next Step

Use this error analysis to implement `rule_based_v0.2` and compare it against `rule_based_v0.1` using the same evaluation pipeline.
