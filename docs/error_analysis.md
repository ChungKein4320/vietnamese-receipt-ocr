# Error Analysis

## Goal

Analyze the remaining errors of the current OCR + rule-based extraction pipeline after the `rule_based_v0.3` milestone.

This report is generated from:

```text
data/evaluation/evaluation_report.csv
data/evaluation/evaluation_summary.json
```

## Current Development Evaluation Summary

This analysis uses the same 15 receipts used during parser development. The figures are development metrics, not held-out test estimates.

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

### Store name

Three receipts had incorrect store names. Two OCR headers collapsed into the same short fragment, and one prediction selected a different header line.

### Datetime

One error changed the month while retaining the day and time.

### Invoice ID

The parser returned no invoice ID on two receipts. The detailed comparisons are kept with the local evaluation artifacts.

### Total amount

On one receipt, the parser selected a larger amount than the annotated payable total.

### payment_method

_No errors detected for this field._

### items_count

_No errors detected for this field._

## Parser Warnings

_No parser warnings found in the current evaluation report._

## Observations

### Strongest field

`payment_method` and `items_count` currently have no errors on the MVP development benchmark. `total_amount` is also strong after improving Vietnamese money normalization for formats such as `70.000d`, `80.000d`, `20.000d`, and `CASH(VND)-88000`.

### Weakest field

Store name had the lowest accuracy. Invoice IDs were the next most error-prone field. Receipt IDs appear in many inconsistent formats and can be confused with phone numbers, cashier IDs, receipt titles, or transaction codes.

### Item extraction

`items_count` is correct on the current MVP development benchmark, but full item-field extraction is still harder for the text-based parser because item names, quantities, unit prices, and line totals are often split across multiple OCR lines. A pure text-based parser has limited layout awareness.

### Payment method

`payment_method` is rule-based and depends on keyword matching. It can fail when OCR misses or corrupts words such as `tien mat`, `cash`, or card-related terms.

## Current Improvement Plan

Recommended priority order:

1. Improve `store_name` extraction for distorted receipt headers.
2. Improve `invoice_id` extraction with stricter receipt-code patterns and better filtering against phone/cashier/order IDs.
3. Validate the layout-aware item parser on more receipt layouts beyond the current MVP set.
4. Add confidence-based warnings for suspicious predictions.
5. Maintain a standalone synthetic receipt for public smoke testing.
6. Keep unit tests for normalizer and parser utilities up to date.

## Next Step

Use this error analysis to guide the next parser milestone and compare future changes against `rule_based_v0.3` and `layout_aware_item_v0.4_candidate` using the same evaluation pipeline.
