"""Email Role Schemas."""

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class EmailRoleBase(CamelModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class EmailRoleCreate(EmailRoleBase):
    pass


class EmailRoleUpdate(CamelModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class EmailRoleResponse(EmailRoleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
