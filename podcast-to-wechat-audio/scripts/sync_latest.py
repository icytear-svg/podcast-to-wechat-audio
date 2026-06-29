#!/usr/bin/env python3
"""Refresh, prepare, and upload the newest pending podcast episode."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import sync_feed
import wechat_audio_uploader


SCRIPT_DIR = Path(__file__).resolve().parent


def refresh_queue(feed_url: str, description_limit: int) -> None:
    args = argparse.Namespace(feed_url=feed_url, description_limit=description_limit)
    sync_feed.refresh(args)


def newest_pending() -> wechat_audio_uploader.QueueItem | None:
    rows, _ = wechat_audio_uploader.read_queue(wechat_audio_uploader.QUEUE_CSV)
    items = wechat_audio_uploader.selected_items(rows, "pending", 1, None)
    return items[0] if items else None


def run_uploader(item: wechat_audio_uploader.QueueItem, args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "wechat_audio_uploader.py"),
        "--episode-no",
        item.data.get("episode_no", ""),
        "--limit",
        "1",
        "--download-missing",
        "--submit-mode",
        args.submit_mode,
        "--upload-wait",
        str(args.upload_wait),
        "--verify-pages",
        str(args.verify_pages),
        "--publish-verify-wait",
        str(args.publish_verify_wait),
        "--title-max-chars",
        str(args.title_max_chars),
    ]
    if args.dry_run:
        command.append("--dry-run")
    if args.preflight:
        command.append("--preflight")
    if args.no_transcode_mp3:
        command.append("--no-transcode-mp3")
    return subprocess.run(command, cwd=Path.cwd()).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the newest pending episode to WeChat Channels audio.")
    parser.add_argument("--feed-url", required=True)
    parser.add_argument("--description-limit", type=int, default=1800)
    parser.add_argument("--submit-mode", choices=["pause", "draft", "publish"], default="pause")
    parser.add_argument("--upload-wait", type=int, default=120)
    parser.add_argument("--verify-pages", type=int, default=2)
    parser.add_argument("--publish-verify-wait", type=int, default=180)
    parser.add_argument("--title-max-chars", type=int, default=wechat_audio_uploader.DEFAULT_TITLE_MAX_CHARS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--no-transcode-mp3", action="store_true")
    args = parser.parse_args(argv)

    refresh_queue(args.feed_url, args.description_limit)
    item = newest_pending()
    if item is None:
        print("No pending episodes after refresh.")
        return 0

    print(f"Newest pending episode: {item.data.get('episode_no')} | {item.title}")
    return run_uploader(item, args)


if __name__ == "__main__":
    raise SystemExit(main())
