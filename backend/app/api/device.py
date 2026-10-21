from fastapi import APIRouter

from .. import store
from ..schemas import DeviceUpdate

router = APIRouter()


@router.get("/api/device")
async def get_device():
    d = store.get_device()
    d["online"] = store.device_online()
    return d


@router.post("/api/device")
async def update_device(req: DeviceUpdate):
    store.set_device(manual_offline=req.manual_offline)
    d = store.get_device()
    d["online"] = store.device_online()
    return d
