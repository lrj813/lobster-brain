"""运营看板指标统计。"""
from . import store


def compute():
    tasks = store.get_tasks()
    total = len(tasks)
    success = sum(1 for t in tasks if t["status"] == "success")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    completed = success + failed
    success_rate = round(success / completed * 100, 1) if completed else None

    durations = [t["duration"] for t in tasks if t.get("duration") is not None]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else None

    running = sum(1 for t in tasks if t["status"] in ("queued", "dispatched", "running"))

    dist = {"search_movie": 0, "join_meeting": 0, "create_meeting": 0, "unknown": 0}
    for t in tasks:
        if t["intent"] in dist:
            dist[t["intent"]] += 1

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "success_rate": success_rate,
        "avg_duration": avg_duration,
        "running": running,
        "intent_distribution": dist,
        "recent_tasks": tasks[:10],
    }
