from fastapi import APIRouter

from .. import store

router = APIRouter()


@router.post("/api/reset")
async def reset():
    n = store.reset()
    return {"ok": True, "seeded": n}
