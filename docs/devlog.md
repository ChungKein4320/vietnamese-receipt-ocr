# Development Log

## 2026-06-01

Paused active implementation today.

Current stable milestones:
- rule_based_v0.3 parser completed
- optional OCR text correction experiment completed
- layout_aware_item_v0.4_candidate added
- layout-aware item evaluation reached 100% on the same MVP development benchmark used for parser development (not a held-out test)

Next planned work:
- update README for layout-aware parser candidate
- integrate layout-aware item parser into Streamlit as an optional mode
- validate on a larger dataset

## 2026-06-03

Paused active implementation today.

Current project state:
- rule_based_v0.3 remains the default text-based parser.
- layout_aware_item_v0.4_candidate has been integrated into Streamlit as an optional parser mode.
- Streamlit now supports switching between Text parser v0.3 and Layout parser v0.4.
- Next UI polish task: format numeric values in tables, e.g. 10000 -> 10,000.
- Next documentation task: update screenshots to reflect the new parser mode selector.

Planned next steps:
1. Test numeric formatting in Streamlit item/database tables.
2. Update README screenshots.
3. Commit updated screenshots.
4. Tag the Streamlit layout-parser UI milestone if stable.
