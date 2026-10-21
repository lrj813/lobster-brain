from fastapi import APIRouter

from .. import dashboard

router = APIRouter()


@router.get("/api/dashboard")
async def get_dashboard():
    return dashboard.compute()
