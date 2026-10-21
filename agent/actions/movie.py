"""场景一：电影（真实执行，真控 Mac）。
- 无头 Playwright 只搜一次 B 站（拿第一个视频的链接+标题）→ 用系统 Chrome 打开播放 → 原生截屏作证据
- 停止播放：用 AppleScript 精准关闭本次打开的那个视频标签页
"""
import asyncio
import base64
import re
import subprocess
from urllib.parse import quote

BLOCK_WORDS = ["福利", "成人", "色情", "18禁", "激情", "裸聊", "赌博", "网赌"]
UI_WORDS = ["稍后", "点赞", "投币", "收藏", "分享", "关注", "弹幕", "评论", "下载"]

STOP_WORDS = ["搜索", "播放", "一部", "相关视频", "相关", "并", "的", "帮我",
              "我想", "我要", "想看", "看看", "请", "给我", "打开", "上b站", "b站", "看"]

_opened_url = None  # 本次真实打开的视频 URL，供"停止播放"精准关闭
_opened_bvid = None  # 本次打开的视频 BV 号（B 站会重定向加 /zh-Hans/ 等，用 BV 号匹配更稳）


def _svg_data_url(text):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="200">'
        '<rect width="360" height="200" fill="#14142b"/>'
        '<text x="180" y="90" font-size="20" fill="#4ade80" text-anchor="middle" '
        'font-family="sans-serif">🦞 模拟截图</text>'
        f'<text x="180" y="122" font-size="13" fill="#e5e7eb" text-anchor="middle" '
        f'font-family="sans-serif">{text}</text>'
        '<text x="180" y="148" font-size="11" fill="#6b7280" text-anchor="middle" '
        'font-family="sans-serif">（演示截图）</text>'
        '</svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return "data:image/svg+xml;base64," + b64


def build_result(task):
    return "已打开浏览器并在 B 站播放热门电影，视频已自动播放", _svg_data_url("电影播放中")


def extract_query(command):
    q = (command or "").strip()
    for w in STOP_WORDS:
        q = q.replace(w, " ")
    q = " ".join(q.split())
    return q if q else "热门电影"


def _looks_like_title(text):
    t = (text or "").replace("\n", " ").strip()
    if not t:
        return False
    if any(u in t for u in UI_WORDS):
        return False
    # 同时含"播放量(万)"与"时长(mm:ss)"的是封面/卡片信息，不是标题
    if re.search(r"\d+\.?\d*万", t) and re.search(r"\d{1,2}:\d{2}", t):
        return False
    return len(re.findall(r"[\u4e00-\u9fff]", t)) >= 3


async def _find_safe_video(page):
    """返回第一个视频的 (href, title)。"""
    data = await page.evaluate("""() => {
        const out = [];
        for (const a of document.querySelectorAll('a[href*="bilibili.com/video/BV"]')) {
            out.push({href: a.getAttribute('href'), text: (a.textContent || '').trim()});
        }
        return out;
    }""")
    first_href = None
    for item in data:
        href, text = item.get("href"), item.get("text", "")
        if first_href is None:
            first_href = href
        title = text.replace("\n", " ").strip()
        if href and _looks_like_title(text) and not any(b in title for b in BLOCK_WORDS):
            return href, title
    if first_href:
        return first_href, "视频"
    return None, "视频"


async def _goto_retry(page, url, tries=2, timeout=20000):
    last = None
    for _ in range(tries):
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            return
        except Exception as e:
            last = e
            await asyncio.sleep(1)
    raise last


def _extract_bv(url):
    m = re.search(r"(BV[0-9A-Za-z]{6,})", url or "")
    return m.group(1) if m else None


def _open_in_chrome(url):
    global _opened_url, _opened_bvid
    subprocess.run(["open", "-a", "Google Chrome", url])
    _opened_url = url
    _opened_bvid = _extract_bv(url)


def _close_video_tab(bvid):
    script = (
        'tell application "Google Chrome"\n'
        '  repeat with w in windows\n'
        '    repeat with t in tabs of w\n'
        f'      if URL of t contains "{bvid}" then\n'
        '        close t\n'
        '        return "closed"\n'
        '      end if\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return "notfound"\n'
        'end tell'
    )
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20)
    return "closed" in (r.stdout or "")


def _capture_evidence():
    big = "/tmp/lb_movie_shot.png"
    small = "/tmp/lb_movie_shot_small.png"
    subprocess.run(["screencapture", "-x", big], timeout=15)
    try:
        subprocess.run(["sips", "-Z", "800", big, "--out", small],
                       capture_output=True, timeout=15)
        path = small
    except Exception:
        path = big
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


async def run_real(task, send_step):
    global _opened_url
    _opened_url = None
    query = extract_query(task.get("command"))

    from playwright.async_api import async_playwright

    # 第一步：无头搜索，拿链接+标题
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            await send_step(0, "running")
            await _goto_retry(page, f"https://search.bilibili.com/all?keyword={quote(query)}")
            await send_step(0, "done")

            await send_step(1, "running")
            await page.wait_for_timeout(1200)
            await send_step(1, "done")

            await send_step(2, "running")
            href, title = await _find_safe_video(page)
            if not href:
                raise RuntimeError("未找到视频结果")
            await send_step(2, "done")
        finally:
            await browser.close()

    # 第二步：用系统 Chrome 打开播放（不自动关闭）
    await send_step(3, "running")
    full_url = href if href.startswith("http") else "https:" + href
    _open_in_chrome(full_url)
    await asyncio.sleep(3)
    evidence = await asyncio.to_thread(_capture_evidence)
    await send_step(3, "done")

    return f"已为你打开并播放：{title}", evidence


async def stop_movie():
    global _opened_url, _opened_bvid
    bvid = _opened_bvid
    _opened_url = None
    _opened_bvid = None
    if not bvid:
        return False
    return await asyncio.to_thread(_close_video_tab, bvid)


async def stop_movie_task(task, send_step):
    if task.get("steps"):
        await send_step(0, "running")
    closed = await stop_movie()
    if task.get("steps"):
        await send_step(0, "done")
    if closed:
        return "已关闭正在播放的视频", None
    return "当前没有正在播放的视频", None
