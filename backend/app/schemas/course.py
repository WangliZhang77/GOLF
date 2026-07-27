from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CourseBase(BaseModel):
    name_zh: str
    name_en: str | None = None
    address: str | None = None
    city: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    holes: int | None = Field(default=18, ge=1)
    par: int | None = Field(default=None, ge=1)
    rating: Decimal | None = None
    slope: int | None = Field(default=None, ge=55, le=155)
    is_active: bool = True
    remark: str | None = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name_zh: str | None = None
    name_en: str | None = None
    address: str | None = None
    city: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    holes: int | None = Field(default=None, ge=1)
    par: int | None = Field(default=None, ge=1)
    rating: Decimal | None = None
    slope: int | None = Field(default=None, ge=55, le=155)
    is_active: bool | None = None
    remark: str | None = None


class CourseOut(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
