#!/usr/bin/env python3
"""Build a WeChat Channels audio upload queue from a podcast RSS feed.

The script intentionally uses only Python's standard library so it can run on a
plain Windows Python install.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


ROOT = Path.cwd()
DATA_DIR = ROOT / "data"
DOWNLOAD_DIR = ROOT / "downloads"
AUDIO_DIR = DOWNLOAD_DIR / "audio"
COVER_DIR = DOWNLOAD_DIR / "covers"
MANIFEST_JSON = DATA_DIR / "episodes.json"
MANIFEST_CSV = DATA_DIR / "wechat_audio_upload_queue.csv"

ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
USER_AGENT = "Mozilla/5.0 podcast-sync/1.0"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = html.unescape(text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line).strip()


@dataclass
class Episode:
    guid: str
    episode_no: str
    title: str
    pub_date: str
    duration: str
    link: str
    audio_url: str
    audio_type: str
    audio_length: int | None
    cover_url: str
    description: str
    wechat_title: str
    wechat_description: str
    local_audio: str
    local_cover: str
    upload_status: str = "pending"
    uploaded_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "guid": self.guid,
            "episode_no": self.episode_no,
            "title": self.title,
            "pub_date": self.pub_date,
            "duration": self.duration,
            "link": self.link,
            "audio_url": self.audio_url,
            "audio_type": self.audio_type,
            "audio_length": self.audio_length,
            "cover_url": self.cover_url,
            "description": self.description,
            "wechat_title": self.wechat_title,
            "wechat_description": self.wechat_description,
            "local_audio": self.local_audio,
            "local_cover": self.local_cover,
            "upload_status": self.upload_status,
            "uploaded_at": self.uploaded_at,
            "notes": self.notes,
        }


def request_bytes(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def text_or_empty(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def html_to_text(raw_html: str) -> str:
    parser = TextExtractor()
    parser.feed(raw_html or "")
    parser.close()
    return parser.get_text()


def safe_filename(value: str, max_len: int = 90) -> str:
    value = html.unescape(value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "untitled")[:max_len].rstrip(" .")


def extension_from_url(url: str, default: str) -> str:
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix and re.fullmatch(r"\.[a-z0-9]{2,5}", suffix):
        return suffix
    return default


def parse_episode_no(title: str, index_from_latest: int) -> str:
    match = re.search(r"[-_ ](\d{1,4})$", title.strip())
    if match:
        return match.group(1).zfill(3)
    return f"rss-{index_from_latest:03d}"


def parse_pub_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %Z")
        return parsed.replace(tzinfo=timezone.utc).astimezone().isoformat(timespec="seconds")
    except ValueError:
        return value


def build_wechat_description(description: str, link: str, limit: int) -> str:
    footer = f"\n\n原节目链接：{link}" if link else ""
    body_limit = max(0, limit - len(footer))
    body = description[:body_limit].rstrip()
    return f"{body}{footer}".strip()


def parse_feed(feed_url: str, description_limit: int) -> tuple[dict[str, str], list[Episode]]:
    root = ET.fromstring(request_bytes(feed_url))
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS feed does not contain a channel element.")

    channel_image = ""
    channel_itunes_image = channel.find(f"{ITUNES_NS}image")
    if channel_itunes_image is not None:
        channel_image = channel_itunes_image.attrib.get("href", "")

    podcast = {
        "title": text_or_empty(channel.find("title")),
        "description": text_or_empty(channel.find("description")),
        "link": text_or_empty(channel.find("link")),
        "feed_url": feed_url,
        "image": channel_image,
        "synced_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    episodes: list[Episode] = []
    for index, item in enumerate(channel.findall("item"), start=1):
        title = text_or_empty(item.find("title"))
        guid = text_or_empty(item.find("guid")) or f"item-{index:03d}"
        episode_no = parse_episode_no(title, index)
        link = text_or_empty(item.find("link"))
        pub_date = parse_pub_date(text_or_empty(item.find("pubDate")))
        duration = text_or_empty(item.find(f"{ITUNES_NS}duration"))

        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
        audio_type = enclosure.attrib.get("type", "") if enclosure is not None else ""
        raw_length = enclosure.attrib.get("length", "") if enclosure is not None else ""
        audio_length = int(raw_length) if raw_length.isdigit() else None

        image = item.find(f"{ITUNES_NS}image")
        cover_url = image.attrib.get("href", "") if image is not None else channel_image

        raw_description = text_or_empty(item.find(f"{CONTENT_NS}encoded")) or text_or_empty(
            item.find("description")
        )
        description = html_to_text(raw_description)
        base_name = safe_filename(f"{episode_no}-{title}")
        audio_ext = extension_from_url(audio_url, ".m4a")
        cover_ext = extension_from_url(cover_url, ".jpg")

        episodes.append(
            Episode(
                guid=guid,
                episode_no=episode_no,
                title=title,
                pub_date=pub_date,
                duration=duration,
                link=link,
                audio_url=audio_url,
                audio_type=audio_type,
                audio_length=audio_length,
                cover_url=cover_url,
                description=description,
                wechat_title=title[:60],
                wechat_description=build_wechat_description(description, link, description_limit),
                local_audio=str((AUDIO_DIR / f"{base_name}{audio_ext}").relative_to(ROOT)),
                local_cover=str((COVER_DIR / f"{base_name}{cover_ext}").relative_to(ROOT)),
            )
        )

    return podcast, episodes


def load_existing_statuses() -> dict[str, dict[str, str]]:
    if not MANIFEST_JSON.exists():
        return {}
    try:
        data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    statuses: dict[str, dict[str, str]] = {}
    for item in data.get("episodes", []):
        guid = str(item.get("guid", ""))
        if guid:
            statuses[guid] = {
                "upload_status": str(item.get("upload_status", "pending")),
                "uploaded_at": str(item.get("uploaded_at", "")),
                "notes": str(item.get("notes", "")),
            }
    return statuses


def merge_statuses(episodes: Iterable[Episode], statuses: dict[str, dict[str, str]]) -> None:
    for episode in episodes:
        existing = statuses.get(episode.guid)
        if not existing:
            continue
        episode.upload_status = existing.get("upload_status", episode.upload_status)
        episode.uploaded_at = existing.get("uploaded_at", episode.uploaded_at)
        episode.notes = existing.get("notes", episode.notes)


def write_manifest(podcast: dict[str, str], episodes: list[Episode]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "podcast": podcast,
        "episodes": [episode.to_dict() for episode in episodes],
    }
    MANIFEST_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fieldnames = list(episodes[0].to_dict().keys()) if episodes else []
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for episode in episodes:
            writer.writerow(episode.to_dict())


def download_file(url: str, destination: Path, expected_size: int | None = None) -> str:
    if not url:
        return "missing-url"
    if destination.exists() and destination.stat().st_size > 0:
        if expected_size is None or destination.stat().st_size == expected_size:
            return "exists"

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    fd, temp_name = tempfile.mkstemp(prefix=destination.name, suffix=".part", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temp_path.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        temp_path.replace(destination)
        return "downloaded"
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def iter_selected(episodes: list[Episode], limit: int | None) -> list[Episode]:
    if limit is None:
        return episodes
    return episodes[:limit]


def refresh(args: argparse.Namespace) -> None:
    if not args.feed_url:
        raise ValueError("Missing --feed-url.")
    statuses = load_existing_statuses()
    podcast, episodes = parse_feed(args.feed_url, args.description_limit)
    merge_statuses(episodes, statuses)
    write_manifest(podcast, episodes)
    print(f"Podcast: {podcast['title']}")
    print(f"Episodes: {len(episodes)}")
    print(f"Wrote: {MANIFEST_JSON}")
    print(f"Wrote: {MANIFEST_CSV}")


def download(args: argparse.Namespace) -> None:
    if not MANIFEST_JSON.exists() or args.refresh:
        refresh(args)

    data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    episodes = data.get("episodes", [])
    selected = episodes if args.limit is None else episodes[: args.limit]
    print(f"Selected episodes: {len(selected)}")
    for index, episode in enumerate(selected, start=1):
        title = episode["title"]
        print(f"[{index}/{len(selected)}] {title}")
        if args.assets in {"all", "covers"}:
            result = download_file(episode["cover_url"], ROOT / episode["local_cover"])
            print(f"  cover: {result}")
        if args.assets in {"all", "audio"}:
            result = download_file(
                episode["audio_url"],
                ROOT / episode["local_audio"],
                episode.get("audio_length"),
            )
            print(f"  audio: {result}")
        if args.sleep > 0:
            time.sleep(args.sleep)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync podcast RSS metadata for WeChat audio.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh_parser = subparsers.add_parser("refresh", help="Fetch RSS and rebuild JSON/CSV queue.")
    refresh_parser.add_argument("--feed-url", required=True)
    refresh_parser.add_argument("--description-limit", type=int, default=1800)
    refresh_parser.set_defaults(func=refresh)

    download_parser = subparsers.add_parser("download", help="Download covers and/or audio files.")
    download_parser.add_argument("--feed-url", required=True)
    download_parser.add_argument("--description-limit", type=int, default=1800)
    download_parser.add_argument("--assets", choices=["covers", "audio", "all"], default="covers")
    download_parser.add_argument("--limit", type=int, default=None, help="Newest N episodes to download.")
    download_parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to wait between files.")
    download_parser.add_argument("--refresh", action="store_true", help="Refresh the RSS first.")
    download_parser.set_defaults(func=download)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
