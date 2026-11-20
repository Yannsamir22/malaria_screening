"""M1: POST /screenings, the R-I-S-P pipeline (TODO M1-4 and M1-5)."""
from uuid import UUID

import pytest

from app.publisher import MemoryPublisher
from app.storage import MemoryImageStorage
from app.store import ScreeningStore
from conformance import check_response
from conftest import TECH_A, URL, auth, build_client, make_image, upload

pytestmark = pytest.mark.m1


def test_store_add_sets_the_server_fields(store):
    r = store.add({"smear_type": "thin"})
    assert r["status"] == "pending" and r["created"] == r["updated"] and isinstance(r["id"], UUID)
    r["status"] = "hacked"
    assert store.get(r["id"])["status"] == "pending", "add must return a COPY"


def test_upload_needs_a_token(client):
    r = upload(client, {})
    check_response(r, "POST", URL)
    assert r.status_code == 401


@pytest.mark.parametrize("role", ["clinician", "public_health_officer", "service"])
def test_upload_refuses_other_roles(client, role):
    r = upload(client, auth(role))
    check_response(r, "POST", URL)
    assert r.status_code == 403


def test_upload_creates_a_pending_screening(client, storage, publisher):
    data = make_image()
    r = upload(client, auth("technician", TECH_A), image=data, patient_reference="P-0042")
    check_response(r, "POST", URL)
    body = r.json()
    assert r.status_code == 201
    assert body["status"] == "pending" and body["submitted_by"] == TECH_A
    assert body["patient_reference"] == "P-0042"
    assert body["image"]["content_type"] == "image/png" and body["image"]["size_bytes"] == len(data)
    assert storage.get(body["id"]) == data, "S: the bytes must be stored under the screening id"
    assert [m["screening_id"] for m in publisher.messages] == [body["id"]], "P: one event"


def test_an_administrator_may_upload(client):
    assert upload(client, auth("administrator")).status_code == 201


def test_optional_fields_are_omitted_never_null(client):
    body = upload(client, auth("technician")).json()
    assert "patient_reference" not in body and "slide_id" not in body, (
        "add response_model_exclude_none=True to the decorator")


def test_the_format_comes_from_the_bytes(client):
    r = upload(client, auth("technician"), image=make_image("PNG"),
               filename="slide.jpg", content_type="image/jpeg", smear_type="thick")
    assert r.status_code == 201 and r.json()["image"]["content_type"] == "image/png"


@pytest.mark.parametrize("image", [b"not an image", make_image("GIF"), make_image(size=(400, 400))],
                         ids=["text", "gif", "too-small"])
def test_bad_images_are_422_with_a_message(client, image):
    r = upload(client, auth("technician"), image=image)
    check_response(r, "POST", URL)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_an_image_too_large_is_413():
    r = upload(build_client(max_image_bytes=1000), auth("technician"))
    check_response(r, "POST", URL)
    assert r.status_code == 413


@pytest.mark.parametrize("form", [{"smear_type": "blurry"}, {"region_code": "cm-lt"},
                                  {"patient_reference": "x" * 65}],
                         ids=["smear_type", "region_code", "patient_reference"])
def test_bad_form_fields_are_422(client, form):
    r = upload(client, auth("technician"), **form)
    check_response(r, "POST", URL)
    assert r.status_code == 422 and r.json()["detail"][0]["loc"][0] == "body"


def test_a_missing_image_is_422(client):
    r = client.post(URL, data={"smear_type": "thin", "region_code": "CM-LT"},
                    headers=auth("technician"))
    assert r.status_code == 422


def test_a_publish_failure_does_not_lose_the_upload():
    class BrokenPublisher(MemoryPublisher):
        def publish_screening_created(self, screening):
            raise RuntimeError("broker down")
    assert upload(build_client(publisher=BrokenPublisher()), auth("technician")).status_code == 201


def test_a_storage_failure_leaves_no_record():
    class BrokenStorage(MemoryImageStorage):
        def put(self, key, data, content_type):
            raise RuntimeError("disk full")
    store = ScreeningStore()
    client = build_client(store, BrokenStorage(), raise_errors=False)
    assert upload(client, auth("technician")).status_code == 500
    assert store._rows == {}, "remove the record when storing the bytes fails"
