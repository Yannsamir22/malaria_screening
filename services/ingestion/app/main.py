from fastapi import FastAPI

from app.config import Settings
from app.publisher import MemoryPublisher
from app.storage import MemoryImageStorage
from app.store import ScreeningStore


def create_app(settings=None, store=None, storage=None, publisher=None):
      app = FastAPI(title="Ingestion services API")
      
      if settings is None:
            app.state.settings = Settings.from_env()
      if store is None:
            app.state.store = ScreeningStore()
      if storage is None:
            app.state.storage = MemoryImageStorage()
      if publisher is None:
            app.state.publisher = MemoryPublisher()
      
      app.include_router()
      return app