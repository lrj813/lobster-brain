from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from . import config, store, ws_hub
from .api import commands, dashboard, device, health, reset, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init(seed=True)
    yield


app = FastAPI(title="龙虾脑 Lobster Brain", lifespan=lifespan)

app.include_router(commands.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(device.router)
app.include_router(health.router)
app.include_router(reset.router)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await ws_hub.handle_agent(websocket)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
async def admin():
    return FileResponse(config.WEB_DIR / "admin.html")
