---
name: podcast-to-wechat-audio
description: Build and operate a semi-automated workflow that syncs podcast RSS episodes, including Xiaoyuzhou feeds, to WeChat Channels audio posts. Use when a user wants to batch migrate or publish podcast episodes to Shipinhao or WeChat Channels audio, generate an upload queue from RSS, download covers and audio, transcode m4a to MP3, or automate the WeChat Channels Assistant audio publishing form.
---

# Podcast To WeChat Audio

## Overview

Use this skill to turn a standard podcast RSS feed into a resumable WeChat Channels audio upload queue, then semi-automate publishing through the WeChat Channels Assistant web UI.

Keep user data outside the skill folder. Run scripts from the user's project/workspace directory so generated `data/`, `downloads/`, `logs/`, and `.wechat-profile/` directories stay local to that project.

## Workflow

1. Create or choose a clean project directory for the migration.
2. Generate the RSS queue:

```powershell
python "<skill_dir>\scripts\sync_feed.py" refresh --feed-url "<RSS_URL>"
```

3. Download a small pilot batch:

```powershell
python "<skill_dir>\scripts\sync_feed.py" download --feed-url "<RSS_URL>" --assets all --limit 3
```

4. Install browser automation dependencies when needed:

```powershell
pip install -r "<skill_dir>\scripts\requirements.txt"
python -m playwright install chromium
```

5. Dry-run the upload queue:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --dry-run --limit 3
```

6. Fill one post without publishing:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --limit 1 --download-missing --submit-mode pause --upload-wait 120
```

7. After visual confirmation, publish a small batch:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --limit 5 --download-missing --submit-mode publish --upload-wait 120
```

## Operating Rules

- Default to `pause` mode until the user explicitly confirms public publishing.
- Process in small batches, usually 3 to 10 episodes, to reduce platform risk and make failures easy to retry.
- Treat `data/wechat_audio_upload_queue.csv` as the source of truth for `pending`, `uploaded`, `drafted`, and `error` status.
- If a run is interrupted, inspect the queue before restarting.
- Do not commit or share project-local `data/`, `downloads/`, `logs/`, or `.wechat-profile/`.
- If a post is published manually in the browser, update the queue status before continuing to avoid duplicates.

## References

Read [references/wechat-channels-audio.md](references/wechat-channels-audio.md) before changing the upload automation or debugging WeChat Channels Assistant behavior.

Read [references/privacy-and-open-source.md](references/privacy-and-open-source.md) before preparing a repository, gist, archive, or public release of a project that used this workflow.
