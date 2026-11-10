# Synthetic Demo Receipt

This receipt was drawn for the public demo. The store, transaction, date, and purchases are fictional. The fixture is separate from the private 15-receipt development benchmark and from any held-out data.

| File | Contents |
| --- | --- |
| `synthetic_receipt.png` | Rendered receipt marked **Synthetic Demo Receipt** |
| `synthetic_receipt_ocr.txt` | Text recognized by PaddleOCR |
| `synthetic_receipt_ocr.json` | Recognized text, confidence scores, and four-point bounding boxes |
| `synthetic_receipt_ground_truth.json` | Expected fields and items transcribed from the fixture design |
| `synthetic_receipt_extracted.json` | Output from the default text parser |
| `synthetic_receipt_layout_extracted.json` | Output from the layout-aware item candidate |

Upload the image in Streamlit to try both parser modes, SQLite, and the JSON/CSV downloads. The saved OCR artifacts were produced on CPU with PaddleOCR 2.7.3, PaddlePaddle 2.6.2, and the English recognition baseline. The README screenshots were captured using this image and an empty demo database.
