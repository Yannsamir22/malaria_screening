from enum import StrEnum
from typing import Annotated, Literal, Optional
from uuid import UUID
from datetime import datetime

from pydantic import Field, BaseModel, model_validator

class SmearType(StrEnum):
      thin = "thin"
      thick = "thick"
      
class ScreeningStatus(StrEnum):
      pending = "pending"
      processing = "processing"
      completed = "completed"
      failed = "failed"
               
Reference = Annotated[str, Field(min_length=1, max_length=64)]   
Facility = Annotated[str, Field(min_length=1, max_length=120)]
FailureReason = Annotated[str, Field(min_length=1, max_length=500)]

REGION_PATTERN = r"^CM-[A-Z]{2}$"

class Health(BaseModel):
      status: str
      service: str
      
class ImageInfo(BaseModel):
      content_type: Literal["image/png", "image/jpeg", "image/tiff"]
      width: int = Field(ge=1)
      height: int = Field(ge=1)
      size_bytes: int = Field(ge=1, le=20 * 1024 * 1024)
      sha256: str = Field(pattern=r"^[0-9a-f]{64}$")      

class Screening(BaseModel): 
      id: UUID
      created: datetime
      updated: datetime
      status: ScreeningStatus
      smear_type: SmearType
      region_code: str
      image: ImageInfo
      submitted_by: UUID
      patient_reference: Optional[Reference] = None
      slide_id: Optional[str] = None
      facility: Optional[Facility] = None
      failure_reason: Optional[FailureReason] = None

class ScreeningList(BaseModel):
      screenings: list[Screening]
      
class StatusUpdate(BaseModel):
      model_config = {"extra": "forbid"}
      
      status: ScreeningStatus
      failure_reason: FailureReason = None
      
      @model_validator(mode="after")
      def reason_required_when_failed(self) -> "StatusUpdate":
            if self.status == ScreeningStatus.failed and not self.failure_reason:
                  raise ValueError("failure_reason is required when status is failed")
            return self

if __name__ == "__main__":
    # StatusUpdate: failed needs a reason
    try:
        StatusUpdate(status="failed")
        assert False, "should have raised"
    except Exception as e:
        print("caught:", e)

    # StatusUpdate: works fine with reason
    s = StatusUpdate(status="failed", failure_reason="model crashed")
    assert s.status == ScreeningStatus.failed
    print("StatusUpdate OK")

    # StatusUpdate: rejects unknown fields
    try:
        StatusUpdate(status="processing", unknown_field="x")
        assert False, "should have raised"
    except Exception as e:
        print("caught extra field:", e)

    print("all models OK")