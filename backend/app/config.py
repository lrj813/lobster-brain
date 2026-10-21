from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # lobster-brain 根目录
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
META_FILE = DATA_DIR / "meta.json"
WEB_DIR = BASE_DIR / "web"

SCHEMA_VERSION = 1
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8001  # 8000 被其他项目占用，改用 8001
AGENT_TIMEOUT_SECONDS = 15
AGENT_NAME_DEFAULT = "龙虾脑-Windows"
