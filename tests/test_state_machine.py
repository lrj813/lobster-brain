import pytest

from backend.app import config, state_machine, store


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TASKS_FILE", tmp_path / "tasks.json")
    monkeypatch.setattr(config, "META_FILE", tmp_path / "meta.json")
    store._reset_for_tests()
    store.init(seed=False)
    yield
    store._reset_for_tests()


def _go_online():
    store.set_device(online=True, manual_offline=False, last_seen=store.timestamp())


def test_offline_fails(setup):
    store.set_device(online=False, manual_offline=True)
    t = state_machine.submit_command("搜索一部热门电影并播放相关视频")
    assert t["status"] == "failed"
    assert "不在线" in t["error"]


def test_unknown_fails(setup):
    _go_online()
    t = state_machine.submit_command("帮我订机票")
    assert t["status"] == "failed"
    assert t["intent"] == "unknown"
    assert "只会两件事" in t["error"]


def test_missing_code_fails(setup):
    _go_online()
    t = state_machine.submit_command("加入腾讯会议")
    assert t["status"] == "failed"
    assert "会议号" in t["error"]


def test_movie_queued(setup):
    _go_online()
    t = state_machine.submit_command("搜索一部热门电影并播放相关视频")
    assert t["status"] == "queued"
    assert t["intent"] == "search_movie"
    assert len(t["steps"]) == 4


def test_create_meeting_queued(setup):
    _go_online()
    t = state_machine.submit_command("创建一个腾讯会议")
    assert t["status"] == "queued"
    assert t["intent"] == "create_meeting"
    assert len(t["steps"]) == 3


def test_join_meeting_code_in_detail(setup):
    _go_online()
    t = state_machine.submit_command("加入腾讯会议，会议码 1234")
    assert t["meeting_code"] == "1234"
    input_step = [s for s in t["steps"] if s["name"] == "输入会议号"][0]
    assert "1234" in input_step["detail"]


def test_reset_clears_and_reseeds(setup):
    _go_online()
    state_machine.submit_command("创建一个腾讯会议")
    state_machine.submit_command("创建一个腾讯会议")
    assert len(store.get_tasks()) == 2
    n = store.reset()
    assert n == 4
    assert len(store.get_tasks()) == 4


def test_persistence_survives_reinit(setup):
    _go_online()
    state_machine.submit_command("创建一个腾讯会议")
    # 模拟重启：重新从磁盘加载
    store.init(seed=False)
    tasks = store.get_tasks()
    assert any(t["intent"] == "create_meeting" for t in tasks)
