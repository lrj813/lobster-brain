"""执行层分发：sim（模拟）与 real（真实）两种模式。"""
import asyncio

from . import meeting, movie

SIM_STEP_DELAY = float(__import__("os").environ.get("SIM_STEP_DELAY", "1.0"))


def build_result(task):
    intent = task.get("intent")
    if intent == "search_movie":
        return movie.build_result(task)
    if intent == "close_movie":
        return ("已关闭正在播放的视频", None)
    if intent == "close_meeting":
        return ("已退出会议", None)
    if intent in ("join_meeting", "create_meeting"):
        return meeting.build_result(task)
    return ("任务已完成", None)


async def execute_sim(task, send_step):
    for idx in range(len(task.get("steps") or [])):
        await send_step(idx, "running")
        await asyncio.sleep(SIM_STEP_DELAY)
        await send_step(idx, "done")
    return build_result(task)


async def execute_real(task, send_step):
    intent = task.get("intent")
    if intent == "search_movie":
        return await movie.run_real(task, send_step)
    if intent == "close_movie":
        return await movie.stop_movie_task(task, send_step)
    if intent in ("join_meeting", "create_meeting", "close_meeting"):
        return await meeting.run_real(task, send_step)
    return ("任务已完成", None)
