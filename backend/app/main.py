from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    activity,
    auth,
    demo,
    enrollment,
    finance,
    health,
    member,
    message,
    organization,
)
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    description="NZ 华人高协 CRM 后端 API（V1.0 Web 产品）",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(demo.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(organization.router, prefix=API_PREFIX)
app.include_router(enrollment.router, prefix=API_PREFIX)
app.include_router(member.router, prefix=API_PREFIX)
app.include_router(activity.router, prefix=API_PREFIX)
app.include_router(finance.router, prefix=API_PREFIX)
app.include_router(message.router, prefix=API_PREFIX)


@app.get("/")
def root():
    return {"app": settings.app_name, "env": settings.app_env, "docs": "/docs"}
