from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from receipt_ocr.config import DATABASE_DIR, DATABASE_PATH


def get_connection(db_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """
    Create a SQLite connection.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


def init_database(db_path: str | Path = DATABASE_PATH) -> None:
    """
    Initialize SQLite database tables.
    """
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT NOT NULL UNIQUE,
                source_ocr_path TEXT,
                store_name TEXT,
                datetime TEXT,
                invoice_id TEXT,
                vat INTEGER,
                service_fee INTEGER,
                total_amount INTEGER,
                payment_method TEXT,
                num_ocr_lines INTEGER,
                parser_version TEXT,
                warnings_json TEXT,
                raw_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_db_id INTEGER NOT NULL,
                item_index INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity REAL,
                unit_price INTEGER,
                line_total INTEGER,
                FOREIGN KEY (receipt_db_id)
                    REFERENCES receipts(id)
                    ON DELETE CASCADE
            );
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_receipt_id
            ON receipts(receipt_id);
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipt_items_receipt_db_id
            ON receipt_items(receipt_db_id);
            """
        )


def _as_result_dict(result: Any) -> dict[str, Any]:
    """
    Accept either a dataclass result with to_dict() or a plain dictionary.
    """
    if hasattr(result, "to_dict"):
        return result.to_dict()

    if isinstance(result, dict):
        return result

    raise TypeError("result must be a dict or an object with to_dict().")


def save_extraction_to_db(
    result: Any,
    db_path: str | Path = DATABASE_PATH,
    replace: bool = True,
) -> int:
    """
    Save one extraction result to SQLite.

    If replace=True, existing receipt_id will be overwritten.
    """
    init_database(db_path)

    result_dict = _as_result_dict(result)
    receipt_id = result_dict["receipt_id"]

    with get_connection(db_path) as connection:
        if replace:
            existing = connection.execute(
                "SELECT id FROM receipts WHERE receipt_id = ?;",
                (receipt_id,),
            ).fetchone()

            if existing is not None:
                connection.execute(
                    "DELETE FROM receipts WHERE id = ?;",
                    (existing["id"],),
                )

        cursor = connection.execute(
            """
            INSERT INTO receipts (
                receipt_id,
                source_ocr_path,
                store_name,
                datetime,
                invoice_id,
                vat,
                service_fee,
                total_amount,
                payment_method,
                num_ocr_lines,
                parser_version,
                warnings_json,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                result_dict.get("receipt_id"),
                result_dict.get("source_ocr_path"),
                result_dict.get("store_name"),
                result_dict.get("datetime"),
                result_dict.get("invoice_id"),
                result_dict.get("vat"),
                result_dict.get("service_fee"),
                result_dict.get("total_amount"),
                result_dict.get("payment_method"),
                result_dict.get("num_ocr_lines"),
                result_dict.get("parser_version"),
                json.dumps(result_dict.get("warnings", []), ensure_ascii=False),
                json.dumps(result_dict, ensure_ascii=False),
            ),
        )

        receipt_db_id = int(cursor.lastrowid)

        for item_index, item in enumerate(result_dict.get("items", []), start=1):
            connection.execute(
                """
                INSERT INTO receipt_items (
                    receipt_db_id,
                    item_index,
                    name,
                    quantity,
                    unit_price,
                    line_total
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    receipt_db_id,
                    item_index,
                    item.get("name"),
                    item.get("quantity"),
                    item.get("unit_price"),
                    item.get("line_total"),
                ),
            )

        return receipt_db_id


def fetch_all_receipts(db_path: str | Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """
    Fetch all saved receipt rows.
    """
    init_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                receipt_id,
                store_name,
                datetime,
                invoice_id,
                total_amount,
                payment_method,
                num_ocr_lines,
                parser_version,
                created_at,
                updated_at
            FROM receipts
            ORDER BY created_at DESC, id DESC;
            """
        ).fetchall()

    return [dict(row) for row in rows]


def fetch_items_for_receipt(
    receipt_db_id: int,
    db_path: str | Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """
    Fetch item rows for one saved receipt.
    """
    init_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                item_index,
                name,
                quantity,
                unit_price,
                line_total
            FROM receipt_items
            WHERE receipt_db_id = ?
            ORDER BY item_index ASC;
            """,
            (receipt_db_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def fetch_all_items(db_path: str | Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """
    Fetch all item rows joined with receipt_id.
    """
    init_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                r.receipt_id,
                r.store_name,
                r.datetime,
                i.item_index,
                i.name,
                i.quantity,
                i.unit_price,
                i.line_total
            FROM receipt_items i
            JOIN receipts r
                ON i.receipt_db_id = r.id
            ORDER BY r.created_at DESC, r.id DESC, i.item_index ASC;
            """
        ).fetchall()

    return [dict(row) for row in rows]


def count_receipts(db_path: str | Path = DATABASE_PATH) -> int:
    """
    Count saved receipts.
    """
    init_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM receipts;").fetchone()

    return int(row["count"])