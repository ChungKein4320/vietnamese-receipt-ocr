from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReceiptItem:
    name: str
    quantity: int | float | None = None
    unit_price: int | None = None
    line_total: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
        }


@dataclass
class ReceiptExtractionResult:
    receipt_id: str
    source_ocr_path: str | None = None
    store_name: str | None = None
    datetime: str | None = None
    invoice_id: str | None = None
    items: list[ReceiptItem] = field(default_factory=list)
    vat: int | None = None
    service_fee: int | None = None
    total_amount: int | None = None
    payment_method: str = "unknown"
    num_ocr_lines: int = 0
    parser_version: str = "rule_based_v0.2"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "source_ocr_path": self.source_ocr_path,
            "store_name": self.store_name,
            "datetime": self.datetime,
            "invoice_id": self.invoice_id,
            "items": [item.to_dict() for item in self.items],
            "vat": self.vat,
            "service_fee": self.service_fee,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "num_ocr_lines": self.num_ocr_lines,
            "parser_version": self.parser_version,
            "warnings": self.warnings,
        }