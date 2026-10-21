from fastapi import APIRouter

from .. import store

router = APIRouter()


@router.get("/api/tasks")
async def list_tasks():
    return store.get_tasks()
