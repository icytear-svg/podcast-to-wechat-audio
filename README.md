# Podcast to WeChat Audio

Batch-sync podcast RSS episodes to WeChat Channels audio posts.

This repository contains a Codex-friendly skill plus reusable Python scripts that:

- parse a podcast RSS feed into a resumable upload queue;
- preserve upload state in `data/wechat_audio_upload_queue.csv`;
- download episode covers and audio files;
- transcode podcast `m4a` files to WeChat-compatible MP3;
- automate the WeChat Channels Assistant audio publishing form with Playwright;
- verify published items before marking queue rows as `uploaded`.

The workflow was built for standard podcast RSS fields and should work with many podcast hosts, including Xiaoyuzhou-style RSS feeds.

## Safety First

The default publishing mode is `pause`, which fills one form and stops for inspection. `publish` mode publicly posts to WeChat Channels and should only be used after confirming the account and form flow are correct.

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
      sync_latest.py
      wechat_audio_uploader.py
    references/
      privacy-and-open-source.md
      wechat-channels-audio.md
  adapters/
    openclaw.skills.example.json5
  AGENTS.md
  CLAUDE.md
  HERMES.md
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

On Windows, Playwright often provides an ffmpeg binary. If your platform cannot find ffmpeg automatically, install it with your system package manager.

## Quick Start

Create a private working directory outside this repository so queues, media, screenshots, and login state stay out of Git:

```bash
mkdir my-podcast-sync
cd my-podcast-sync
```

Generate the upload queue:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py refresh --feed-url "<RSS_URL>"
```

Check queue state:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py status
```

Download a pilot batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_feed.py download --feed-url "<RSS_URL>" --assets all --limit 3
```

Preflight selected queue rows without opening the browser:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --preflight --limit 3 --download-missing
```

Fill one form without publishing:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 1 --download-missing --submit-mode pause --upload-wait 120
```

After confirming the form is correct, publish a small batch:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --limit 5 --download-missing --submit-mode publish --upload-wait 120
```

## Sync The Newest Episode

Use `sync_latest.py` for the common "sync the latest episode" workflow. It refreshes the RSS queue, selects the newest `pending` row, and then delegates to the uploader.

Preflight the newest pending episode:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_latest.py --feed-url "<RSS_URL>" --preflight
```

Fill the newest pending episode without publishing:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_latest.py --feed-url "<RSS_URL>" --submit-mode pause
```

Publish only after explicit confirmation:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/sync_latest.py --feed-url "<RSS_URL>" --submit-mode publish --upload-wait 120
```

## Generated Files

Run scripts from a private working directory. They create:

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
- `uploaded`: published and verified
- `drafted`: saved as draft
- `filled`: filled in `pause` mode
- `error`: failed and can be retried after inspection

To retry one failed episode, edit its row from `error` to `pending`, then run:

```bash
python ../podcast-to-wechat-audio/podcast-to-wechat-audio/scripts/wechat_audio_uploader.py --episode-no 001 --download-missing --submit-mode pause
```

## Privacy Checklist Before Publishing Forks

Run a scan before pushing your own fork:

```bash
rg -n "RSS_URL|cookie|token|downloads|\\.wechat-profile|data/wechat_audio_upload_queue|xiaoyuzhoufm.com/episode" .
```

This repository intentionally ships without real feeds, account data, downloaded media, screenshots, or login state.
