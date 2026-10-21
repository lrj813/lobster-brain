"""WebSocket 中枢：Agent 主动连后端（无需公网 IP），后端下发任务、接收逐步回报。"""
from datetime import datetime, timezone

from fastapi import WebSocket

from . import store

_agent_ws = None


def _now():
    return datetime.now(timezone.utc).isoformat()


def agent_connected():
    return _agent_ws is not None


async def dispatch_task(task):
    global _agent_ws
    if _agent_ws is None:
        return False
    store.update_task(task["id"], status="dispatched", started_at=_now())
    await _agent_ws.send_json({"type": "task", "task": store.get_task(task["id"])})
    return True


async def _dispatch_queued(ws):
    for t in store.get_tasks():
        if t["status"] == "queued":
            store.update_task(t["id"], status="dispatched", started_at=_now())
            await ws.send_json({"type": "task", "task": store.get_task(t["id"])})


def _apply_step(msg):
    tid = msg.get("task_id")
    idx = msg.get("idx")
    t = store.get_task(tid)
    if not t:
        return
    steps = t.get("steps") or []
    if isinstance(idx, int) and 0 <= idx < len(steps):
        steps = [dict(s) for s in steps]
        steps[idx]["status"] = msg.get("status", "running")
        if msg.get("name"):
            steps[idx]["name"] = msg["name"]
        if msg.get("detail"):
            steps[idx]["detail"] = msg["detail"]
        store.update_task(tid, steps=steps, status="running")


def _apply_result(msg):
    tid = msg.get("task_id")
    t = store.get_task(tid)
    if not t:
        return
    status = msg.get("status", "success")
    now = _now()
    duration = None
    if t.get("started_at"):
        try:
            s = datetime.fromisoformat(t["started_at"])
            e = datetime.fromisoformat(now)
            duration = round((e - s).total_seconds(), 1)
        except (ValueError, TypeError):
            duration = None
    store.update_task(
        tid,
        status=status,
        result=msg.get("result"),
        error=msg.get("error"),
        evidence=msg.get("evidence"),
        finished_at=now,
        duration=msg.get("duration", duration),
    )


async def handle_agent(ws: WebSocket):
    global _agent_ws
    await ws.accept()
    _agent_ws = ws
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")
            if mtype == "hello":
                dev = msg.get("device") or {}
                current = store.get_device()
                store.set_device(
                    online=True,
                    name=dev.get("name") or current.get("name"),
                    os=dev.get("os"),
                    mode=dev.get("mode"),
                    version=dev.get("version"),
                    last_seen=_now(),
                )
                await ws.send_json({"type": "ack", "device": store.get_device().get("name"), "dispatched": 0})
                await _dispatch_queued(ws)
            elif mtype == "heartbeat":
                store.set_device(online=True, last_seen=_now())
            elif mtype == "step":
                _apply_step(msg)
            elif mtype == "result":
                _apply_result(msg)
    except Exception:
        pass
    finally:
        if _agent_ws is ws:
            _agent_ws = None
        store.set_device(online=False)
