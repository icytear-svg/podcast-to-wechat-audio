# 播客同步到视频号音频 / Podcast to WeChat Audio

把播客 RSS 节目批量同步到微信视频号音频内容。

Batch-sync podcast RSS episodes to WeChat Channels audio posts.

维护者 / Maintained by: [zhaole.xyz](https://zhaole.xyz)

这个仓库提供一套适合 agent 调用的 skill，以及可单独运行的 Python 脚本，用来：

This repository contains an agent-friendly skill plus reusable Python scripts that:

- 解析播客 RSS，生成可恢复、可重试的上传队列；
- parse a podcast RSS feed into a resumable upload queue;
- 下载节目封面和音频文件；
- download episode covers and audio files;
- 将常见播客 `m4a` 音频转码为视频号更容易接受的 MP3；
- transcode podcast `m4a` files to WeChat-compatible MP3;
- 用 Playwright 半自动填写视频号助手的音频发布表单；
- automate the WeChat Channels Assistant audio publishing form with Playwright;
- 跟踪 `pending`、`uploaded`、`drafted`、`error` 等状态，方便小批量重试。
- track `pending`, `uploaded`, `drafted`, and `error` states for retry-safe batches.

这套流程最初面向小宇宙风格的播客 RSS，但核心逻辑基于标准播客 RSS 字段，理论上也适用于许多其他播客托管平台。

The workflow was built for Xiaoyuzhou-style podcast RSS feeds, but it is designed around standard RSS podcast fields and should work with many podcast hosts.

## 安全优先 / Safety First

推荐默认使用 `pause` 模式：脚本只填写一条表单，然后停下来让你检查。`publish` 模式会真正公开发布到视频号，请只在确认账号和表单流程可用后再使用。

The recommended default mode is `pause`, which fills one form and stops for inspection. `publish` mode publicly posts to WeChat Channels and should only be used after confirming the form works for your account.

你需要自行确认拥有音频、封面、标题和简介的发布权利，并遵守微信视频号规则以及播客托管平台的条款。

You are responsible for the rights to publish the audio, cover art, titles, and descriptions you upload, and for complying with WeChat Channels rules and any podcast host terms.

## 仓库结构 / Repository Layout

```text
podcast-to-wechat-audio/
  podcast-to-wechat-audio/
    SKILL.md
    agents/openai.yaml
    scripts/
      requirements.txt
      sync_feed.py
      wechat_audio_uploader.py
    references/
      privacy-and-open-source.md
      wechat-channels-audio.md
  adapters/
    openclaw.skills.example.json5
  AGENTS.md
  CLAUDE.md
  HERMES.md
  .hermes.md
```

## 环境要求 / Requirements

- Python 3.10+
- Playwright with Chromium
- ffmpeg
- 一个可以访问视频号助手音频发布功能的微信视频号账号
- A WeChat Channels account that can access WeChat Channels Assistant audio publishing

安装 Python 依赖 / Install Python dependencies:

```bash
pip install -r podcast-to-wechat-audio/scripts/requirements.txt
python -m playwright install chromium
```

在 Windows 上，Playwright 通常会附带可用的 ffmpeg。如果你的平台无法自动找到 ffmpeg，请使用系统包管理器安装。

On Windows, Playwright often provides an ffmpeg binary. If your platform cannot find ffmpeg automatically, install it with your system package manager.

## 快速开始 / Quick Start

请在本仓库外创建一个私有工作目录，避免把队列、媒体文件、截图或登录态提交到 Git。

Create a private working directory outside this repository so queues, media, screenshots, and login state stay out of Git.

```bash
mkdir my-podcast-sync
cd my-podcast-sync
```

生成上传队列 / Generate the upload queue:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py refresh --feed-url "<RSS_URL>"
```

下载一个小批量样本 / Download a pilot batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py download --feed-url "<RSS_URL>" --assets all --limit 3
```

检查队列 / Check the queue:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --dry-run --limit 3
```

只填写一条，不发布 / Fill one form without publishing:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 1 --download-missing --submit-mode pause --upload-wait 120
```

确认表单无误后，小批量发布 / After confirming the form is correct, publish a small batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 5 --download-missing --submit-mode publish --upload-wait 120
```

发布模式会在提交后回到“音频管理”列表核验，只有确认新条目存在时才会写入 `uploaded`。

In publish mode, the script verifies the item in the audio manager after submission and only then marks it as `uploaded`.

## 运行时文件 / Generated Files

请从私有工作目录运行脚本。脚本会生成：

Run the scripts from a private working directory. They create:

- `data/episodes.json`
- `data/wechat_audio_upload_queue.csv`
- `downloads/audio/`
- `downloads/covers/`
- `downloads/wechat_audio/`
- `logs/screenshots/`
- `logs/debug/`
- `.wechat-profile/`

不要提交这些目录。它们可能包含 RSS 元数据、受版权保护的媒体、截图、调试信息和浏览器登录态。

Do not commit those directories. They may contain RSS metadata, copyrighted media, screenshots, debug traces, and browser login state.

## 重试流程 / Retry Workflow

CSV 队列是状态源。

The CSV queue is the source of truth.

- `pending`: 尚未处理 / not processed yet
- `uploaded`: 已确认发布成功 / published and verified
- `drafted`: 已保存草稿 / saved as draft
- `filled`: `pause` 模式下已填写表单 / filled in `pause` mode
- `error`: 失败，可检查后重试 / failed and can be retried

重试某一期失败节目时，把它的 `upload_status` 从 `error` 改回 `pending`，然后运行：

To retry one failed episode, edit its row from `error` to `pending`, then run:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --episode-no 001 --download-missing --submit-mode pause
```

## Agent 适配 / Agent Compatibility

这个仓库包含多个 agent 入口：

This repository includes several agent entry points:

- Codex / Agent Skills: `podcast-to-wechat-audio/SKILL.md`
- Claude Code: 安装同一个 skill 文件夹，或阅读 `CLAUDE.md`
- Claude Code: install the same folder as a Claude skill or follow `CLAUDE.md`
- OpenClaw: 通过 `skills.load.extraDirs` 加载 skill 文件夹，示例见 `adapters/openclaw.skills.example.json5`
- OpenClaw: load the skill folder through `skills.load.extraDirs`; see `adapters/openclaw.skills.example.json5`
- Hermes: `HERMES.md` and `.hermes.md`
- 通用 coding agents / General coding agents: `AGENTS.md`

## 发布 Fork 前的隐私检查 / Privacy Checklist Before Publishing Forks

推送自己的 fork 前，请扫描敏感信息：

Run a scan before pushing your own fork:

```bash
rg -n "RSS_URL|cookie|token|wechat|downloads|\\.wechat-profile|data/wechat_audio_upload_queue|xiaoyuzhoufm.com/episode" .
```

本仓库刻意不包含真实 RSS、账号数据、下载媒体、截图或登录态。

This repository intentionally ships without real feeds, account data, downloaded media, screenshots, or login state.
