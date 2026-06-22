from __future__ import annotations

import cv2
import numpy as np
import pytest

from receipt_ocr.image_preprocessor import (
    apply_adaptive_threshold,
    load_image,
    preprocess_image,
    preprocess_image_file,
    resize_if_large,
    to_grayscale,
)


def make_test_image(width: int = 100, height: int = 60) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.putText(
        image,
        "OCR",
        (8, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )
    return image


def test_to_grayscale_returns_2d_array() -> None:
    image = make_test_image()

    gray = to_grayscale(image)

    assert gray.ndim == 2
    assert gray.shape == image.shape[:2]


def test_resize_if_large_preserves_aspect_ratio() -> None:
    image = make_test_image(width=200, height=100)

    resized = resize_if_large(image, max_width=100)

    assert resized.shape[1] == 100
    assert resized.shape[0] == 50


def test_resize_if_large_keeps_small_image_size() -> None:
    image = make_test_image(width=80, height=40)

    resized = resize_if_large(image, max_width=100)

    assert resized.shape == image.shape
    assert resized is not image


def test_adaptive_threshold_returns_binary_image() -> None:
    image = make_test_image()
    gray = to_grayscale(image)

    thresholded = apply_adaptive_threshold(gray, block_size=10)

    assert thresholded.ndim == 2
    assert set(np.unique(thresholded)).issubset({0, 255})


def test_preprocess_image_default_returns_grayscale() -> None:
    image = make_test_image()

    processed = preprocess_image(image)

    assert processed.ndim == 2
    assert processed.shape == image.shape[:2]


def test_preprocess_image_file_writes_output(tmp_path) -> None:
    input_path = tmp_path / "receipt.png"
    output_path = tmp_path / "receipt_preprocessed.png"
    cv2.imwrite(str(input_path), make_test_image())

    saved_path = preprocess_image_file(input_path, output_path=output_path)

    assert saved_path == output_path
    assert output_path.exists()
    assert load_image(output_path).ndim == 3


def test_load_image_raises_for_missing_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.png"

    with pytest.raises(FileNotFoundError):
        load_image(missing_path)
