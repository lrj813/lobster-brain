from fastapi import APIRouter

from .. import state_machine, ws_hub
from ..schemas import CommandRequest

router = APIRouter()


@router.post("/api/command")
async def create_command(req: CommandRequest):
    task = state_machine.submit_command(req.command)
    if task.get("status") == "queued":
        await ws_hub.dispatch_task(task)
    return task
