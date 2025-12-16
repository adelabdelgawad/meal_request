"""Page Schemas with bilingual support and navigation fields."""

from typing import Optional
from pydantic import ConfigDict, Field, model_validator

from api.schemas._base import CamelModel


class PageBase(CamelModel):
    name_en: str = Field(min_length=1, max_length=64, description="Page name in English")
    name_ar: str = Field(min_length=1, max_length=64, description="Page name in Arabic")
    description_en: Optional[str] = Field(None, max_length=256, description="Description in English")
    description_ar: Optional[str] = Field(None, max_length=256, description="Description in Arabic")
    path: Optional[str] = Field(None, max_length=256, description="URL path for the page")
    icon: Optional[str] = Field(None, max_length=64, description="Lucide-react icon name")
    nav_type: Optional[str] = Field(None, max_length=32, description="Navigation type (e.g., primary, sidebar)")
    order: int = Field(default=100, description="Display order in navigation")
    is_menu_group: bool = Field(default=False, description="Whether this is a menu group (no link)")
    show_in_nav: bool = Field(default=True, description="Whether to show in navigation")
    open_in_new_tab: bool = Field(default=False, description="Whether to open in new tab")
    parent_id: Optional[int] = Field(None, description="Parent page ID for hierarchical navigation")
    key: Optional[str] = Field(None, max_length=128, description="Unique key for idempotent seeds")

    model_config = ConfigDict(from_attributes=True)


class PageCreate(PageBase):
    # Accept legacy name field for backward compatibility
    name: Optional[str] = Field(None, description="Legacy name field (maps to name_en)")

    @model_validator(mode='after')
    def map_legacy_name(self):
        """Map legacy name field to bilingual fields if provided."""
        if self.name:
            if not self.name_en or self.name_en == self.name:
                self.name_en = self.name
            if not self.name_ar or self.name_ar == self.name:
                self.name_ar = self.name
        return self


class PageUpdate(CamelModel):
    name_en: Optional[str] = Field(None, min_length=1, max_length=64)
    name_ar: Optional[str] = Field(None, min_length=1, max_length=64)
    description_en: Optional[str] = Field(None, max_length=256)
    description_ar: Optional[str] = Field(None, max_length=256)
    path: Optional[str] = Field(None, max_length=256)
    icon: Optional[str] = Field(None, max_length=64)
    nav_type: Optional[str] = Field(None, max_length=32)
    order: Optional[int] = None
    is_menu_group: Optional[bool] = None
    show_in_nav: Optional[bool] = None
    open_in_new_tab: Optional[bool] = None
    # Accept legacy name field for backward compatibility
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def map_legacy_name(self):
        """Map legacy name field to bilingual fields if provided."""
        if self.name:
            if not self.name_en:
                self.name_en = self.name
            if not self.name_ar:
                self.name_ar = self.name
        return self


class PageResponse(PageBase):
    id: int
    # Computed fields for backward compatibility (set by API layer based on locale)
    name: Optional[str] = Field(None, description="Computed name based on locale")
    description: Optional[str] = Field(None, description="Computed description based on locale")

    model_config = ConfigDict(from_attributes=True)
