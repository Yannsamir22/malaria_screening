import pytest

from conformance import SPEC, check_response
from conftest import ONE, URL, auth, upload
from tokens import make_token

pytestmark = pytest.mark.m4


def test_a_full_journey_conforms_to_the_yaml(client):
    tech = auth("technician")
    r = upload(client, tech, patient_reference="P-1", slide_id="S-1", facility="Hopital de Bonamoussadi")
    check_response(r, "POST", URL)
    sid = r.json()["id"]
    for method, url, tpl, headers in [
        ("GET", URL, URL, tech), ("GET", f"{URL}/{sid}", ONE, tech),
        ("GET", f"{URL}/{sid}/image", ONE + "/image", tech)]:
        check_response(client.request(method, url, headers=headers), method, tpl)
    svc = auth("service")
    for target in ("processing", "completed"):
        check_response(client.patch(f"{URL}/{sid}/status", json={"status": target}, headers=svc),
                       "PATCH", ONE + "/status")
    check_response(client.delete(f"{URL}/{sid}", headers=auth("administrator")), "DELETE", ONE)


def test_no_response_leaks_an_internal_field(client):
    allowed = set(SPEC["components"]["schemas"]["Screening"]["properties"])
    body = upload(client, auth("technician")).json()
    assert set(body) <= allowed


def test_a_refresh_token_is_refused(client):
    t = make_token("technician", kind="refresh")
    assert client.get(URL, headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_an_expired_token_is_refused(client):
    t = make_token("technician", ttl=-10)
    assert client.get(URL, headers={"Authorization": f"Bearer {t}"}).status_code == 401
