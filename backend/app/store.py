"""JSON 原子落盘存储：任务 + 设备元信息。schema 版本 + 原子写入 + 损坏回退。"""
import json
import os
import random
import string
import threading
from datetime import datetime, timezone

from . import config, intent

_lock = threading.RLock()
_meta = None
_tasks = []


def _now():
    return datetime.now(timezone.utc).isoformat()


def timestamp():
    return _now()


def _short_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _persist_locked():
    _atomic_write(config.TASKS_FILE, _tasks)
    _atomic_write(config.META_FILE, _meta)


def _build_task_locked(command, parsed):
    meta = intent.INTENT_META.get(parsed["intent"], intent.INTENT_META["unknown"])
    steps = []
    for s in intent.STEPS.get(parsed["intent"], []):
        steps.append({"name": s["name"], "detail": s["detail"], "status": "pending"})
    if parsed["intent"] == "join_meeting" and parsed.get("meeting_code"):
        for st in steps:
            if st["name"] == "输入会议号":
                st["detail"] = f"输入会议号 {parsed['meeting_code']}"
    return {
        "id": _short_id(),
        "command": command,
        "intent": parsed["intent"],
        "label": meta["label"],
        "icon": meta["icon"],
        "meeting_code": parsed.get("meeting_code"),
        "status": "queued",
        "error": None,
        "result": None,
        "evidence": None,
        "steps": steps,
        "created_at": _now(),
        "started_at": None,
        "finished_at": None,
        "duration": None,
        "device": _meta["device"]["name"] if _meta else config.AGENT_NAME_DEFAULT,
    }


def _seed_locked():
    demo = [
        ("搜索一部热门电影并播放相关视频", "search_movie", None, "success",
         "已打开浏览器并在 B 站播放热门电影，视频已自动播放", 12.3),
        ("加入腾讯会议，会议码 1234", "join_meeting", "1234", "success",
         "已加入腾讯会议（会议号 1234），已静音、摄像头关闭", 8.5),
        ("创建一个腾讯会议", "create_meeting", None, "success",
         "会议已创建，会议号 987 654 321", 9.1),
        ("帮我订明天去北京的机票", "unknown", None, "failed",
         "抱歉，我现在只会两件事：①搜索电影并播放 ②加入/创建腾讯会议。试试下面的快捷指令。", 0.3),
    ]
    for command, i, code, status, text, dur in demo:
        t = _build_task_locked(command, {"intent": i, "meeting_code": code, "error": None})
        t["status"] = status
        t["started_at"] = _now()
        t["finished_at"] = _now()
        t["duration"] = dur
        if status == "success":
            t["result"] = text
            for st in t["steps"]:
                st["status"] = "done"
        else:
            t["error"] = text
        _tasks.append(t)


def init(seed=True):
    global _meta, _tasks
    with _lock:
        _meta = _read_json(config.META_FILE, None)
        _tasks = _read_json(config.TASKS_FILE, [])
        if _meta is None or not isinstance(_tasks, list):
            _meta = {
                "schema_version": config.SCHEMA_VERSION,
                "device": {
                    "name": config.AGENT_NAME_DEFAULT,
                    "os": "Windows",
                    "mode": "sim",
                    "version": "0.1.0",
                    "online": False,
                    "manual_offline": False,
                    "last_seen": None,
                },
                "seeded": False,
            }
            _tasks = []
            if seed:
                _seed_locked()
                _meta["seeded"] = True
            _persist_locked()


def _reset_for_tests():
    global _meta, _tasks
    with _lock:
        _meta = None
        _tasks = []


def get_meta():
    with _lock:
        return dict(_meta)


def get_tasks():
    with _lock:
        return [dict(t) for t in reversed(_tasks)]


def get_task(task_id):
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                return dict(t)
        return None


def new_task(command, parsed):
    with _lock:
        t = _build_task_locked(command, parsed)
        _tasks.append(t)
        _persist_locked()
        return dict(t)


def update_task(task_id, **fields):
    with _lock:
        for t in _tasks:
            if t["id"] == task_id:
                t.update(fields)
                _persist_locked()
                return dict(t)
        return None


def get_device():
    with _lock:
        return dict(_meta["device"])


def set_device(**fields):
    with _lock:
        _meta["device"].update(fields)
        _persist_locked()
        return dict(_meta["device"])


def device_online():
    d = get_device()
    if d.get("manual_offline"):
        return False
    if not d.get("online"):
        return False
    last = d.get("last_seen")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now(timezone.utc) - last_dt).total_seconds() <= config.AGENT_TIMEOUT_SECONDS
    except (ValueError, TypeError):
        return False


def reset():
    global _meta, _tasks
    with _lock:
        _tasks = []
        _seed_locked()
        _meta["seeded"] = True
        _persist_locked()
        return len(_tasks)
