from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_lang
from app.core.database import get_db
from app.i18n import t

router = APIRouter(tags=["health"])


@router.get("/health")
def health(lang: str = Depends(get_lang)):
    return {"status": "ok", "message": t("healthy", lang)}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """检查数据库连通性。"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "database": "unavailable", "detail": str(exc)}
