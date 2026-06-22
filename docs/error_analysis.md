# Error Analysis

## Goal

Analyze the remaining errors of the current OCR + rule-based extraction pipeline after the `rule_based_v0.3` milestone.

This report is generated from:

```text
data/evaluation/evaluation_report.csv
data/evaluation/evaluation_summary.json
```

## Current Evaluation Summary

- Number of receipts: `15`
- Overall accuracy: `92.22%`

### Field-level error buckets

| field | accuracy | accuracy_percent | num_errors | num_receipts | error_rate |
| --- | --- | --- | --- | --- | --- |
| store_name | 0.8 | 80.00% | 3 | 15 | 0.2 |
| datetime | 0.9333 | 93.33% | 1 | 15 | 0.0667 |
| invoice_id | 0.8667 | 86.67% | 2 | 15 | 0.1333 |
| total_amount | 0.9333 | 93.33% | 1 | 15 | 0.0667 |
| payment_method | 1.0 | 100.00% | 0 | 15 | 0.0 |
| items_count | 1.0 | 100.00% | 0 | 15 | 0.0 |

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
| receipt_013 | 2020-08-10 20:01 | 2020-03-10 20:01 | 0.0 |

### invoice_id

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_013 | 2003000874 |  | 0.0 |
| receipt_014 | I00022-550301 |  | 0.0 |

### total_amount

| receipt_id | ground_truth | prediction | score |
| --- | --- | --- | --- |
| receipt_011 | 49000 | 67000 | 0.0 |

### payment_method

_No errors detected for this field._

### items_count

_No errors detected for this field._

## Parser Warnings

_No parser warnings found in the current evaluation report._

## Observations

### Strongest field

`payment_method` and `items_count` currently have no errors on the MVP dataset. `total_amount` is also strong after improving Vietnamese money normalization for formats such as `70.000d`, `80.000d`, `20.000d`, and `CASH(VND)-88000`.

### Weakest field

`invoice_id` is currently the weakest field. Receipt IDs appear in many inconsistent formats and can be confused with phone numbers, cashier IDs, receipt titles, or transaction codes.

### Item extraction

`items_count` is correct on the current MVP dataset, but full item-field extraction is still harder for the text-based parser because item names, quantities, unit prices, and line totals are often split across multiple OCR lines. A pure text-based parser has limited layout awareness.

### Payment method

`payment_method` is rule-based and depends on keyword matching. It can fail when OCR misses or corrupts words such as `tien mat`, `cash`, or card-related terms.

## Current Improvement Plan

Recommended priority order:

1. Improve `store_name` extraction for distorted receipt headers.
2. Improve `invoice_id` extraction with stricter receipt-code patterns and better filtering against phone/cashier/order IDs.
3. Validate the layout-aware item parser on more receipt layouts beyond the current MVP set.
4. Add confidence-based warnings for suspicious predictions.
5. Add a small reproducible sample dataset for GitHub users.
6. Keep unit tests for normalizer and parser utilities up to date.

## Next Step

Use this error analysis to guide the next parser milestone and compare future changes against `rule_based_v0.3` and `layout_aware_item_v0.4_candidate` using the same evaluation pipeline.
