"""场景二：腾讯会议（真实执行，真控 Mac）。
- 加入会议：wemeet:// 拉起客户端入会
- 创建会议：OCR+点击「快速会议」→ 点「电脑音频」进入 → OCR 读取会议号
"""
import asyncio
import base64
import os
import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MAC_OCR_BIN = _HERE / "mac_ocr"
_MAC_OCR_SRC = _HERE / "mac_ocr.swift"


def build_result(task):
    intent = task.get("intent")
    code = task.get("meeting_code")
    if intent == "join_meeting":
        return (f"已加入腾讯会议（会议号 {code}），已静音、摄像头关闭", None)
    return ("会议已创建，会议号 987 654 321", None)


async def run_real(task, send_step):
    intent = task.get("intent")
    if intent == "join_meeting":
        return await _join_real(task, send_step)
    if intent == "close_meeting":
        return await _close_meeting_real(task, send_step)
    return await _create_real(task, send_step)


def _activate_tencent():
    subprocess.run(["osascript", "-e",
                    'tell application "System Events" to tell process "TencentMeeting" to set frontmost to true'],
                   timeout=10)


def _ensure_mac_ocr():
    if not _MAC_OCR_BIN.exists():
        subprocess.run(["swiftc", "-O", str(_MAC_OCR_SRC), "-o", str(_MAC_OCR_BIN)], check=True)


def _ocr_click(text):
    _ensure_mac_ocr()
    shot = "/tmp/lb_meeting_ocr.png"
    subprocess.run(["screencapture", "-x", shot], timeout=15)
    r = subprocess.run([str(_MAC_OCR_BIN), shot, "click", text],
                       capture_output=True, text=True, timeout=30)
    return "clicked" in (r.stdout or "")


def _ocr_has(text):
    _ensure_mac_ocr()
    shot = "/tmp/lb_meeting_check.png"
    subprocess.run(["screencapture", "-x", shot], timeout=15)
    r = subprocess.run([str(_MAC_OCR_BIN), shot, "dump"],
                       capture_output=True, text=True, timeout=30)
    return text in (r.stdout or "")


def _read_meeting_number():
    _ensure_mac_ocr()
    shot = "/tmp/lb_meeting_shot.png"
    subprocess.run(["screencapture", "-x", shot], timeout=15)
    small = "/tmp/lb_meeting_shot_small.png"
    try:
        subprocess.run(["sips", "-Z", "800", shot, "--out", small],
                       capture_output=True, timeout=15)
    except Exception:
        small = shot
    path = small if os.path.exists(small) else shot
    with open(path, "rb") as f:
        evidence = "data:image/png;base64," + base64.b64encode(f.read()).decode()

    r = subprocess.run([str(_MAC_OCR_BIN), shot, "digits"],
                       capture_output=True, text=True, timeout=30)
    code = (r.stdout or "").strip()
    return (None if code == "nodigits" else code), evidence


async def _join_real(task, send_step):
    code = task.get("meeting_code")
    await send_step(0, "running")
    url = f"wemeet://page/inmeeting?meeting_code={code}&nick_name=龙虾脑"
    subprocess.run(["open", url])
    await asyncio.sleep(3)
    await send_step(0, "done")

    await send_step(1, "running")
    _activate_tencent()
    await asyncio.sleep(1)
    # 若弹出加入确认框，点"加入"真正入会
    await asyncio.to_thread(_ocr_click, "加入")
    await asyncio.sleep(2)
    # 检测失败：会议不存在 / 查询失败
    _activate_tencent()
    await asyncio.sleep(1)
    fail = await asyncio.to_thread(_ocr_has, "不存在") or await asyncio.to_thread(_ocr_has, "查询")
    await send_step(1, "done")

    await send_step(2, "running")
    await asyncio.sleep(2)
    await send_step(2, "done")

    if fail:
        raise RuntimeError("会议号无效或会议不存在，请检查会议号后重试")
    return (f"已拉起腾讯会议并加入（会议号 {code}），请确认已静音、摄像头关闭", None)


async def _close_meeting_real(task, send_step):
    if task.get("steps"):
        await send_step(0, "running")
    clicked = False
    # 第一下：点"离开会议"（主持人可能是"结束会议"）
    _activate_tencent()
    await asyncio.sleep(1)
    for target in ["离开会议", "结束会议"]:
        if await asyncio.to_thread(_ocr_click, target):
            clicked = True
            break
    await asyncio.sleep(2)
    # 确认框：再点一次"离开会议"（第一次是打开面板，这次才是真离开）
    if clicked:
        _activate_tencent()
        await asyncio.sleep(1)
        await asyncio.to_thread(_ocr_click, "离开会议")
        await asyncio.sleep(2)
    if task.get("steps"):
        await send_step(0, "done")
    if clicked:
        return "已退出会议", None
    return "当前没有正在进行的会议", None


async def _create_real(task, send_step):
    await send_step(0, "running")
    subprocess.run(["open", "-a", "TencentMeeting"])
    await asyncio.sleep(5)
    await send_step(0, "done")

    await send_step(1, "running")
    clicked = False
    for _ in range(3):
        _activate_tencent()
        await asyncio.sleep(1.5)
        for target in ["快速会议", "速会议", "快速会"]:
            if await asyncio.to_thread(_ocr_click, target):
                clicked = True
                break
        if clicked:
            break
        await asyncio.sleep(2)
    await asyncio.sleep(4)
    # 若弹出"请选择会议音频的接入方式"，点"电脑音频"进入
    for target in ["电脑音频", "音频"]:
        await asyncio.to_thread(_ocr_click, target)
    await asyncio.sleep(4)
    await send_step(1, "done")
    if not clicked:
        raise RuntimeError("未找到「快速会议」按钮，请确认腾讯会议已登录并显示主界面")

    await send_step(2, "running")
    code, evidence = await asyncio.to_thread(_read_meeting_number)
    await send_step(2, "done")

    result = f"会议已创建，会议号 {code}" if code else "会议已创建（会议号见截图）"
    return result, evidence
