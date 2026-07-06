"""后端双语文案。

Phase 0 提供最小实现：按 lang 返回中英文文案，
供接口返回与错误码使用。后续可扩展为完整词库。
"""

DEFAULT_LANG = "zh-CN"
SUPPORTED_LANGS = ("zh-CN", "en")

MESSAGES: dict[str, dict[str, str]] = {
    "welcome": {
        "zh-CN": "欢迎使用 NZ 华人高协 CRM",
        "en": "Welcome to the NZ Chinese Golf Association CRM",
    },
    "healthy": {
        "zh-CN": "服务运行正常",
        "en": "Service is healthy",
    },
}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    lang = lang.strip()
    if lang in SUPPORTED_LANGS:
        return lang
    # 兼容 "en-US" / "zh" 等
    if lang.lower().startswith("zh"):
        return "zh-CN"
    if lang.lower().startswith("en"):
        return "en"
    return DEFAULT_LANG


def t(key: str, lang: str | None = None) -> str:
    lang = normalize_lang(lang)
    entry = MESSAGES.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get(DEFAULT_LANG, key))
