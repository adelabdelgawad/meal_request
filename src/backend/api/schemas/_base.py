"""
Base Pydantic models for the application.

CRITICAL: All schema classes must inherit from CamelModel to ensure camelCase
JSON serialization for frontend compatibility and proper UTC datetime handling.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from utils.datetime_utils import ensure_utc


class CamelModel(BaseModel):
    """
    Base model that enforces camelCase aliases and UTC datetime serialization.

    This ensures that:
    - Python code uses snake_case field names (Pythonic convention)
    - JSON API responses use camelCase keys (JavaScript convention)
    - Frontend receives consistent camelCase data
    - Datetimes are always serialized as UTC with 'Z' suffix

    Configuration:
        - alias_generator=to_camel: Automatically generates camelCase aliases
          from snake_case field names
        - populate_by_name=True: Allows input by both field name (snake_case)
          and alias (camelCase) when creating models
        - Datetime serialization: Ensures all datetime fields are in UTC with 'Z' suffix

    Example:
        ```python
        class UserResponse(CamelModel):
            user_id: int
            first_name: str
            is_active: bool
            created_at: datetime

        # Python code uses snake_case
        user = UserResponse(
            user_id=1,
            first_name="John",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )

        # JSON output uses camelCase with UTC datetime
        user.model_dump(by_alias=True)
        # {"userId": 1, "firstName": "John", "isActive": true, "createdAt": "2025-12-12T15:00:00Z"}
        ```

    IMPORTANT: When returning responses from FastAPI endpoints, either:
    1. Return Pydantic model instances directly (FastAPI handles serialization)
    2. Use model.model_dump(by_alias=True) to manually serialize

    DO NOT create new base models or duplicate alias configuration.
    All schemas must inherit from this class.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """
        Override model_dump to ensure datetimes are UTC with 'Z' suffix.

        This method processes all datetime fields to ensure they're in UTC format
        before serialization, providing a consistent API response format.
        """
        data = super().model_dump(**kwargs)
        return self._process_datetimes(data)

    def model_dump_json(self, **kwargs: Any) -> str:
        """
        Override model_dump_json to ensure datetimes are UTC with 'Z' suffix.
        """
        # Convert datetimes to UTC before JSON serialization
        data = self.model_dump(**kwargs)
        # Pydantic's default JSON serializer will handle the ISO format
        from pydantic_core import to_json
        return to_json(data, indent=kwargs.get('indent')).decode()

    @classmethod
    def _process_datetimes(cls, data: Any) -> Any:
        """
        Recursively process data to ensure all datetime objects are UTC-aware.

        This handles:
        - Direct datetime values
        - Datetimes in nested dictionaries
        - Datetimes in lists
        """
        if isinstance(data, datetime):
            # Ensure datetime is UTC-aware and format with 'Z' suffix
            utc_dt = ensure_utc(data)
            return utc_dt.isoformat().replace('+00:00', 'Z')
        elif isinstance(data, dict):
            return {key: cls._process_datetimes(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [cls._process_datetimes(item) for item in data]
        else:
            return data
