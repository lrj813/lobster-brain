from fastapi import APIRouter

from .. import store

router = APIRouter()


@router.get("/api/health")
async def health():
    return {
        "ok": True,
        "device_online": store.device_online(),
        "schema_version": store.get_meta().get("schema_version"),
    }
