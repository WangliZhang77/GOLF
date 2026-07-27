from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.sponsor import Sponsor, SponsorContract
from app.models.user import User, UserRole
from app.schemas.sponsor import (
    SponsorContractCreate,
    SponsorContractOut,
    SponsorContractUpdate,
    SponsorCreate,
    SponsorOut,
    SponsorUpdate,
)

router = APIRouter(prefix="/sponsors", tags=["sponsor"])

_MANAGE_ROLES = {UserRole.super_admin, UserRole.council_admin}


def _get_sponsor(db: Session, sponsor_id: int) -> Sponsor:
    s = (
        db.query(Sponsor)
        .filter(Sponsor.id == sponsor_id, Sponsor.is_deleted.is_(False))
        .first()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="赞助商不存在 / Sponsor not found")
    return s


def _get_contract(db: Session, sponsor_id: int, contract_id: int) -> SponsorContract:
    c = (
        db.query(SponsorContract)
        .filter(
            SponsorContract.id == contract_id,
            SponsorContract.sponsor_id == sponsor_id,
            SponsorContract.is_deleted.is_(False),
        )
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="合同不存在 / Contract not found")
    return c


@router.post("", response_model=SponsorOut, status_code=status.HTTP_201_CREATED)
def create_sponsor(
    payload: SponsorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    sponsor = Sponsor(**payload.model_dump(), created_by=current_user.id)
    db.add(sponsor)
    db.commit()
    db.refresh(sponsor)
    return sponsor


@router.get("", response_model=list[SponsorOut])
def list_sponsors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Sponsor)
        .filter(Sponsor.is_deleted.is_(False))
        .order_by(Sponsor.id)
        .all()
    )


@router.get("/{sponsor_id}", response_model=SponsorOut)
def get_sponsor(
    sponsor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_sponsor(db, sponsor_id)


@router.put("/{sponsor_id}", response_model=SponsorOut)
def update_sponsor(
    sponsor_id: int,
    payload: SponsorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    sponsor = _get_sponsor(db, sponsor_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sponsor, field, value)
    sponsor.updated_by = current_user.id
    db.commit()
    db.refresh(sponsor)
    return sponsor


@router.post(
    "/{sponsor_id}/contracts",
    response_model=SponsorContractOut,
    status_code=status.HTTP_201_CREATED,
)
def create_contract(
    sponsor_id: int,
    payload: SponsorContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    _get_sponsor(db, sponsor_id)
    contract = SponsorContract(
        sponsor_id=sponsor_id, **payload.model_dump(), created_by=current_user.id
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/{sponsor_id}/contracts", response_model=list[SponsorContractOut])
def list_contracts(
    sponsor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_sponsor(db, sponsor_id)
    return (
        db.query(SponsorContract)
        .filter(
            SponsorContract.sponsor_id == sponsor_id,
            SponsorContract.is_deleted.is_(False),
        )
        .order_by(SponsorContract.id)
        .all()
    )


@router.put("/{sponsor_id}/contracts/{contract_id}", response_model=SponsorContractOut)
def update_contract(
    sponsor_id: int,
    contract_id: int,
    payload: SponsorContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    contract = _get_contract(db, sponsor_id, contract_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)
    contract.updated_by = current_user.id
    db.commit()
    db.refresh(contract)
    return contract
