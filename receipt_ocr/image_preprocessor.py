from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from receipt_ocr.config import PROCESSED_IMAGE_DIR


ImageArray = np.ndarray


def load_image(image_path: str | Path) -> ImageArray:
    """
    Load an image from disk using OpenCV.

    OpenCV reads images in BGR format. This function keeps the BGR format because
    the rest of the preprocessing utilities use OpenCV operations directly.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Unable to read image file: {image_path}")

    return image


def save_image(image: ImageArray, output_path: str | Path) -> Path:
    """
    Save an image to disk and return the output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(str(output_path), image)

    if not success:
        raise ValueError(f"Unable to save image to: {output_path}")

    return output_path


def resize_if_large(image: ImageArray, max_width: int = 1600) -> ImageArray:
    """
    Resize an image only when its width is larger than max_width.

    Keeping the original image when it is already small avoids unnecessary
    interpolation and makes preprocessing safer for OCR experiments.
    """
    if max_width <= 0:
        raise ValueError("max_width must be greater than 0")

    height, width = image.shape[:2]

    if width <= max_width:
        return image.copy()

    scale = max_width / width
    new_height = max(1, int(round(height * scale)))

    return cv2.resize(image, (max_width, new_height), interpolation=cv2.INTER_AREA)


def to_grayscale(image: ImageArray) -> ImageArray:
    """
    Convert an image to grayscale.

    Supports grayscale, BGR, and BGRA images.
    """
    if image.ndim == 2:
        return image.copy()

    if image.ndim != 3:
        raise ValueError("image must be a 2D grayscale or 3D color array")

    channels = image.shape[2]

    if channels == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    raise ValueError("image must have 1, 3, or 4 channels")


def denoise_image(gray_image: ImageArray, h: int = 10) -> ImageArray:
    """
    Apply light denoising to a grayscale image.
    """
    if gray_image.ndim != 2:
        raise ValueError("denoise_image expects a grayscale image")

    return cv2.fastNlMeansDenoising(gray_image, None, h=h)


def apply_adaptive_threshold(
    gray_image: ImageArray,
    block_size: int = 31,
    c: int = 10,
) -> ImageArray:
    """
    Apply adaptive thresholding to a grayscale image.

    This is optional because thresholding may help some receipts but hurt others.
    """
    if gray_image.ndim != 2:
        raise ValueError("apply_adaptive_threshold expects a grayscale image")

    if block_size < 3:
        raise ValueError("block_size must be at least 3")

    if block_size % 2 == 0:
        block_size += 1

    return cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )


def preprocess_image(
    image: ImageArray,
    max_width: int = 1600,
    denoise: bool = False,
    threshold: bool = False,
) -> ImageArray:
    """
    Run a conservative preprocessing pipeline for receipt OCR experiments.

    Default behavior only resizes large images and converts them to grayscale.
    Denoising and thresholding are optional because OCR performance can vary by
    receipt quality and camera conditions.
    """
    processed = resize_if_large(image, max_width=max_width)
    processed = to_grayscale(processed)

    if denoise:
        processed = denoise_image(processed)

    if threshold:
        processed = apply_adaptive_threshold(processed)

    return processed


def preprocess_image_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    max_width: int = 1600,
    denoise: bool = False,
    threshold: bool = False,
) -> Path:
    """
    Preprocess one image file and save the result.

    If output_path is not provided, the processed image is saved to
    data/processed/images/<original_stem>_preprocessed.png.
    """
    input_path = Path(input_path)
    image = load_image(input_path)
    processed = preprocess_image(
        image,
        max_width=max_width,
        denoise=denoise,
        threshold=threshold,
    )

    if output_path is None:
        output_path = PROCESSED_IMAGE_DIR / f"{input_path.stem}_preprocessed.png"

    return save_image(processed, output_path)
