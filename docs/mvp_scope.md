# MVP Scope

## Project Name

Vietnamese Receipt/Invoice OCR & Information Extraction System

## Goal

Build an end-to-end OCR and information extraction system for Vietnamese receipts and invoices.

## Input

- Receipt/invoice image files: JPG, JPEG, PNG

## Output

Structured JSON and table output containing extracted receipt fields.

## MVP Fields

### Required

- store_name
- datetime
- items
- total_amount

### Optional

- invoice_id
- quantity
- unit_price
- line_total
- vat
- service_fee
- payment_method

## MVP Pipeline

1. Upload image
2. Preprocess image
3. Run OCR
4. Extract raw text
5. Parse fields using regex/rules
6. Display JSON and item table
7. Save result to SQLite
8. Export JSON/CSV

## Out of Scope

- Training custom OCR model
- Fine-tuning VietOCR
- Complex invoice layout understanding
- Authentication
- Production deployment
- FastAPI backend

## Success Criteria

The MVP is successful if a user can upload a receipt image and receive structured JSON/table output, then save or export the result.