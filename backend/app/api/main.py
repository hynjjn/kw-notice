from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import meta, notices
from app.config import settings

app = FastAPI(
    title="KW Notice API",
    version="0.1.0",
    description="광운대학교 공지사항 수집, 요약 서비스",
)

# SPA 를 S3 에 올리면 origin 이 갈린다. 배포 시에는 CloudFront 에서
# /api/* 를 백엔드로 라우팅해 같은 origin 으로 만드는 편이 낫다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(notices.router)
api.include_router(meta.router)
app.include_router(api)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
