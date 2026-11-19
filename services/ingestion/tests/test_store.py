import uuid 
from datetime import datetime, timedelta, timezone

from app.store import ScreeningStore

def make_id_factory():
      counter = {"n": 0}
      
      def new_id():
            counter["n"] += 1
            return uuid.UUID(int=counter["n"])
      
      return new_id

def make_ticking_clock():
      state = {"t": datetime(2026, 1, 1, tzinfo=timezone.utc)}

      def clock():
            state["t"] += timedelta(seconds=1)
            return state["t"]

      return clock


def make_store(clock=None):
    return ScreeningStore(new_id=make_id_factory(), clock=clock or make_ticking_clock())


DETAILS = {
    "smear_type": "thin",
    "region_code": "CM-LT",
    "submitted_by": uuid.UUID(int=999),
    "image": {"content_type": "image/png", "width": 600, "height": 600,
              "size_bytes": 10, "sha256": "a" * 64},
}


def test_add_sets_the_basics():
    store = make_store()
    record = store.add(dict(DETAILS))
    assert record["id"] == uuid.UUID(int=1)
    assert record["status"] == "pending"
    assert record["created"] == record["updated"]


def test_add_does_not_modify_the_callers_dict():
    store = make_store()
    details = dict(DETAILS)
    store.add(details)
    assert "id" not in details and "status" not in details


def test_get_returns_a_copy():
    store = make_store()
    record = store.add(dict(DETAILS))
    got = store.get(record["id"])
    got["status"] = "completed"
    got["image"]["width"] = 1
    again = store.get(record["id"])
    assert again["status"] == "pending"
    assert again["image"]["width"] == 600


def test_list_is_newest_first():
    store = make_store()
    for _ in range(3):
        store.add(dict(DETAILS))
    ids = [r["id"].int for r in store.list()]
    assert ids == [3, 2, 1]


def test_list_is_newest_first_when_the_clock_is_frozen():
    frozen = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = make_store(clock=lambda: frozen)
    for _ in range(3):
        store.add(dict(DETAILS))
    ids = [r["id"].int for r in store.list()]
    assert ids == [3, 2, 1]


def test_list_paging():
    store = make_store()
    for _ in range(3):
        store.add(dict(DETAILS))
    page = store.list(limit=1, offset=1)
    assert [r["id"].int for r in page] == [2]