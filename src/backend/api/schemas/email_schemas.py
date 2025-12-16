"""Email Schemas."""

from pydantic import ConfigDict, EmailStr

from api.schemas._base import CamelModel


class EmailBase(CamelModel):
    address: EmailStr
    role_id: int

    model_config = ConfigDict(from_attributes=True)


class EmailCreate(EmailBase):
    pass


class EmailUpdate(CamelModel):
    address: EmailStr
    role_id: int

    model_config = ConfigDict(from_attributes=True)


class EmailResponse(EmailBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
