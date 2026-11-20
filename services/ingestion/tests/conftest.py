"""Shared test helpers and fixtures. PROVIDED: do not edit (the marking uses its own copy)."""
import io
from datetime import datetime, timedelta, timezone
from itertools import count
from uuid import NAMESPACE_DNS, uuid5

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app
from app.publisher import MemoryPublisher
from app.storage import MemoryImageStorage
from app.store import ScreeningStore
from tokens import SECRET, make_token

NS = uuid5(NAMESPACE_DNS, "malaria-screening.example")
URL = "/api/v1/screenings"
ONE = "/api/v1/screenings/{screening_id}"
TECH_A = str(uuid5(NS, "user:technician-a"))
TECH_B = str(uuid5(NS, "user:technician-b"))
UNKNOWN = str(uuid5(NS, "screening:nobody"))


def sequential_ids():
    n = count(1)
    return lambda: uuid5(NS, f"screening:test-{next(n)}")


def ticking_clock():
    start, n = datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc), count()
    return lambda: start + timedelta(minutes=next(n))


def expect_invalid(model, data, todo, what=None):
    """Validation of *data* must fail; otherwise say which TODO to work on."""
    from pydantic import ValidationError
    try:
        model.model_validate(data)
    except ValidationError:
        return
    raise AssertionError(f"{todo}: {model.__name__} accepted {what or data!r}, which the YAML forbids")


def auth(role, sub=None):
    return {"Authorization": f"Bearer {make_token(role, sub)}"}


def make_image(fmt="PNG", size=(640, 640)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format=fmt)
    return buf.getvalue()


def upload(client, headers, *, image=None, filename="slide.png", content_type="image/png", **form):
    """POST /screenings as multipart (files= for the image, data= for the form fields)."""
    data = {"smear_type": "thin", "region_code": "CM-LT", **form}
    body = make_image() if image is None else image
    return client.post(URL, files={"image": (filename, body, content_type)},
                       data=data, headers=headers)


def build_client(store=None, storage=None, publisher=None, *, raise_errors=True, **settings):
    app = create_app(Settings(jwt_secret=SECRET, **settings),
                     store or ScreeningStore(new_id=sequential_ids(), clock=ticking_clock()),
                     storage or MemoryImageStorage(), publisher or MemoryPublisher())
    return TestClient(app, raise_server_exceptions=raise_errors)


@pytest.fixture
def store():
    return ScreeningStore(new_id=sequential_ids(), clock=ticking_clock())


@pytest.fixture
def storage():
    return MemoryImageStorage()


@pytest.fixture
def publisher():
    return MemoryPublisher()


@pytest.fixture
def client(store, storage, publisher):
    return build_client(store, storage, publisher)
