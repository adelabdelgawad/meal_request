"""Log Meal Request Line Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class LogMealRequestLineBase(CamelModel):
    meal_request_line_id: int
    user_id: str
    action: str
    is_successful: bool
    result: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LogMealRequestLineCreate(LogMealRequestLineBase):
    pass


class LogMealRequestLineResponse(LogMealRequestLineBase):
    id: int
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
