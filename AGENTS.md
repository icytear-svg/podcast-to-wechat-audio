# Agent 说明 / Agent Instructions

## 项目目的 / Project Purpose

这个仓库把播客 RSS 同步到微信视频号音频的流程封装成可复用的 skill 和脚本。

This repository packages a reusable skill and scripts for syncing podcast RSS episodes to WeChat Channels audio posts.

## 重要安全规则 / Important Safety Rules

- 不要提交真实 RSS 地址、生成的队列、下载的媒体、截图、调试日志或浏览器登录态。
- Never commit real RSS feeds, generated queues, downloaded media, screenshots, debug logs, or browser profile state.
- 用户运行时数据必须放在单独的私有工作目录，不要放进本仓库。
- Keep user runtime data in a separate working directory, not inside this repository.
- 除非用户明确批准公开发布，否则默认使用 `--submit-mode pause`。
- Default to `--submit-mode pause` unless the user explicitly approves public publishing.
- 把 `--submit-mode publish` 当作真实生产发布动作处理。
- Treat `--submit-mode publish` as a live production action.
- 不要把账号专属选择器、cookies、tokens 或个人数据写入源码。
- Do not add account-specific selectors, cookies, tokens, or personal data to source files.

## 常用命令 / Common Commands

安装依赖 / Install dependencies:

```bash
pip install -r podcast-to-wechat-audio/scripts/requirements.txt
python -m playwright install chromium
```

校验脚本 / Validate the skill:

```bash
python -m py_compile podcast-to-wechat-audio/scripts/sync_feed.py podcast-to-wechat-audio/scripts/wechat_audio_uploader.py
```

在私有工作目录中冒烟测试 RSS 解析 / Smoke-test RSS parsing from a private work directory:

```bash
python /path/to/repo/podcast-to-wechat-audio/scripts/sync_feed.py refresh --feed-url "<RSS_URL>"
```

## 代码风格 / Code Style

- 脚本应保持依赖轻量，适合命令行调用。
- Keep scripts dependency-light and command-line friendly.
- 优先使用显式状态文件和可恢复操作，不依赖隐藏状态。
- Prefer explicit status files and resumable operations over hidden state.
- 生成的数据不要进入仓库。
- Keep generated data out of the repository.
- CLI 选项变化时，同步更新 README 示例。
- Update README examples when CLI options change.

## Agent 兼容性 / Agent Compatibility

- Codex 和 OpenClaw 可以把 `podcast-to-wechat-audio/SKILL.md` 当作 Agent Skills 风格的 skill。
- Codex and OpenClaw can use `podcast-to-wechat-audio/SKILL.md` as an Agent Skills style skill.
- Claude Code 可以安装或引用同一个 `SKILL.md` skill 文件夹。
- Claude Code can install or reference the same `SKILL.md` skill folder.
- Hermes 会读取本文件，除非 `.hermes.md` 或 `HERMES.md` 有更高优先级。
- Hermes reads this file unless `.hermes.md` or `HERMES.md` takes priority.
