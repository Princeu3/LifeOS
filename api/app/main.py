from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .procrastinate_app import procrastinate_app
from .routers import auth, capture, health, photos, timeline, withings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Open the Procrastinate pool so endpoints can defer jobs. Be resilient: a transient DB blip
    # at startup must not take down the whole API (deferring would simply error until it recovers).
    opened = False
    try:
        await procrastinate_app.open_async()
        opened = True
    except Exception:  # noqa: BLE001
        pass
    try:
        yield
    finally:
        if opened:
            await procrastinate_app.close_async()


app = FastAPI(title="LifeOS API", version="0.1.0", lifespan=lifespan)

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
app.include_router(withings.router)
