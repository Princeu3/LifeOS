from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth, capture, health, photos, timeline

app = FastAPI(title="LifeOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", *([settings.frontend_origin] if settings.frontend_origin else [])],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(capture.router)
app.include_router(timeline.router)
app.include_router(photos.router)
