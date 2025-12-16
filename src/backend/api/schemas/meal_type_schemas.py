"""Meal Type Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class MealTypeBase(CamelModel):
    name_en: str = Field(min_length=1, max_length=64)
    name_ar: str = Field(min_length=1, max_length=64)
    priority: int = Field(default=0, ge=0, description="Higher value = higher priority (default selection)")

    model_config = ConfigDict(from_attributes=True)


class MealTypeCreate(MealTypeBase):
    created_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MealTypeUpdate(CamelModel):
    name_en: Optional[str] = Field(None, min_length=1, max_length=64)
    name_ar: Optional[str] = Field(None, max_length=64)
    priority: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    updated_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MealTypeResponse(CamelModel):
    id: int
    name_en: str
    name_ar: str
    priority: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
