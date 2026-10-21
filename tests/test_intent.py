from backend.app import intent


def test_movie():
    r = intent.classify("搜索一部热门电影并播放相关视频")
    assert r["intent"] == "search_movie"
    assert r["meeting_code"] is None


def test_join_meeting_with_code():
    r = intent.classify("加入腾讯会议，会议码 1234")
    assert r["intent"] == "join_meeting"
    assert r["meeting_code"] == "1234"


def test_create_meeting():
    r = intent.classify("创建一个腾讯会议")
    assert r["intent"] == "create_meeting"


def test_unknown():
    r = intent.classify("帮我订明天去北京的机票")
    assert r["intent"] == "unknown"


def test_join_missing_code():
    r = intent.classify("加入腾讯会议")
    assert r["intent"] == "join_meeting"
    assert r["error"] == "MISSING_MEETING_CODE"


def test_close_movie():
    assert intent.classify("停止播放")["intent"] == "close_movie"
    assert intent.classify("关闭电影")["intent"] == "close_movie"
    assert intent.classify("关掉浏览器")["intent"] == "close_movie"


def test_close_meeting():
    assert intent.classify("退出会议")["intent"] == "close_meeting"
    assert intent.classify("离开会议")["intent"] == "close_meeting"
    assert intent.classify("结束会议")["intent"] == "close_meeting"


def test_extract_longest_number():
    assert intent.extract_meeting_code("会议码 12，另一个 12345") == "12345"
    assert intent.extract_meeting_code("没有数字") is None


def test_extract_hyphenated_meeting_code():
    assert intent.extract_meeting_code("会议码 601-651-818") == "601651818"
    assert intent.extract_meeting_code("会议码 601 651 818") == "601651818"
