from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.llm_runtime import reset_request_llm_provider, set_request_llm_provider
from app.db.base import Base
from app.db.database import engine, ensure_runtime_schema
import app.models  # noqa: F401 — register all models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def llm_model_override_middleware(request, call_next):
    token = set_request_llm_provider(request.headers.get("x-llm-provider"))
    try:
        return await call_next(request)
    finally:
        reset_request_llm_provider(token)

app.mount(settings.figure_url_prefix, StaticFiles(directory=settings.figure_path), name="figures")


from app.api.upload import router as upload_router
from app.api.documents import router as documents_router
from app.api.extraction import router as extraction_router
from app.api.questions import router as questions_router
from app.api.random_sets import router as random_sets_router

app.include_router(upload_router)
app.include_router(documents_router)
app.include_router(extraction_router)
app.include_router(questions_router)
app.include_router(random_sets_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}
