from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import Settings
from app.publisher import JobPublisher
from app.schemas import Health
from app.security import Principal, require_roles
from app.storage import ImageStorage
from app.store import ScreeningStore

router = APIRouter(prefix="/api/v1")

# One getter per item stored on app.state
def get_store(request: Request) -> ScreeningStore:
    return request.app.state.store


def get_storage(request: Request) -> ImageStorage:
    return request.app.state.storage


def get_publisher(request: Request) -> JobPublisher:
    return request.app.state.publisher


def get_settings(request: Request) -> Settings:
    return request.app.state.settings

Store = Annotated[ScreeningStore, Depends(get_store)]
Storage = Annotated[ImageStorage, Depends(get_storage)]
Publisher = Annotated[JobPublisher, Depends(get_publisher)]
Cfg = Annotated[Settings, Depends(get_settings)]

# Role aliases: each one declares who may call the route
Uploader = Annotated[Principal, Depends(require_roles("technician", "administrator"))]
Viewer = Annotated[Principal, Depends(require_roles("administrator", "clinician", "technician"))]
Reader = Annotated[
    Principal,
    Depends(require_roles("administrator", "clinician", "technician", "service")),
]
Admin = Annotated[Principal, Depends(require_roles("administrator"))]
Worker = Annotated[Principal, Depends(require_roles("service"))]

@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health() -> Health:
      return Health(status="ok", service="ingestion-service")


