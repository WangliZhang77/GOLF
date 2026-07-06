from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ACCESS_TOKEN, decode_token
from app.i18n import normalize_lang
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_lang(accept_language: str | None = Header(default=None)) -> str:
    """从请求头解析语言，供接口返回双语文案。"""
    return normalize_lang(accept_language)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证 / Not authenticated",
        )

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期 / Invalid or expired token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_deleted.is_(False)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在 / User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已停用 / Account disabled",
        )
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """生成一个校验当前用户角色的依赖。"""

    allowed = set(roles)

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足 / Insufficient permissions",
            )
        return current_user

    return checker
