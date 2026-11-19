from app.storage import MemoryImageStorage
from app.publisher import MemoryPublisher

def test_storage_put_and_get():
    storage = MemoryImageStorage()
    storage.put("key-1", b"hello bytes", "image/png")
    assert storage.get("key-1") == b"hello bytes"

def test_storage_delete_is_harmless():
    storage = MemoryImageStorage()
    storage.delete("does-not-exist")  # should not raise

# def test_publisher_records_event():
#     from app.store import ScreeningStore  # type: ignore # we haven't written this yet
#     # skip for now — come back after Step 7
#     pass

def test_publisher_appends_message():
    publisher = MemoryPublisher()
    fake_screening = {
        "id": __import__("uuid").uuid4(),
        "smear_type": "thin",
        "region_code": "CM-LT",
        "created": __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc),
    }
    publisher.publish_screening_created(fake_screening)
    assert len(publisher.messages) == 1
    assert publisher.messages[0]["event"] == "screening.created"
    assert publisher.messages[0]["smear_type"] == "thin"