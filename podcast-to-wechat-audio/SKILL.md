---
name: podcast-to-wechat-audio
description: Build and operate a semi-automated workflow that syncs podcast RSS episodes, including Xiaoyuzhou feeds, to WeChat Channels audio posts. 生成可恢复的播客 RSS 到微信视频号音频同步队列，并半自动发布音频内容。
---

# 播客同步到视频号音频 / Podcast To WeChat Audio

## 概览 / Overview

使用这个 skill，可以把标准播客 RSS feed 转成可恢复的微信视频号音频上传队列，并通过视频号助手网页半自动发布。

Use this skill to turn a standard podcast RSS feed into a resumable WeChat Channels audio upload queue, then semi-automate publishing through the WeChat Channels Assistant web UI.

用户数据必须留在 skill 文件夹之外。请从用户的项目/工作目录运行脚本，让生成的 `data/`、`downloads/`、`logs/` 和 `.wechat-profile/` 都保存在该项目本地。

Keep user data outside the skill folder. Run scripts from the user's project/workspace directory so generated `data/`, `downloads/`, `logs/`, and `.wechat-profile/` directories stay local to that project.

## 工作流 / Workflow

1. 创建或选择一个干净的迁移工作目录。
2. Create or choose a clean project directory for the migration.

生成 RSS 队列 / Generate the RSS queue:

```powershell
python "<skill_dir>\scripts\sync_feed.py" refresh --feed-url "<RSS_URL>"
```

下载小批量样本 / Download a small pilot batch:

```powershell
python "<skill_dir>\scripts\sync_feed.py" download --feed-url "<RSS_URL>" --assets all --limit 3
```

按需安装浏览器自动化依赖 / Install browser automation dependencies when needed:

```powershell
pip install -r "<skill_dir>\scripts\requirements.txt"
python -m playwright install chromium
```

预览上传队列 / Dry-run the upload queue:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --dry-run --limit 3
```

填写一条但不发布 / Fill one post without publishing:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --limit 1 --download-missing --submit-mode pause --upload-wait 120
```

人工确认后，小批量发布 / After visual confirmation, publish a small batch:

```powershell
python "<skill_dir>\scripts\wechat_audio_uploader.py" --limit 5 --download-missing --submit-mode publish --upload-wait 120
```

## 运行规则 / Operating Rules

- 默认使用 `pause` 模式，直到用户明确确认可以公开发布。
- Default to `pause` mode until the user explicitly confirms public publishing.
- 小批量处理，通常每批 3 到 10 期，降低平台风险，也便于失败后重试。
- Process in small batches, usually 3 to 10 episodes, to reduce platform risk and make failures easy to retry.
- 把 `data/wechat_audio_upload_queue.csv` 当作 `pending`、`uploaded`、`drafted` 和 `error` 状态的事实来源。
- Treat `data/wechat_audio_upload_queue.csv` as the source of truth for `pending`, `uploaded`, `drafted`, and `error` status.
- 如果运行中断，重启前先检查队列状态。
- If a run is interrupted, inspect the queue before restarting.
- 不要提交或分享项目本地的 `data/`、`downloads/`、`logs/` 或 `.wechat-profile/`。
- Do not commit or share project-local `data/`, `downloads/`, `logs/`, or `.wechat-profile/`.
- 如果某条内容是用户在浏览器里手动发布的，继续前先更新队列状态，避免重复发布。
- If a post is published manually in the browser, update the queue status before continuing to avoid duplicates.

## 参考 / References

修改上传自动化或调试视频号助手行为前，先读 [references/wechat-channels-audio.md](references/wechat-channels-audio.md)。

Read [references/wechat-channels-audio.md](references/wechat-channels-audio.md) before changing the upload automation or debugging WeChat Channels Assistant behavior.

准备仓库、gist、压缩包或公开发布任何使用过该流程的项目时，先读 [references/privacy-and-open-source.md](references/privacy-and-open-source.md)。

Read [references/privacy-and-open-source.md](references/privacy-and-open-source.md) before preparing a repository, gist, archive, or public release of a project that used this workflow.
