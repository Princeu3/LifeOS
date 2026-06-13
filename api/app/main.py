from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import capture, health

app = FastAPI(title="LifeOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health.router)
app.include_router(capture.router)
