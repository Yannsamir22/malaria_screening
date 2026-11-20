import pytest

from conformance import check_response
from conftest import ONE, TECH_A, TECH_B, UNKNOWN, URL, auth, make_image, upload

pytestmark = pytest.mark.m2


def three_uploads(client):
    """Two by technician A, one by B; returns the ids oldest first."""
    return [upload(client, auth("technician", t), smear_type=s, region_code=g).json()["id"]
            for t, s, g in ((TECH_A, "thin", "CM-LT"), (TECH_B, "thick", "CM-CE"),
                            (TECH_A, "thin", "CM-LT"))]


def test_store_list_filters_orders_and_slices(store):
    ids = [store.add({"status": "pending", "smear_type": s, "region_code": "CM-LT",
                      "submitted_by": None})["id"] for s in ("thin", "thick", "thin")]
    assert [r["id"] for r in store.list()] == ids[::-1], "newest first"
    assert [r["id"] for r in store.list(smear_type="thin")] == [ids[2], ids[0]]
    assert [r["id"] for r in store.list(limit=1, offset=1)] == [ids[1]]


def test_list_is_newest_first_and_paged(client):
    ids = three_uploads(client)
    r = client.get(URL + "?limit=1&offset=1", headers=auth("administrator"))
    check_response(r, "GET", URL)
    assert [s["id"] for s in r.json()["screenings"]] == [ids[1]]


def test_list_filters(client):
    three_uploads(client)
    h = auth("clinician")
    assert len(client.get(URL + "?smear_type=thick", headers=h).json()["screenings"]) == 1
    assert len(client.get(URL + "?region_code=CM-LT", headers=h).json()["screenings"]) == 2
    assert len(client.get(URL + "?status=pending", headers=h).json()["screenings"]) == 3


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "status=lost",
                                   "region_code=cm-lt"])
def test_list_bounds_are_422(client, query):
    r = client.get(f"{URL}?{query}", headers=auth("administrator"))
    check_response(r, "GET", URL)
    assert r.status_code == 422


def test_a_technician_lists_only_their_own(client):
    three_uploads(client)
    assert len(client.get(URL, headers=auth("technician", TECH_A)).json()["screenings"]) == 2
    assert len(client.get(URL, headers=auth("technician", TECH_B)).json()["screenings"]) == 1
    assert len(client.get(URL, headers=auth("administrator")).json()["screenings"]) == 3


@pytest.mark.parametrize("role", ["public_health_officer", "service"])
def test_list_refuses_other_roles(client, role):
    assert client.get(URL, headers=auth(role)).status_code == 403


@pytest.mark.parametrize("role,sub,code", [
    ("technician", TECH_A, 200), ("technician", TECH_B, 403), ("administrator", None, 200),
    ("clinician", None, 200), ("service", None, 200), ("public_health_officer", None, 403)])
def test_get_visibility_matrix(client, role, sub, code):
    sid = upload(client, auth("technician", TECH_A)).json()["id"]
    r = client.get(f"{URL}/{sid}", headers=auth(role, sub))
    check_response(r, "GET", ONE)
    assert r.status_code == code


def test_get_unknown_is_404_with_the_id(client):
    r = client.get(f"{URL}/{UNKNOWN}", headers=auth("clinician"))
    check_response(r, "GET", ONE)
    assert r.status_code == 404 and UNKNOWN in r.json()["detail"]


def test_get_malformed_id_is_422(client):
    r = client.get(f"{URL}/42", headers=auth("clinician"))
    assert r.status_code == 422 and r.json()["detail"][0]["type"] == "uuid_parsing"


def test_image_download_returns_the_same_bytes(client):
    data = make_image("JPEG")
    sid = upload(client, auth("technician", TECH_A), image=data).json()["id"]
    r = client.get(f"{URL}/{sid}/image", headers=auth("service"))
    check_response(r, "GET", ONE + "/image")
    assert r.status_code == 200 and r.content == data
    assert r.headers["content-type"] == "image/jpeg"


def test_image_follows_the_same_access_rules(client):
    sid = upload(client, auth("technician", TECH_A)).json()["id"]
    assert client.get(f"{URL}/{sid}/image", headers=auth("technician", TECH_B)).status_code == 403
    assert client.get(f"{URL}/{UNKNOWN}/image", headers=auth("service")).status_code == 404
