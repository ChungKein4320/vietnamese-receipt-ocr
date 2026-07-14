from __future__ import annotations

from pathlib import Path

import pytest

from receipt_ocr.dataset_manifest import (
    ManifestValidationError,
    load_dataset_manifest,
    summarize_splits,
)


HEADER = "receipt_id,split,image_path,ground_truth_path\n"


def _write_manifest(path: Path, rows: list[str]) -> None:
    path.write_text(HEADER + "".join(rows), encoding="utf-8")


def test_load_manifest_and_summarize_splits(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            "receipt_001,development,data/dev.png,data/dev.json\n",
            "receipt_002,held_out,data/test.png,data/test.json\n",
        ],
    )

    records = load_dataset_manifest(manifest)

    assert [record.receipt_id for record in records] == [
        "receipt_001",
        "receipt_002",
    ]
    assert summarize_splits(records) == {"development": 1, "held_out": 1}


def test_manifest_rejects_legacy_test_split(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        ["receipt_001,test,data/image.png,data/ground_truth.json\n"],
    )

    with pytest.raises(ManifestValidationError, match="split must be one of"):
        load_dataset_manifest(manifest)


def test_manifest_rejects_missing_required_columns(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("receipt_id,split\nreceipt_001,development\n", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="Missing required columns"):
        load_dataset_manifest(manifest)


def test_manifest_rejects_empty_dataset(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [])

    with pytest.raises(ManifestValidationError, match="at least one record"):
        load_dataset_manifest(manifest)


def test_manifest_rejects_duplicate_receipt_id(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            "receipt_001,development,data/one.png,data/one.json\n",
            "receipt_001,held_out,data/two.png,data/two.json\n",
        ],
    )

    with pytest.raises(ManifestValidationError, match="duplicate receipt_id"):
        load_dataset_manifest(manifest)


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.png", "data/../../outside.png", "C:/receipts/outside.png"],
)
def test_manifest_rejects_unsafe_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [f"receipt_001,development,{unsafe_path},data/ground_truth.json\n"],
    )

    with pytest.raises(ManifestValidationError, match="repository-relative path"):
        load_dataset_manifest(manifest)


def test_manifest_can_check_referenced_files(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    image = tmp_path / "data" / "receipt.png"
    ground_truth = tmp_path / "data" / "receipt.json"
    image.parent.mkdir()
    image.write_bytes(b"image")
    ground_truth.write_text("{}", encoding="utf-8")
    _write_manifest(
        manifest,
        ["receipt_001,development,data/receipt.png,data/receipt.json\n"],
    )

    records = load_dataset_manifest(
        manifest,
        project_root=tmp_path,
        check_files=True,
    )

    assert len(records) == 1


def test_manifest_reports_missing_referenced_file(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        ["receipt_001,development,data/missing.png,data/missing.json\n"],
    )

    with pytest.raises(ManifestValidationError, match="does not exist"):
        load_dataset_manifest(
            manifest,
            project_root=tmp_path,
            check_files=True,
        )
