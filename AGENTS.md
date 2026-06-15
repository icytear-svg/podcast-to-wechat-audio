# Agent Instructions

## Project Purpose

This repository packages a reusable skill and scripts for syncing podcast RSS episodes to WeChat Channels audio posts.

## Important Safety Rules

- Never commit real RSS feeds, generated queues, downloaded media, screenshots, debug logs, or browser profile state.
- Keep user runtime data in a separate working directory, not inside this repository.
- Default to `--submit-mode pause` unless the user explicitly approves public publishing.
- Treat `--submit-mode publish` as a live production action.
- Do not add account-specific selectors, cookies, tokens, or personal data to source files.

## Common Commands

Install dependencies:

```bash
pip install -r podcast-to-wechat-audio/scripts/requirements.txt
python -m playwright install chromium
```

Validate the skill:

```bash
python -m py_compile podcast-to-wechat-audio/scripts/sync_feed.py podcast-to-wechat-audio/scripts/wechat_audio_uploader.py
```

Smoke-test RSS parsing from a private work directory:

```bash
python /path/to/repo/podcast-to-wechat-audio/scripts/sync_feed.py refresh --feed-url "<RSS_URL>"
```

## Code Style

- Keep scripts dependency-light and command-line friendly.
- Prefer explicit status files and resumable operations over hidden state.
- Keep generated data out of the repository.
- Update README examples when CLI options change.

## Agent Compatibility

- Codex and OpenClaw can use `podcast-to-wechat-audio/SKILL.md` as an Agent Skills style skill.
- Claude Code can install or reference the same `SKILL.md` skill folder.
- Hermes reads this file unless `.hermes.md` or `HERMES.md` takes priority.
