from fastapi import APIRouter, Depends

from app.api.deps import get_lang
from app.i18n import t

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/welcome")
def welcome(lang: str = Depends(get_lang)):
    """联调示例接口：返回双语欢迎语，供前端验证前后端打通与语言切换。"""
    return {"lang": lang, "message": t("welcome", lang)}
