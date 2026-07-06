from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.member import MemberLevel, MemberStatus


class MemberPublicOut(BaseModel):
    """公开信息视图（非超管/财务只能看到这些）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    chinese_name: str
    english_name: str | None
    avatar: str | None
    golf_age: int | None
    club_number: str | None
    handicap: Decimal | None
    level: MemberLevel
    status: MemberStatus
    branch_id: int | None
    team_id: int | None
    join_date: date | None


class MemberFullOut(MemberPublicOut):
    """完整视图（含隐私信息，仅超管/财务/本人可见）。"""

    nz_address: str | None
    local_phone: str | None
    passport_no: str | None
    visa_type: str | None
    payment_account: str | None
    emergency_contact: str | None
    last_active_at: datetime | None


class MemberCreate(BaseModel):
    chinese_name: str
    english_name: str | None = None
    golf_age: int | None = None
    club_number: str | None = None
    handicap: Decimal | None = None
    # 隐私信息
    nz_address: str | None = None
    local_phone: str | None = None
    passport_no: str | None = None
    visa_type: str | None = None
    payment_account: str | None = None
    emergency_contact: str | None = None
    # 归属与等级
    level: MemberLevel = MemberLevel.probationary
    branch_id: int | None = None
    team_id: int | None = None
    join_date: date | None = None
    # 可选：同时开通登录账号
    account_username: str | None = None
    account_password: str | None = None


class MemberAdminUpdate(BaseModel):
    english_name: str | None = None
    golf_age: int | None = None
    club_number: str | None = None
    handicap: Decimal | None = None
    nz_address: str | None = None
    local_phone: str | None = None
    passport_no: str | None = None
    visa_type: str | None = None
    payment_account: str | None = None
    emergency_contact: str | None = None
    branch_id: int | None = None
    team_id: int | None = None


class MemberSelfUpdate(BaseModel):
    """会员本人仅能修改公开信息。"""

    english_name: str | None = None
    avatar: str | None = None
    golf_age: int | None = None
    club_number: str | None = None


class PromoteResult(BaseModel):
    id: int
    level: MemberLevel
    promoted: bool
    reason: str | None = None
