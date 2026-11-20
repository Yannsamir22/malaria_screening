import hashlib

import pytest

from app.imaging import ImageRejected, inspect_image
from conftest import make_image

pytestmark = pytest.mark.m1


def test_a_good_png_gives_its_facts():
    data = make_image("PNG", (640, 520))
    assert inspect_image(data, min_side=512) == {
        "content_type": "image/png", "width": 640, "height": 520,
        "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


@pytest.mark.parametrize("fmt,mime", [("JPEG", "image/jpeg"), ("TIFF", "image/tiff")])
def test_jpeg_and_tiff_are_accepted(fmt, mime):
    assert inspect_image(make_image(fmt), min_side=512)["content_type"] == mime


def test_text_bytes_are_rejected():
    with pytest.raises(ImageRejected, match="not a readable image"):
        inspect_image(b"this is not an image", min_side=512)


def test_a_truncated_png_is_rejected():
    with pytest.raises(ImageRejected):
        inspect_image(make_image()[:200], min_side=512)


@pytest.mark.parametrize("fmt", ["GIF", "BMP"])
def test_other_formats_are_rejected_and_named(fmt):
    with pytest.raises(ImageRejected, match=fmt):
        inspect_image(make_image(fmt), min_side=512)


def test_a_small_image_is_rejected_with_its_size():
    with pytest.raises(ImageRejected, match="400x300"):
        inspect_image(make_image(size=(400, 300)), min_side=512)
