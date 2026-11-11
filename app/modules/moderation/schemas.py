import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    action: str
    target_type: str
    target_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="extra_metadata")
    created_at: datetime

