from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas import ImageInfo, Screening
from conftest import expect_invalid

pytestmark = pytest.mark.m1

GOOD_INFO = {"content_type": "image/png", "width": 640, "height": 480,
             "size_bytes": 1000, "sha256": "a" * 64}


@pytest.mark.parametrize("field,bad", [
    ("content_type", "image/gif"), ("width", 0), ("height", 0),
    ("size_bytes", 0), ("size_bytes", 20 * 1024 * 1024 + 1),
    ("sha256", "A" * 64), ("sha256", "abc")])
def test_image_info_refuses_values_the_yaml_forbids(field, bad):
    expect_invalid(ImageInfo, {**GOOD_INFO, field: bad}, "TODO M1-1 (ImageInfo)", f"{field}={bad!r}")
    assert ImageInfo.model_validate(GOOD_INFO).width == 640, "TODO M1-1: declare the ImageInfo fields"


def record(**extra):
    now = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc)
    return {"id": uuid4(), "created": now, "updated": now, "status": "pending",
            "smear_type": "thin", "region_code": "CM-LT", "image": GOOD_INFO,
            "submitted_by": uuid4(), **extra}


def test_screening_drops_internal_fields():
    dumped = Screening.model_validate(record(storage_key="secret/path")).model_dump()
    assert "storage_key" not in dumped, (
        "TODO M1-2: Screening must declare the YAML fields only (a whitelist), "
        "so internal keys of the store never leave the server")


def test_screening_optional_fields_default_to_none():
    s = Screening.model_validate(record())
    for name in ("patient_reference", "slide_id", "facility", "failure_reason"):
        assert getattr(s, name, "MISSING") is None, f"TODO M1-2: declare {name} with default None"


@pytest.mark.parametrize("field,bad", [("region_code", "cm-lt"), ("status", "lost"),
                                       ("smear_type", "blurry")])
def test_screening_checks_its_values(field, bad):
    expect_invalid(Screening, record(**{field: bad}), "TODO M1-2 (Screening)", f"{field}={bad!r}")
