from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SponsorBase(BaseModel):
    company_name: str
    industry: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    level: str | None = None
    is_active: bool = True


class SponsorCreate(SponsorBase):
    pass


class SponsorUpdate(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    level: str | None = None
    is_active: bool | None = None


class SponsorOut(SponsorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SponsorContractBase(BaseModel):
    competition_id: int | None = None
    amount: Decimal
    start_date: date
    end_date: date | None = None
    benefit: str | None = None


class SponsorContractCreate(SponsorContractBase):
    pass


class SponsorContractUpdate(BaseModel):
    competition_id: int | None = None
    amount: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    benefit: str | None = None


class SponsorContractOut(SponsorContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sponsor_id: int
