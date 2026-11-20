import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from .config import Settings
from .imaging import ImageRejected, inspect_image
from .publisher import JobPublisher
from .schemas import (REGION_PATTERN, Health, Screening, ScreeningList, ScreeningStatus,
                      SmearType, StatusUpdate)
from .security import Principal, require_roles
from .storage import ImageStorage
from .store import ScreeningStore

log = logging.getLogger("ingestion")
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


def find(store: ScreeningStore, screening_id: UUID) -> dict:
    record = store.get(screening_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Screening {screening_id} not found")
    return record


def load_visible(store: ScreeningStore, screening_id: UUID, who: Principal) -> dict:
    record = find(store, screening_id)
    if who.role == "technician" and record.get("submitted_by") != who.id:
        raise HTTPException(status_code=403, detail="You may only access your own screenings")
    return record


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health() -> Health:
      return Health(status="ok", service="ingestion-service")

@router.post("/screenings", status_code=201, response_model=Screening,
             response_model_exclude_none=True, operation_id="createScreening",
             tags=["screenings"])
async def create_screening(
    image: UploadFile, # the file part of the multipart body
    smear_type: Annotated[SmearType, Form()], # the form part of the multipart body
    region_code: Annotated[str, Form(pattern=REGION_PATTERN)], # the form part of the multipart body
    store: Store, storage:Storage, publisher: Publisher, settings: Cfg,
    who: Uploader,
    patient_reference: Annotated[str | None, Form(min_length=1, max_length=64)] = None, # optional form part of the multipart body
    slide_id: Annotated[str | None, Form(min_length=1, max_length=64)] = None, # optional form part of the multipart body
    facility: Annotated[str | None, Form(min_length=1, max_length=120)] = None, # optional form part of the multipart body
) -> dict:
    # R: read at most the limit +1 byte
    data = await image.read(settings.max_image_bytes + 1)
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="The image is larger than 20 MB")
    
    #I: inspect the bytes
    try:
        info = inspect_image(data, min_side=settings.min_image_side)
    except ImageRejected as exc:
        raise HTTPException(422, str(exc)) from None
    
    # S: store the record, them the bytes
    details = {
        "smear_type": smear_type.value,
        "region_code": region_code,
        "image": info,
        "submitted_by": who.id,
        "patient_reference": patient_reference,
        "slide_id": slide_id,
        "facility": facility
    }
    
    record = store.add({k: v for k, v in details.items() if v is not None})
    try:
        storage.put(str(record["id"]), data, info["content_type"])
    except Exception as exc:
        store.remove(record["id"])
        raise 
    
    # P: Publish the event; a failure must not lose the upload
    try:
        publisher.publish_screening_created(record)
    except Exception:
        log.exception("could not publish screening.created for %s", record["id"])
    return record

@router.get("/screenings", response_model=ScreeningList, response_model_exclude_none=True,
            operation_id="listScreenings", tags=["screenings"])
def list_screenings(
    store: Store, who: Viewer,
    status: ScreeningStatus | None = None,
    smear_type: SmearType | None = None,
    region_code: Annotated[str | None, Query(pattern=REGION_PATTERN)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    owner = who.id if who.role == "technician" else None
    return {"screenings": store.list(status=status, smear_type=smear_type,
                                     region_code=region_code, submitted_by=owner,
                                     limit=limit, offset=offset)}



@router.get("/screenings/{screening_id}", response_model=Screening,
            response_model_exclude_none=True, operation_id="getScreening",
            tags=["screenings"])
def get_screening(screening_id: UUID, store: Store, who: Reader) -> dict:
    return load_visible(store, screening_id, who)



@router.get("/screenings/{screening_id}/image", response_class=Response,
            response_model=None, operation_id="getScreeningImage", tags=["screenings"],
            responses={200: {"content": {"image/png": {}, "image/jpeg": {},
                                         "image/tiff": {}}}})
def get_screening_image(screening_id: UUID, store: Store, storage: Storage,
                        who: Reader) -> Response:
    record = load_visible(store, screening_id, who)
    return Response(content=storage.get(str(screening_id)),
                    media_type=record["image"]["content_type"],
                    headers={"Cache-Control": "private, no-store"})



SCREENING_MOVES: dict[str, set[str]] = {     # from status -> legal target statuses
    "pending": {"processing"},
    "processing": {"completed", "failed"},
}


@router.patch("/screenings/{screening_id}/status", response_model=Screening,
              response_model_exclude_none=True, operation_id="updateScreeningStatus",
              tags=["internal"])
def update_screening_status(screening_id: UUID, body: StatusUpdate, store: Store,
                            _worker: Worker) -> dict:
    record = find(store, screening_id)
    target = body.status.value
    if target not in SCREENING_MOVES.get(record["status"], set()):
        raise HTTPException(
            409, f"Cannot move a screening from {record['status']} to {target}")
    reason = body.failure_reason if target == "failed" else None
    return store.set_status(screening_id, target, reason)



@router.delete("/screenings/{screening_id}", status_code=204,
               operation_id="deleteScreening", tags=["screenings"])
def delete_screening(screening_id: UUID, store: Store, storage: Storage,
                     _admin: Admin) -> None:
    record = find(store, screening_id)
    if record["status"] == "processing":
        raise HTTPException(409, "Cannot delete a screening that is processing")
    store.remove(screening_id)
    storage.delete(str(screening_id))
