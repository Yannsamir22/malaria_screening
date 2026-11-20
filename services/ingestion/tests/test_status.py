
from uuid import UUID

import pytest

from app.schemas import StatusUpdate
from conformance import check_response
from conftest import ONE, UNKNOWN, URL, auth, expect_invalid, upload

pytestmark = pytest.mark.m3

STATUS = ONE + "/status"
STATES = ["pending", "processing", "completed", "failed"]
LEGAL = {("pending", "processing"), ("processing", "completed"), ("processing", "failed")}
ILLEGAL = [(a, b) for a in STATES for b in STATES if (a, b) not in LEGAL]   # 13 pairs


def new_screening(client, store, status="pending"):
    sid = upload(client, auth("technician")).json()["id"]
    if status != "pending":
        store._force_status(UUID(sid), status)        # fixture: put it in any status
    return sid


def patch(client, sid, body, role="service"):
    return client.patch(f"{URL}/{sid}/status", json=body, headers=auth(role))


def test_status_update_rules():
    assert StatusUpdate(status="processing").failure_reason is None
    for bad in ({"status": "failed"}, {"status": "failed", "failure_reason": None},
                {"status": "completed", "unknown": 1}):
        expect_invalid(StatusUpdate, bad, "TODO M3-1 (StatusUpdate)")


def test_store_set_status_refreshes_updated(store):
    rid = store.add({"smear_type": "thin"})["id"]
    before = store.get(rid)["updated"]
    after = store.set_status(rid, "failed", "model crashed")
    assert after["status"] == "failed" and after["failure_reason"] == "model crashed"
    assert after["updated"] > before


@pytest.mark.parametrize("start,target", sorted(LEGAL))
def test_every_legal_move_is_200(client, store, start, target):
    sid = new_screening(client, store, start)
    body = {"status": target, **({"failure_reason": "model crashed"} if target == "failed" else {})}
    r = patch(client, sid, body)
    check_response(r, "PATCH", STATUS)
    assert r.status_code == 200 and r.json()["status"] == target


@pytest.mark.parametrize("start,target", ILLEGAL)
def test_every_other_pair_is_409(client, store, start, target):
    sid = new_screening(client, store, start)
    body = {"status": target, **({"failure_reason": "model crashed"} if target == "failed" else {})}
    r = patch(client, sid, body)
    check_response(r, "PATCH", STATUS)
    assert r.status_code == 409
    assert store.get(UUID(sid))["status"] == start, "a refused move changes nothing"


def test_failed_without_a_reason_is_422(client, store):
    sid = new_screening(client, store, "processing")
    r = patch(client, sid, {"status": "failed"})
    check_response(r, "PATCH", STATUS)
    assert r.status_code == 422


@pytest.mark.parametrize("role", ["administrator", "clinician", "technician"])
def test_only_service_accounts_change_the_status(client, store, role):
    sid = new_screening(client, store)
    assert patch(client, sid, {"status": "processing"}, role).status_code == 403


def test_status_of_an_unknown_screening_is_404(client):
    r = patch(client, UNKNOWN, {"status": "processing"})
    check_response(r, "PATCH", STATUS)
    assert r.status_code == 404


def test_delete_is_for_administrators(client, store):
    sid = new_screening(client, store)
    assert client.delete(f"{URL}/{sid}", headers=auth("technician")).status_code == 403


def test_delete_answers_204_then_404(client, store, storage):
    sid = new_screening(client, store)
    r = client.delete(f"{URL}/{sid}", headers=auth("administrator"))
    check_response(r, "DELETE", ONE)
    assert r.status_code == 204 and r.content == b""
    assert sid not in storage, "delete the image bytes too"
    assert client.delete(f"{URL}/{sid}", headers=auth("administrator")).status_code == 404


def test_delete_while_processing_is_409(client, store):
    sid = new_screening(client, store, "processing")
    r = client.delete(f"{URL}/{sid}", headers=auth("administrator"))
    check_response(r, "DELETE", ONE)
    assert r.status_code == 409
