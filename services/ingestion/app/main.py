from fastapi import FastAPI

from app.config import Settings
from app.publisher import MemoryPublisher
from app.storage import MemoryImageStorage
from app.store import ScreeningStore
from app.api import router


def create_app(settings=None, store=None, storage=None, publisher=None):
      app = FastAPI(title="Ingestion services API")

      app.state.settings = settings if settings is not None else Settings.from_env()
      app.state.store = store if store is not None else ScreeningStore()
      app.state.storage = storage if storage is not None else MemoryImageStorage()
      app.state.publisher = publisher if publisher is not None else MemoryPublisher()
      
      app.include_router(router)
      return app