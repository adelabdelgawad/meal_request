"""Department Assignment Schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class DepartmentAssignmentBase(CamelModel):
    user_id: UUID
    department_id: int
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True)


class DepartmentAssignmentCreate(DepartmentAssignmentBase):
    pass


class DepartmentAssignmentUpdate(CamelModel):
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True)


class DepartmentAssignmentResponse(DepartmentAssignmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
