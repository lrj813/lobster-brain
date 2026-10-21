"""规则版意图识别。MVP 不接 LLM，确定性规则 100% 覆盖两场景。"""
import re

INTENT_META = {
    "search_movie": {"label": "搜索电影并播放", "icon": "🎬"},
    "close_movie": {"label": "停止播放", "icon": "⏹️"},
    "join_meeting": {"label": "加入腾讯会议", "icon": "📞"},
    "create_meeting": {"label": "创建腾讯会议", "icon": "📹"},
    "close_meeting": {"label": "退出会议", "icon": "🚪"},
    "unknown": {"label": "未识别", "icon": "❓"},
}

STEPS = {
    "search_movie": [
        {"name": "打开浏览器", "detail": "正在启动 Chrome 浏览器"},
        {"name": "搜索热门电影", "detail": "在 B 站搜索当前热门电影"},
        {"name": "打开相关视频", "detail": "点击第一个视频结果"},
        {"name": "确认播放", "detail": "视频已开始播放，截图留证"},
    ],
    "join_meeting": [
        {"name": "拉起腾讯会议", "detail": "启动腾讯会议客户端"},
        {"name": "输入会议号", "detail": "输入会议号"},
        {"name": "加入会议", "detail": "已静音、摄像头关闭入会"},
    ],
    "create_meeting": [
        {"name": "启动腾讯会议", "detail": "打开腾讯会议客户端"},
        {"name": "创建快速会议", "detail": "点击「快速会议」"},
        {"name": "读取会议号", "detail": "获取会议号"},
    ],
    "close_movie": [
        {"name": "停止播放", "detail": "关闭正在播放的视频"},
    ],
    "close_meeting": [
        {"name": "退出会议", "detail": "离开当前会议"},
    ],
}

CREATE_WORDS = ["创建", "新建", "预约", "发起", "create"]
JOIN_WORDS = ["加入", "入会", "参会", "进入", "join"]
MOVIE_WORDS = ["电影", "视频", "播放", "搜索", "看片", "影片"]
MEETING_KEYWORDS = ["会议", "meeting"]
STOP_WORDS = ["关闭", "关掉", "停止", "退出", "停掉"]
STOP_CONTEXT = MOVIE_WORDS + ["浏览器", "网页", "页面", "窗口"]
CLOSE_MEETING_WORDS = ["退出会议", "离开会议", "结束会议", "关闭会议", "退出腾讯会议", "离开腾讯会议", "结束腾讯会议"]


def extract_meeting_code(text: str):
    """提取会议号：支持 601-651-818 / 601 651 818 / 123456789 等形式。"""
    # 带分隔符（连字符/空格）的多段数字：601-651-818 → 601651818
    m = re.search(r"\d{3,}(?:[- ]\d{3,})+", text)
    if m:
        return re.sub(r"[- ]", "", m.group())
    # 单段数字：取最长的一串 3 位以上
    runs = re.findall(r"\d{3,}", text)
    if not runs:
        return None
    return max(runs, key=len)


def classify(command):
    text = (command or "").strip()
    if not text:
        return {"intent": "unknown", "meeting_code": None, "error": "INVALID_COMMAND"}

    lower = text.lower()

    # 退出会议（优先判断，避免与"停止播放"混淆）
    if any(w in text for w in CLOSE_MEETING_WORDS):
        return {"intent": "close_meeting", "meeting_code": None, "error": None}

    # 停止播放：关闭/停止 + 电影/浏览器上下文
    has_stop = any(w in text for w in STOP_WORDS)
    if has_stop and any(w in text for w in STOP_CONTEXT):
        return {"intent": "close_movie", "meeting_code": None, "error": None}

    has_meeting = any(k in lower for k in MEETING_KEYWORDS)
    code = extract_meeting_code(text)

    if has_meeting:
        has_create = any(w in lower for w in CREATE_WORDS)
        has_join = any(w in lower for w in JOIN_WORDS)
        if has_create:
            return {"intent": "create_meeting", "meeting_code": None, "error": None}
        if has_join:
            if code:
                return {"intent": "join_meeting", "meeting_code": code, "error": None}
            return {"intent": "join_meeting", "meeting_code": None, "error": "MISSING_MEETING_CODE"}
        if code:
            return {"intent": "join_meeting", "meeting_code": code, "error": None}

    has_movie = any(w in text for w in MOVIE_WORDS)
    if has_movie:
        return {"intent": "search_movie", "meeting_code": None, "error": None}

    return {"intent": "unknown", "meeting_code": None, "error": "INTENT_UNKNOWN"}
