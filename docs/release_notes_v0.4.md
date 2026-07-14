# Release Notes — v0.4 Streamlit Layout Parser Mode

## Version

`v0.4-streamlit-layout-mode`

## Summary

This release adds a layout-aware item parser mode to the Streamlit OCR demo.

The project now supports two item extraction modes:

* `Text parser v0.3`: the default rule-based text parser.
* `Layout parser v0.4`: a layout-aware item parser candidate using OCR bounding-box row structure.

The default receipt-level extraction pipeline remains rule-based and deterministic. The layout-aware parser only replaces item rows while keeping receipt-level fields from the default parser.

## Main Changes

### Streamlit UI

* Added item parser mode selector in the sidebar.
* Added support for switching between:

  * `Text parser v0.3`
  * `Layout parser v0.4`
* Shortened parser mode labels for a cleaner UI.
* Updated numeric formatting in Streamlit tables.
* Updated screenshots to reflect the new parser mode UI.

### Layout-aware Item Parser

* Added layout-aware item parser candidate.
* Added production-like module:

```text
receipt_ocr/layout_item_parser.py
```

* Added layout-aware extraction script:

```text
scripts/run_layout_item_extraction.py
```

* Added layout-aware item evaluation script:

```text
scripts/evaluate_layout_items.py
```

### Documentation

* Updated README with parser comparison.
* Added layout-aware parser candidate documentation.
* Updated Streamlit screenshots.
* Added layout-aware item evaluation report.

## Current Development Evaluation

MVP development benchmark:

* 15 Vietnamese receipt/invoice images
* 39 ground-truth item rows

### Receipt-level Evaluation

Default parser: `rule_based_v0.3`

| Field          | Accuracy |
| -------------- | -------: |
| Store name     |   80.00% |
| Datetime       |   93.33% |
| Invoice ID     |   86.67% |
| Total amount   |   93.33% |
| Payment method |  100.00% |
| Items count    |  100.00% |
| Overall        |   92.22% |

### Default Item Parser Evaluation

Parser: `Text parser v0.3`

| Item Field                  | Accuracy |
| --------------------------- | -------: |
| Item count                  |  100.00% |
| Item name                   |   84.62% |
| Quantity                    |   74.36% |
| Unit price                  |   97.44% |
| Line total                  |   94.87% |
| Overall item field accuracy |   87.82% |

### Layout-aware Item Parser Evaluation

Parser: `Layout parser v0.4`

| Item Field                  | Accuracy |
| --------------------------- | -------: |
| Item count                  |  100.00% |
| Item name                   |  100.00% |
| Quantity                    |  100.00% |
| Unit price                  |  100.00% |
| Line total                  |  100.00% |
| Overall item field accuracy |  100.00% |

## Important Notes

The layout-aware parser result is measured on the same MVP development benchmark used for parser development and error analysis.

It is not a held-out test result and should not be interpreted as production-level generalization.

The next validation step is to test the layout-aware parser on a larger and more diverse receipt dataset.

## Git Tags

Related milestones:

| Tag                           | Description                                                     |
| ----------------------------- | --------------------------------------------------------------- |
| `v1.0-mvp`                    | Initial Streamlit MVP release                                   |
| `v0.3-rule-based-parser`      | Rule-based parser v0.3 milestone                                |
| `v0.4-layout-aware-candidate` | Layout-aware item parser candidate                              |
| `v0.4-streamlit-layout-mode`  | Streamlit UI with parser mode selection and updated screenshots |

## Known Limitations

* Dataset size is still small.
* Store name extraction remains heuristic-based.
* Receipt-level fields still depend on OCR quality.
* Layout-aware parsing depends on OCR bounding boxes.
* The system has not yet been benchmarked on a large external dataset.
* The layout-aware parser has not yet been validated on many unseen receipt formats.
* Optional LLM/API correction is not part of the core deterministic pipeline.

## Next Steps

1. Validate layout-aware parser on more receipt formats.
2. Add more ground-truth labeled receipts.
3. Improve store name extraction.
4. Add OCR preprocessing experiments.
5. Consider optional LLM-based correction for difficult text fields.
6. Add FastAPI or Docker support if needed.
