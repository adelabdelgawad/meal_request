"""Employee Schemas."""

from typing import List, Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class EmployeeBase(CamelModel):
    code: int
    name_en: Optional[str] = Field(None, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=128)
    is_active: bool = True
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(EmployeeBase):
    # For creation, we need the HRIS employee ID as well
    id: int = Field(..., description="HRIS Employee ID (primary key)")


class EmployeeUpdate(CamelModel):
    name_en: Optional[str] = Field(None, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeResponse(EmployeeBase):
    id: int = Field(..., description="HRIS Employee ID")

    model_config = ConfigDict(from_attributes=True)


# Hierarchical Response Schemas for /employees/grouped endpoint


class EmployeeRecord(CamelModel):
    """Employee info for hierarchical department view."""

    id: int
    code: int
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentNode(CamelModel):
    """Hierarchical department with employees and child departments."""

    id: int
    name_en: str
    name_ar: str
    employees: List[EmployeeRecord] = []
    children: List["DepartmentNode"] = []

    model_config = ConfigDict(from_attributes=True)
