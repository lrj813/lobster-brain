"""任务创建与前置失败校验。"""
from . import intent, store

ERROR_MSGS = {
    "INVALID_COMMAND": "请输入指令。",
    "INTENT_UNKNOWN": "抱歉，我现在只会两件事：①搜索电影并播放 ②加入/创建腾讯会议。试试下面的快捷指令。",
    "MISSING_MEETING_CODE": "要加入腾讯会议，请把会议号一起告诉我，例如「加入腾讯会议，会议码 1234」",
    "DEVICE_OFFLINE": "电脑不在线：请先开机并登录桌面，再重试。",
}


def _mark_failed(task, code):
    store.update_task(
        task["id"],
        status="failed",
        error=ERROR_MSGS.get(code, code),
        finished_at=store.timestamp(),
        duration=0.0,
    )
    return store.get_task(task["id"])


def submit_command(command):
    parsed = intent.classify(command)
    task = store.new_task(command, parsed)

    if parsed["intent"] == "unknown":
        code = parsed.get("error") or "INTENT_UNKNOWN"
        return _mark_failed(task, code)
    if parsed.get("error") == "MISSING_MEETING_CODE":
        return _mark_failed(task, "MISSING_MEETING_CODE")
    if not store.device_online():
        return _mark_failed(task, "DEVICE_OFFLINE")

    return store.get_task(task["id"])
