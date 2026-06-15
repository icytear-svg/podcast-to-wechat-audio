# Podcast to WeChat Audio

Batch-sync podcast RSS episodes to WeChat Channels audio posts.

Maintained by [zhaole.xyz](https://zhaole.xyz).

This repository contains an agent-friendly skill plus reusable Python scripts that:

- parse a podcast RSS feed into a resumable upload queue;
- download episode covers and audio files;
- transcode podcast `m4a` files to WeChat-compatible MP3;
- automate the WeChat Channels Assistant audio publishing form with Playwright;
- track `pending`, `uploaded`, `drafted`, and `error` states for retry-safe batches.

The workflow was built for Xiaoyuzhou-style podcast RSS feeds, but it is designed around standard RSS podcast fields and should work with many podcast hosts.

## Safety First

The default recommended mode is `pause`, which fills one form and stops for inspection. `publish` mode publicly posts to WeChat Channels and should only be used after confirming the form works for your account.

You are responsible for the rights to publish the audio, cover art, titles, and descriptions you upload, and for complying with WeChat Channels rules and any podcast host terms.

## Repository Layout

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

## Requirements

- Python 3.10+
- Playwright with Chromium
- ffmpeg
- A WeChat Channels account that can access WeChat Channels Assistant audio publishing

Install Python dependencies:

```bash
pip install -r podcast-to-wechat-audio/scripts/requirements.txt
python -m playwright install chromium
```

On Windows, Playwright also installs an ffmpeg binary. If your platform cannot find ffmpeg automatically, install it with your system package manager.

## Quick Start

Create a private working directory outside this repository:

```bash
mkdir my-podcast-sync
cd my-podcast-sync
```

Generate the upload queue:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py refresh --feed-url "<RSS_URL>"
```

Download a pilot batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py download --feed-url "<RSS_URL>" --assets all --limit 3
```

Check the queue:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --dry-run --limit 3
```

Fill one form without publishing:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 1 --download-missing --submit-mode pause --upload-wait 120
```

After you confirm the form is correct, publish a small batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 5 --download-missing --submit-mode publish --upload-wait 120
```

## Generated Files

Run the scripts from a private working directory. They create:

- `data/episodes.json`
- `data/wechat_audio_upload_queue.csv`
- `downloads/audio/`
- `downloads/covers/`
- `downloads/wechat_audio/`
- `logs/screenshots/`
- `logs/debug/`
- `.wechat-profile/`

Do not commit those directories. They may contain RSS metadata, copyrighted media, screenshots, debug traces, and browser login state.

## Retry Workflow

The CSV queue is the source of truth.

- `pending`: not processed yet
- `uploaded`: published successfully
- `drafted`: saved as draft when the platform supports that action
- `filled`: filled in `pause` mode
- `error`: failed and can be retried

To retry one failed episode, edit its row from `error` to `pending`, then run:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --episode-no 001 --download-missing --submit-mode pause
```

## Agent Compatibility

This repository includes several agent entry points:

- Codex / Agent Skills compatible: `podcast-to-wechat-audio/SKILL.md`
- Claude Code compatible: install the same folder as a Claude skill or follow `CLAUDE.md`
- OpenClaw compatible: load the skill folder through `skills.load.extraDirs`; see `adapters/openclaw.skills.example.json5`
- Hermes compatible: `HERMES.md` and `.hermes.md`
- General coding agents: `AGENTS.md`

## Privacy Checklist Before Publishing Forks

Run a scan before pushing your own fork:

```bash
rg -n "RSS_URL|cookie|token|wechat|downloads|\\.wechat-profile|data/wechat_audio_upload_queue|xiaoyuzhoufm.com/episode" .
```

This repository intentionally ships without real feeds, account data, downloaded media, screenshots, or login state.
