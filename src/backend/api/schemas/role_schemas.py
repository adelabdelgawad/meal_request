"""
Role Schemas - Pydantic DTOs for Role entity with bilingual support.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from api.schemas._base import CamelModel


class RoleBase(CamelModel):
    """Base role schema with bilingual fields."""

    name_en: str = Field(min_length=1, max_length=64, description="Role name in English")
    name_ar: str = Field(min_length=1, max_length=64, description="Role name in Arabic")
    description_en: Optional[str] = Field(None, max_length=256, description="Description in English")
    description_ar: Optional[str] = Field(None, max_length=256, description="Description in Arabic")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""

    # Accept legacy name field for backward compatibility
    name: Optional[str] = Field(None, description="Legacy name field (maps to name_en)")
    description: Optional[str] = Field(None, description="Legacy description field (maps to description_en)")

    @model_validator(mode='after')
    def map_legacy_fields(self):
        """Map legacy name/description fields to bilingual fields if provided."""
        if self.name:
            if not self.name_en or self.name_en == self.name:
                self.name_en = self.name
            if not self.name_ar or self.name_ar == self.name:
                self.name_ar = self.name
        if self.description:
            if not self.description_en or self.description_en == self.description:
                self.description_en = self.description
            if not self.description_ar or self.description_ar == self.description:
                self.description_ar = self.description
        return self


class RoleUpdate(CamelModel):
    """Schema for updating a role."""

    name_en: Optional[str] = Field(None, min_length=1, max_length=64)
    name_ar: Optional[str] = Field(None, min_length=1, max_length=64)
    description_en: Optional[str] = Field(None, max_length=256)
    description_ar: Optional[str] = Field(None, max_length=256)
    is_active: Optional[bool] = Field(None, description="Role active status")
    # Accept legacy fields for backward compatibility
    name: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode='after')
    def map_legacy_fields(self):
        """Map legacy name/description fields to bilingual fields if provided."""
        if self.name:
            if not self.name_en:
                self.name_en = self.name
            if not self.name_ar:
                self.name_ar = self.name
        if self.description:
            if not self.description_en:
                self.description_en = self.description
            if not self.description_ar:
                self.description_ar = self.description
        return self


class RoleResponse(RoleBase):
    """Schema for returning role data in API responses."""

    id: int
    is_active: bool = Field(default=True, description="Role active status")
    created_at: datetime
    updated_at: datetime
    # Computed fields for backward compatibility (set by API layer based on locale)
    name: Optional[str] = Field(None, description="Computed name based on locale")
    description: Optional[str] = Field(None, description="Computed description based on locale")


class RoleStatusUpdate(CamelModel):
    """Schema for updating role status."""

    is_active: bool = Field(description="New active status")


class SimpleRole(CamelModel):
    """Simple role schema for dropdowns and lists."""

    id: int
    name: str
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    total_users: Optional[int] = Field(None, description="Number of users with this role")


class RolePagesUpdate(CamelModel):
    """Schema for updating role page assignments."""

    page_ids: list[int] = Field(description="List of page IDs to assign to the role")


class RoleUsersUpdate(CamelModel):
    """Schema for updating role user assignments."""

    user_ids: list[str] = Field(description="List of user IDs to assign to the role")


class RolePageInfo(CamelModel):
    """Page info in role context."""

    id: int
    name_en: str
    name_ar: str
    name: Optional[str] = None  # Computed based on locale


class RoleUserInfo(CamelModel):
    """User info in role context."""

    id: str
    username: str
    full_name: Optional[str] = None


class RolePagesResponse(CamelModel):
    """Response for role pages."""

    role_id: int
    pages: list[RolePageInfo]
    total: int


class RoleUsersResponse(CamelModel):
    """Response for role users."""

    role_id: int
    users: list[RoleUserInfo]
    total: int
