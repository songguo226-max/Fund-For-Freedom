from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.modules.data_sources.router import router as data_sources_router
from app.modules.fed.router import router as fed_router
from app.modules.fund_analytics.index_router import router as index_router
from app.modules.fund_analytics.router import router as fund_router
from app.modules.news.router import router as news_router
from app.shared.http_errors import install_error_handlers

app = FastAPI(title=settings.app_name, version=settings.version)
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_sources_router)
app.include_router(fund_router)
app.include_router(index_router)
app.include_router(news_router)
app.include_router(fed_router)

@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}
