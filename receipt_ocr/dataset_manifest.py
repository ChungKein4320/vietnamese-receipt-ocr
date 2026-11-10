from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PureWindowsPath


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

    windows_path = PureWindowsPath(value.strip())
    if path.anchor or windows_path.anchor or ".." in windows_path.parts:
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
    root = root.resolve()
    records: list[DatasetRecord] = []
    seen_receipt_ids: set[str] = set()
    seen_paths: dict[str, set[Path]] = {"image_path": set(), "ground_truth_path": set()}

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

            if not re.fullmatch(r"[A-Za-z0-9_-]+", receipt_id):
                raise ManifestValidationError(
                    f"Row {row_number}: receipt_id must contain only letters, digits, underscores, or hyphens."
                )
            normalized_id = receipt_id.casefold()
            if normalized_id in seen_receipt_ids:
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

            for field, relative_path in (
                ("image_path", image_path),
                ("ground_truth_path", ground_truth_path),
            ):
                resolved_path = (root / relative_path).resolve()
                if not resolved_path.is_relative_to(root):
                    raise ManifestValidationError(
                        f"Row {row_number}: {field} must stay inside the repository."
                    )
                if resolved_path in seen_paths[field]:
                    raise ManifestValidationError(f"Row {row_number}: duplicate {field}.")
                seen_paths[field].add(resolved_path)
                if check_files and not resolved_path.is_file():
                    raise ManifestValidationError(
                        f"Row {row_number}: {field} does not exist: {relative_path}"
                    )

            seen_receipt_ids.add(normalized_id)
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

    if check_files and len({record.split for record in records}) > 1:
        image_splits: dict[bytes, str] = {}
        for record in records:
            digest = sha256((root / record.image_path).read_bytes()).digest()
            previous_split = image_splits.setdefault(digest, record.split)
            if previous_split != record.split:
                raise ManifestValidationError("An identical image appears in both dataset splits.")

    return records


def summarize_splits(records: list[DatasetRecord]) -> dict[str, int]:
    counts = Counter(record.split for record in records)
    return {split: counts.get(split, 0) for split in sorted(ALLOWED_SPLITS)}


def records_for_split(
    records: list[DatasetRecord],
    split: str,
) -> list[DatasetRecord]:
    normalized_split = split.strip().lower()

    if normalized_split not in ALLOWED_SPLITS:
        allowed = ", ".join(sorted(ALLOWED_SPLITS))
        raise ManifestValidationError(f"Split must be one of: {allowed}.")

    selected_records = [
        record for record in records if record.split == normalized_split
    ]

    if not selected_records:
        raise ManifestValidationError(
            f"No records found for split '{normalized_split}'."
        )

    return selected_records
