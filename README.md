# 🦞 龙虾脑（Lobster Brain）

用手机发一句自然语言，遥控你常开的电脑完成任务。手机端实时看到执行进度和结果截图。

## 能做什么

- 搜索电影并播放（真实打开浏览器播放）
- 停止播放
- 加入腾讯会议（输入会议号）
- 创建腾讯会议
- 退出会议

## 架构

- `backend/` FastAPI 后端：指令意图识别、任务状态机、JSON 落盘、WebSocket 中枢
- `agent/` 执行端：连接后端，按"演示模式 / 真实控制模式"执行任务
- `web/` 手机控制页 + 运营看板（原生 HTML/CSS/JS，无构建步骤）
- `tests/` 意图识别与状态机单元测试

## 环境要求

- Python 3.9+
- macOS（真实控制模式需要；演示模式任意系统可跑）
- 无需任何 API Key

## 快速开始

```bash
cd lobster-brain
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

启动两个进程：

**终端 1 — 后端：**

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001
```

**终端 2 — 执行端（Agent）：**

```bash
# 演示模式（默认，不真控电脑，任何机器可跑）
.venv/bin/python -m agent.main

# 真实控制模式（真控本机：真开浏览器 / 真开腾讯会议）
AGENT_MODE=real .venv/bin/python -m agent.main
```

看到 `[agent] 已连接后端（mode=…）` 即成功。

## 使用

- 手机控制页（手机与电脑同一 WiFi，用电脑局域网 IP 访问）：`http://<电脑IP>:8001/`
- 运营看板：`http://<电脑IP>:8001/admin`
- 本机访问：`http://127.0.0.1:8001/`

> 查电脑局域网 IP：Mac 上 `ipconfig getifaddr en0`；Windows 上 `ipconfig` 看 IPv4。

## 真实控制模式说明

`AGENT_MODE=real` 时，执行端会真的操作本机：电影用 Playwright 打开浏览器播放，会议用 `wemeet://` 拉起腾讯会议。

首次使用需要：

1. 打开腾讯会议并登录；
2. 系统设置 → 隐私与安全性 → 给运行执行端的终端授权「辅助功能」与「屏幕录制」；
3. 执行时电脑亮屏、不锁屏。

会议号读取依赖 macOS 自带的 `swiftc`（OCR 工具首次运行时会自动从源码编译）。

## 运行测试

```bash
.venv/bin/python -m pytest tests/ -q
```

## License

[MIT](LICENSE)
