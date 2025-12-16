"""Department Schemas."""

from typing import Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class DepartmentBase(CamelModel):
    name_en: str = Field(min_length=1, max_length=128)
    name_ar: str = Field(min_length=1, max_length=128)
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(CamelModel):
    name_en: Optional[str] = Field(None, min_length=1, max_length=128)
    name_ar: Optional[str] = Field(None, min_length=1, max_length=128)
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(DepartmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
