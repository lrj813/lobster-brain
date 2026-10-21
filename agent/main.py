"""Agent 主进程：WebSocket client 主动连后端，收任务后按 AGENT_MODE 执行（sim 模拟 / real 真实）。"""
import asyncio
import json
import os
import platform
from datetime import datetime, timezone

import websockets

from . import actions

BACKEND_WS_URL = os.environ.get("BACKEND_WS_URL", "ws://127.0.0.1:8001/ws")
AGENT_MODE = os.environ.get("AGENT_MODE", "sim")
HEARTBEAT_SECONDS = 5


def _now():
    return datetime.now(timezone.utc).isoformat()


async def run_task(send, task):
    tid = task["id"]
    steps = task.get("steps") or []

    async def send_step(idx, status):
        st = steps[idx]
        await send({
            "type": "step", "task_id": tid, "idx": idx,
            "name": st["name"], "detail": st["detail"], "status": status,
        })

    started = datetime.now(timezone.utc)
    try:
        if AGENT_MODE == "real":
            result, evidence = await actions.execute_real(task, send_step)
        else:
            result, evidence = await actions.execute_sim(task, send_step)
        duration = round((datetime.now(timezone.utc) - started).total_seconds(), 1)
        await send({
            "type": "result", "task_id": tid, "status": "success",
            "result": result, "error": None, "evidence": evidence, "duration": duration,
        })
    except Exception as e:
        duration = round((datetime.now(timezone.utc) - started).total_seconds(), 1)
        print(f"[agent] 任务 {tid} 执行失败：{e}", flush=True)
        await send({
            "type": "result", "task_id": tid, "status": "failed",
            "result": None, "error": f"执行失败：{e}", "evidence": None, "duration": duration,
        })


async def main():
    device_info = {
        "name": os.environ.get("AGENT_NAME", "龙虾脑-Mac"),
        "os": platform.system() or "macOS",
        "mode": AGENT_MODE,
        "version": "0.2.0",
    }
    while True:
        try:
            async with websockets.connect(BACKEND_WS_URL, ping_interval=None) as ws:
                send_lock = asyncio.Lock()

                async def send(obj):
                    async with send_lock:
                        await ws.send(json.dumps(obj, ensure_ascii=False))

                await send({"type": "hello", "device": device_info})
                ack = await ws.recv()
                print(f"[agent] 已连接后端（mode={AGENT_MODE}），ack={ack}", flush=True)

                async def heartbeat():
                    while True:
                        await asyncio.sleep(HEARTBEAT_SECONDS)
                        await send({"type": "heartbeat", "ts": _now()})

                hb = asyncio.create_task(heartbeat())
                try:
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("type") == "task":
                            t = msg["task"]
                            print(f"[agent] 收到任务 {t['id']} -> {t['intent']}", flush=True)
                            await run_task(send, t)
                finally:
                    hb.cancel()
        except Exception as e:
            print(f"[agent] 连接异常：{e}，3 秒后重试", flush=True)
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
