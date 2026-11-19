from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.publisher import MemoryPublisher
from app.storage import MemoryImageStorage
from app.store import ScreeningStore
from tests.helpers import make_id_factory, make_ticking_clock
from tests.tokens import SECRET

@pytest.fixture
def parts():
      """ONe group of objects shared by the app AND the test."""
      return SimpleNamespace(
            store=ScreeningStore(new_id=make_id_factory(), clock=make_ticking_clock()),
            storage=MemoryImageStorage(),
            publisher=MemoryPublisher()
      )
      
@pytest.fixture
def store(parts):
      return parts.store

@pytest.fixture
def storage(parts):
      return parts.storage

@pytest.fixture
def publisher(parts):
      return parts.publisher

@pytest.fixture
def client(parts):
      app = create_app(
            Settings(jwt_secret=SECRET), parts.store, parts.storage, parts.publisher
      )
      return TestClient(app)