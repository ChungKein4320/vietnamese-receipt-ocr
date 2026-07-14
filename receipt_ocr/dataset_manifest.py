from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ALLOWED_SPLITS = frozenset({"development", "held_out"})
REQUIRED_COLUMNS = frozenset(
    {"receipt_id", "split", "image_path", "ground_truth_path"}
)


class ManifestValidationError(ValueError):
    """Raised when a dataset manifest violates the evaluation contract."""


@dataclass(frozen=True)
class DatasetRecord:
    receipt_id: str
    split: str
    image_path: Path
    ground_truth_path: Path


def _relative_path(value: str, field: str, row_number: int) -> Path:
    path = Path(value.strip())

    if not value.strip():
        raise ManifestValidationError(
            f"Row {row_number}: {field} must not be empty."
        )

    if path.is_absolute() or ".." in path.parts:
        raise ManifestValidationError(
            f"Row {row_number}: {field} must be a safe repository-relative path."
        )

    return path


def load_dataset_manifest(
    manifest_path: str | Path,
    *,
    project_root: str | Path | None = None,
    check_files: bool = False,
) -> list[DatasetRecord]:
    """Load and validate development/held-out dataset membership."""
    manifest_path = Path(manifest_path)

    if not manifest_path.is_file():
        raise ManifestValidationError(f"Manifest not found: {manifest_path}")

    root = Path(project_root) if project_root is not None else Path.cwd()
    records: list[DatasetRecord] = []
    seen_receipt_ids: set[str] = set()

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_COLUMNS - columns)

        if missing_columns:
            raise ManifestValidationError(
                "Missing required columns: " + ", ".join(missing_columns)
            )

        for row_number, row in enumerate(reader, start=2):
            receipt_id = (row.get("receipt_id") or "").strip()
            split = (row.get("split") or "").strip().lower()

            if not receipt_id:
                raise ManifestValidationError(
                    f"Row {row_number}: receipt_id must not be empty."
                )

            if receipt_id in seen_receipt_ids:
                raise ManifestValidationError(
                    f"Row {row_number}: duplicate receipt_id '{receipt_id}'."
                )

            if split not in ALLOWED_SPLITS:
                allowed = ", ".join(sorted(ALLOWED_SPLITS))
                raise ManifestValidationError(
                    f"Row {row_number}: split must be one of: {allowed}."
                )

            image_path = _relative_path(
                row.get("image_path") or "",
                "image_path",
                row_number,
            )
            ground_truth_path = _relative_path(
                row.get("ground_truth_path") or "",
                "ground_truth_path",
                row_number,
            )

            if check_files:
                for field, relative_path in (
                    ("image_path", image_path),
                    ("ground_truth_path", ground_truth_path),
                ):
                    if not (root / relative_path).is_file():
                        raise ManifestValidationError(
                            f"Row {row_number}: {field} does not exist: "
                            f"{relative_path}"
                        )

            seen_receipt_ids.add(receipt_id)
            records.append(
                DatasetRecord(
                    receipt_id=receipt_id,
                    split=split,
                    image_path=image_path,
                    ground_truth_path=ground_truth_path,
                )
            )

    if not records:
        raise ManifestValidationError("Manifest must contain at least one record.")

    return records


def summarize_splits(records: list[DatasetRecord]) -> dict[str, int]:
    counts = Counter(record.split for record in records)
    return {split: counts.get(split, 0) for split in sorted(ALLOWED_SPLITS)}
