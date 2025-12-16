"""Meal Request Status Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class MealRequestStatusBase(CamelModel):
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class MealRequestStatusCreate(MealRequestStatusBase):
    pass


class MealRequestStatusUpdate(CamelModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class MealRequestStatusResponse(MealRequestStatusBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
