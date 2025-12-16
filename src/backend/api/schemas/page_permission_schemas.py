"""Page Permission Schemas."""

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class PagePermissionBase(CamelModel):
    role_id: int
    page_id: int
    created_by_id: int

    model_config = ConfigDict(from_attributes=True)


class PagePermissionCreate(PagePermissionBase):
    pass


class PagePermissionUpdate(CamelModel):
    role_id: int
    page_id: int

    model_config = ConfigDict(from_attributes=True)


class PagePermissionResponse(PagePermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
