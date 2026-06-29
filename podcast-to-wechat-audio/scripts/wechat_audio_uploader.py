#!/usr/bin/env python3
"""Semi-automate WeChat Channels audio uploads from the generated CSV queue."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from playwright.sync_api import (
        BrowserContext,
        Frame,
        Locator,
        Page,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )
except ImportError:  # pragma: no cover - exercised before dependency install
    BrowserContext = Any  # type: ignore
    Frame = Any  # type: ignore
    Locator = Any  # type: ignore
    Page = Any  # type: ignore
    PlaywrightTimeoutError = TimeoutError  # type: ignore
    sync_playwright = None  # type: ignore


ROOT = Path.cwd()
QUEUE_CSV = ROOT / "data" / "wechat_audio_upload_queue.csv"
MANIFEST_JSON = ROOT / "data" / "episodes.json"
SCREENSHOT_DIR = ROOT / "logs" / "screenshots"
DEBUG_DIR = ROOT / "logs" / "debug"
PROFILE_DIR = ROOT / ".wechat-profile"
WECHAT_AUDIO_DIR = ROOT / "downloads" / "wechat_audio"
DEFAULT_URL = "https://channels.weixin.qq.com/platform"
CREATE_AUDIO_URL = "https://channels.weixin.qq.com/platform/post/createAudio"
AUDIO_MANAGER_URL = "https://channels.weixin.qq.com/platform/post/audioManager"
DEFAULT_TITLE_MAX_CHARS = 40


TEXT = {
    "audio_menu": "\u97f3\u9891",
    "content_menu": "\u5185\u5bb9\u7ba1\u7406",
    "publish_audio": "\u53d1[\u5e03\u8868]\u97f3\u9891",
    "save_draft": "\u4fdd\u5b58\u8349\u7a3f",
    "draft": "\u8349\u7a3f",
    "publish": "\u53d1\u8868",
    "confirm": "\u786e\u5b9a",
    "title": "\u6807\u9898",
    "description": "\u7b80\u4ecb",
    "cover": "\u5c01\u9762",
    "upload_audio": "\u4e0a\u4f20\u97f3\u9891",
    "upload_cover": "\u4e0a\u4f20\u5c01\u9762",
}


@dataclass
class QueueItem:
    row_index: int
    data: dict[str, str]

    @property
    def guid(self) -> str:
        return self.data.get("guid", "")

    @property
    def title(self) -> str:
        return self.data.get("wechat_title") or self.data.get("title", "")

    @property
    def description(self) -> str:
        return self.data.get("wechat_description") or self.data.get("description", "")

    @property
    def audio_path(self) -> Path:
        return resolve_path(self.data.get("local_audio", ""))

    @property
    def cover_path(self) -> Path:
        return resolve_path(self.data.get("local_cover", ""))

    @property
    def audio_url(self) -> str:
        return self.data.get("audio_url", "")

    @property
    def cover_url(self) -> str:
        return self.data.get("cover_url", "")

    @property
    def audio_length(self) -> int | None:
        raw = self.data.get("audio_length", "")
        return int(raw) if raw.isdigit() else None


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def fit_wechat_title(title: str, episode_no: str, max_chars: int = DEFAULT_TITLE_MAX_CHARS) -> str:
    title = title.strip()
    if max_chars <= 0 or len(title) <= max_chars:
        return title

    suffix = ""
    if re.fullmatch(r"\d{3}", episode_no or ""):
        candidate = f"-{episode_no}"
        if title.endswith(candidate):
            suffix = candidate
    elif title.endswith("-番外"):
        suffix = "-番外"

    if suffix:
        base = title[: -len(suffix)].rstrip(" -_")
        available = max_chars - len(suffix)
        if available > 0:
            return base[:available].rstrip(" ，。！？、…-") + suffix

    return title[:max_chars].rstrip(" ，。！？、…-")


def apply_title_limit(item: QueueItem, max_chars: int) -> None:
    title = item.title
    fitted = fit_wechat_title(title, item.data.get("episode_no", ""), max_chars)
    if fitted != title:
        print(f"Shortening title to {len(fitted)}/{max_chars} chars: {fitted}")
        item.data["wechat_title"] = fitted


def require_playwright() -> None:
    if sync_playwright is None:
        print("Playwright is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        print("Then run: python -m playwright install chromium", file=sys.stderr)
        raise SystemExit(2)


def read_queue(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    return rows, fieldnames


def write_queue(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def update_manifest_status(guid: str, status: str, note: str = "") -> None:
    if not MANIFEST_JSON.exists() or not guid:
        return
    data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    for episode in data.get("episodes", []):
        if episode.get("guid") == guid:
            episode["upload_status"] = status
            episode["uploaded_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            if note:
                episode["notes"] = note
            break
    MANIFEST_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_queue_status(
    queue_path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    item: QueueItem,
    status: str,
    note: str = "",
) -> None:
    row = rows[item.row_index]
    row["upload_status"] = status
    row["uploaded_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    if note:
        row["notes"] = note
    write_queue(queue_path, rows, fieldnames)
    update_manifest_status(item.guid, status, note)


def selected_items(rows: list[dict[str, str]], status: str, limit: int | None, episode_no: str | None) -> list[QueueItem]:
    items: list[QueueItem] = []
    for index, row in enumerate(rows):
        if episode_no and row.get("episode_no") != episode_no:
            continue
        if status != "all" and row.get("upload_status", "pending") != status:
            continue
        items.append(QueueItem(index, row))
        if limit is not None and len(items) >= limit:
            break
    return items


def ensure_assets(item: QueueItem, download_missing: bool) -> None:
    missing: list[str] = []
    if not item.audio_path.exists():
        missing.append(f"audio: {item.audio_path}")
    if not item.cover_path.exists():
        missing.append(f"cover: {item.cover_path}")
    if not missing:
        return
    if not download_missing:
        raise FileNotFoundError("Missing files. Use --download-missing first:\n" + "\n".join(missing))

    import sync_feed

    if not item.cover_path.exists():
        print(f"Downloading cover: {item.cover_path.name}")
        sync_feed.download_file(item.cover_url, item.cover_path)
    if not item.audio_path.exists():
        print(f"Downloading audio: {item.audio_path.name}")
        sync_feed.download_file(item.audio_url, item.audio_path, item.audio_length)


def planned_wechat_audio_path(item: QueueItem, transcode: bool) -> Path:
    source = item.audio_path
    if source.suffix.lower() in {".mp3", ".wav"} or not transcode:
        return source
    return WECHAT_AUDIO_DIR / f"{source.stem}.mp3"


def preflight_item(item: QueueItem, args: argparse.Namespace, prepare: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    apply_title_limit(item, args.title_max_chars)

    if prepare and args.download_missing:
        try:
            ensure_assets(item, download_missing=True)
        except Exception as exc:
            errors.append(f"asset download failed: {type(exc).__name__}: {exc}")

    if args.title_max_chars > 0 and len(item.title) > args.title_max_chars:
        errors.append(f"title is {len(item.title)} chars after fitting; max is {args.title_max_chars}")
    if not item.description.strip():
        warnings.append("description is empty")

    audio_exists = item.audio_path.exists()
    cover_exists = item.cover_path.exists()
    if not audio_exists and not args.download_missing:
        errors.append(f"audio is missing: {item.audio_path}")
    if not cover_exists and not args.download_missing:
        errors.append(f"cover is missing: {item.cover_path}")
    if not audio_exists and args.download_missing and not item.audio_url:
        errors.append("audio is missing and audio_url is empty")
    if not cover_exists and args.download_missing and not item.cover_url:
        errors.append("cover is missing and cover_url is empty")

    planned_audio = planned_wechat_audio_path(item, args.transcode_mp3)
    if item.audio_path.suffix.lower() not in {".mp3", ".wav"} and args.transcode_mp3:
        try:
            find_ffmpeg()
        except FileNotFoundError as exc:
            errors.append(str(exc))
        if prepare and item.audio_path.exists():
            try:
                wechat_audio_path(item, args.transcode_mp3)
            except Exception as exc:
                errors.append(f"audio transcode failed: {type(exc).__name__}: {exc}")
        if planned_audio.exists() and item.audio_path.exists() and planned_audio.stat().st_mtime < item.audio_path.stat().st_mtime:
            warnings.append(f"cached MP3 is older than source and will be regenerated: {planned_audio}")

    return errors, warnings


def preflight_items(items: list[QueueItem], args: argparse.Namespace, prepare: bool = False) -> bool:
    ok = True
    for item in items:
        errors, warnings = preflight_item(item, args, prepare=prepare)
        print(f"{item.data.get('episode_no')} | {item.title}")
        print(f"  audio: {item.audio_path} ({'ok' if item.audio_path.exists() else 'missing'})")
        print(f"  cover: {item.cover_path} ({'ok' if item.cover_path.exists() else 'missing'})")
        print(f"  wechat audio: {planned_wechat_audio_path(item, args.transcode_mp3)}")
        for warning in warnings:
            print(f"  warning: {warning}")
        for error in errors:
            print(f"  error: {error}")
        if errors:
            ok = False
    return ok


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates = sorted(Path(local).glob("ms-playwright/ffmpeg-*/ffmpeg*.exe"))
        if candidates:
            return str(candidates[-1])
    raise FileNotFoundError("ffmpeg was not found. Install ffmpeg or run python -m playwright install chromium.")


def wechat_audio_path(item: QueueItem, transcode: bool) -> Path:
    source = item.audio_path
    if source.suffix.lower() in {".mp3", ".wav"}:
        return source
    if not transcode:
        return source
    WECHAT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    target = WECHAT_AUDIO_DIR / f"{source.stem}.mp3"
    if target.exists() and target.stat().st_size > 0 and target.stat().st_mtime >= source.stat().st_mtime:
        return target

    ffmpeg = find_ffmpeg()
    print(f"Transcoding for WeChat audio: {source.name} -> {target.name}")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(target),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return target


def launch_context(args: argparse.Namespace) -> tuple[Any, BrowserContext]:
    require_playwright()
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(args.profile),
        headless=False,
        accept_downloads=True,
        viewport={"width": 1440, "height": 950},
        args=["--disable-blink-features=AutomationControlled"],
    )
    return playwright, context


def close_context(playwright: Any, context: BrowserContext) -> None:
    context.close()
    playwright.stop()


def visible_count(locator: Locator) -> int:
    try:
        count = locator.count()
    except Exception:
        return 0
    total = 0
    for index in range(count):
        try:
            if locator.nth(index).is_visible():
                total += 1
        except Exception:
            continue
    return total


def click_first(page: Page, candidates: Iterable[Any], timeout: int = 2500) -> bool:
    for scope in page_scopes(page):
        for candidate in candidates:
            try:
                locator = candidate(scope) if callable(candidate) else scope.locator(candidate)
                if locator.count() == 0:
                    continue
                first = locator.first
                first.wait_for(state="visible", timeout=timeout)
                first.click(timeout=timeout)
                return True
            except Exception:
                continue
    return False


def fill_first(page: Page, value: str, candidates: Iterable[Any], timeout: int = 2500) -> bool:
    for scope in page_scopes(page):
        for candidate in candidates:
            try:
                locator = candidate(scope) if callable(candidate) else scope.locator(candidate)
                if locator.count() == 0:
                    continue
                first = locator.first
                first.wait_for(state="visible", timeout=timeout)
                first.fill(value, timeout=timeout)
                return True
            except Exception:
                continue
    return False


def upload_by_file_input(page: Page, path: Path, kind: str) -> bool:
    patterns = {
        "audio": re.compile(r"audio|mp3|m4a|wav|aac", re.I),
        "image": re.compile(r"image|jpg|jpeg|png|webp", re.I),
    }
    for scope in page_scopes(page):
        inputs = scope.locator("input[type='file']")
        for index in range(inputs.count()):
            input_locator = inputs.nth(index)
            accept = input_locator.get_attribute("accept") or ""
            if patterns[kind].search(accept):
                input_locator.set_input_files(str(path))
                return True
    return False


def upload_by_file_chooser(page: Page, path: Path, labels: list[str], timeout: int = 5000) -> bool:
    for label in labels:
        candidates = [
            lambda p, label=label: p.get_by_role("button", name=re.compile(label)),
            lambda p, label=label: p.get_by_text(re.compile(label)),
            f"text={label}",
        ]
        for scope in page_scopes(page):
            for candidate in candidates:
                try:
                    locator = candidate(scope) if callable(candidate) else scope.locator(candidate)
                    if locator.count() == 0:
                        continue
                    with page.expect_file_chooser(timeout=timeout) as file_chooser_info:
                        locator.first.click(timeout=timeout)
                    file_chooser_info.value.set_files(str(path))
                    return True
                except Exception:
                    continue
    return False


def upload_asset(page: Page, path: Path, kind: str) -> bool:
    if upload_by_file_input(page, path, kind):
        return True
    labels = (
        [TEXT["upload_audio"], "\u9009\u62e9\u97f3\u9891", "\u70b9\u51fb\u4e0a\u4f20"]
        if kind == "audio"
        else [TEXT["upload_cover"], "\u66f4\u6362\u5c01\u9762", TEXT["cover"], "\u70b9\u51fb\u4e0a\u4f20"]
    )
    return upload_by_file_chooser(page, path, labels)


def click_text_center(page: Page, text: str, timeout: int = 3000) -> bool:
    locator = page.get_by_text(text, exact=True)
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        try:
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if not candidate.is_visible():
                    continue
                box = candidate.bounding_box()
                if not box:
                    continue
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def page_scopes(page: Page) -> list[Any]:
    scopes: list[Any] = [page]
    scopes.extend(frame for frame in page.frames if frame != page.main_frame)
    return scopes


def click_visible_text_with_dom(scope: Any, text: str) -> bool:
    return bool(
        scope.evaluate(
            """(text) => {
                const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.visibility !== 'hidden'
                        && style.display !== 'none'
                        && rect.width > 0
                        && rect.height > 0;
                };
                const elements = Array.from(document.querySelectorAll('button, a, div, span'));
                const matches = elements
                    .filter((el) => (el.innerText || el.textContent || '').trim() === text)
                    .filter(visible)
                    .map((el) => {
                        const clickable = el.closest('button, a, [role="button"]') || el;
                        const rect = clickable.getBoundingClientRect();
                        return { el: clickable, y: rect.y, x: rect.x };
                    })
                    .sort((a, b) => (b.y - a.y) || (b.x - a.x));
                if (!matches.length) return false;
                matches[0].el.click();
                return true;
            }""",
            text,
        )
    )


def cover_modal_visible(scope: Any) -> bool:
    try:
        return bool(
            scope.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    return Array.from(document.querySelectorAll('.weui-desktop-dialog'))
                        .some((el) => visible(el) && (el.innerText || '').includes('编辑音频封面'));
                }"""
            )
        )
    except Exception:
        return False


def click_cover_modal_confirm(scope: Any) -> bool:
    try:
        return bool(
            scope.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const dialog = Array.from(document.querySelectorAll('.weui-desktop-dialog'))
                        .find((el) => visible(el) && (el.innerText || '').includes('编辑音频封面'));
                    if (!dialog) return false;
                    const btn = Array.from(dialog.querySelectorAll('.weui-desktop-dialog__ft button, .weui-desktop-dialog__ft [role="button"]'))
                        .find((el) => visible(el) && (el.innerText || el.textContent || '').trim() === '确认');
                    if (!btn) return false;
                    btn.focus && btn.focus();
                    const rect = btn.getBoundingClientRect();
                    const opts = {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: rect.left + rect.width / 2,
                        clientY: rect.top + rect.height / 2,
                    };
                    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
                        btn.dispatchEvent(new MouseEvent(type, opts));
                    }
                    btn.click();
                    return true;
                }"""
            )
        )
    except Exception:
        return False


def click_modal_confirm_button(page: Page) -> None:
    for scope in page_scopes(page):
        if click_cover_modal_confirm(scope):
            page.wait_for_timeout(1000)
            if not cover_modal_visible(scope):
                return
        attempts = [
            lambda scope=scope: scope.locator(
                ".weui-desktop-dialog__ft button.weui-desktop-btn_primary"
            ).last.click(timeout=2000, force=True),
            lambda scope=scope: scope.locator("button").filter(has_text=TEXT["confirm"]).last.click(
                timeout=2000,
                force=True,
            ),
            lambda scope=scope: scope.locator("[role='button']").filter(has_text=TEXT["confirm"]).last.click(
                timeout=2000,
                force=True,
            ),
            lambda scope=scope: scope.locator("text=\u786e\u8ba4").last.click(timeout=2000, force=True),
            lambda scope=scope: scope.evaluate(
                """() => {
                    const btn = Array.from(document.querySelectorAll('.weui-desktop-dialog__ft button, .weui-desktop-dialog__ft [role="button"]'))
                        .find((el) => (el.innerText || el.textContent || '').trim() === '确认');
                    if (!btn) return false;
                    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
                        btn.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
                    }
                    return true;
                }"""
            ),
            lambda scope=scope: click_visible_text_with_dom(scope, TEXT["confirm"]),
        ]
        for attempt in attempts:
            try:
                attempt()
                page.wait_for_timeout(1000)
                if not cover_modal_visible(scope):
                    return
            except Exception:
                continue

    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    if not any(cover_modal_visible(scope) for scope in page_scopes(page)):
        return

    viewport = page.viewport_size or {"width": 1440, "height": 950}
    for x_ratio, y_ratio in [(0.54, 0.785), (0.54, 0.79), (0.55, 0.785)]:
        try:
            page.mouse.click(viewport["width"] * x_ratio, viewport["height"] * y_ratio)
            page.wait_for_timeout(1000)
            if not any(cover_modal_visible(scope) for scope in page_scopes(page)):
                return
        except Exception:
            continue


def confirm_cover_modal(page: Page, timeout_ms: int = 60000, manual_wait_ms: int = 30000) -> bool:
    def modal_is_visible() -> bool:
        return any(cover_modal_visible(scope) for scope in page_scopes(page))

    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if modal_is_visible():
            click_modal_confirm_button(page)
            page.wait_for_timeout(1500)
            if not modal_is_visible():
                return True
        time.sleep(1)
    manual_deadline = time.time() + manual_wait_ms / 1000
    while time.time() < manual_deadline:
        if not modal_is_visible():
            return True
        time.sleep(1)
    return False


def wait_for_login_or_dashboard(page: Page, timeout_ms: int) -> None:
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if page.get_by_text(re.compile(TEXT["publish_audio"])).count() > 0:
            return
        if page.get_by_text(re.compile(TEXT["audio_menu"])).count() > 0:
            return
        time.sleep(1)
    raise TimeoutError("Timed out waiting for WeChat Channels login/dashboard.")


def goto_audio_manager(page: Page, url: str, login_timeout: int) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    print("If a QR code is shown, scan it in WeChat. Waiting for the dashboard...")
    wait_for_login_or_dashboard(page, login_timeout * 1000)

    click_first(
        page,
        [
            lambda p: p.get_by_text(TEXT["content_menu"], exact=True),
            lambda p: p.get_by_role("menuitem", name=re.compile(TEXT["content_menu"])),
        ],
        timeout=1500,
    )
    click_first(
        page,
        [
            lambda p: p.get_by_text(TEXT["audio_menu"], exact=True),
            lambda p: p.get_by_role("menuitem", name=re.compile(TEXT["audio_menu"])),
            lambda p: p.get_by_role("link", name=re.compile(TEXT["audio_menu"])),
        ],
        timeout=1500,
    )
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(3000)


def wait_for_publish_button(page: Page, timeout_ms: int = 30000) -> bool:
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if page.get_by_role("button", name=re.compile(TEXT["publish_audio"])).count() > 0:
            return True
        if page.get_by_text(re.compile(TEXT["publish_audio"])).count() > 0:
            return True
        time.sleep(1)
    return False


def open_publish_form(page: Page) -> None:
    for attempt in range(3):
        page.goto(CREATE_AUDIO_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(3000)
        if audio_upload_control_present(page):
            return

        if wait_for_publish_button(page, timeout_ms=5000):
            click_first(
                page,
                [
                    lambda p: p.get_by_role("button", name=re.compile(TEXT["publish_audio"])),
                    lambda p: p.get_by_text(re.compile(TEXT["publish_audio"])),
                ],
                timeout=5000,
            )
            page.wait_for_timeout(3000)
            if audio_upload_control_present(page):
                return
    raise RuntimeError("Could not open the Publish Audio form.")


def audio_upload_control_present(page: Page) -> bool:
    for scope in page_scopes(page):
        try:
            inputs = scope.locator("input[type='file']")
            for index in range(inputs.count()):
                accept = inputs.nth(index).get_attribute("accept") or ""
                if re.search(r"audio|mp3|wav|aac|m4a", accept, re.I):
                    return True
            if scope.get_by_text(re.compile("\u4e0a\u4f20\u6587\u4ef6")).count() > 0:
                return True
        except Exception:
            continue
    return False


def fill_form(page: Page, item: QueueItem, args: argparse.Namespace) -> None:
    audio_path = wechat_audio_path(item, args.transcode_mp3)
    if not upload_asset(page, audio_path, "audio"):
        raise RuntimeError("Could not find an audio upload control.")
    page.wait_for_timeout(1000)

    if not upload_asset(page, item.cover_path, "image"):
        print("Cover upload control was not found; continuing so you can set it manually.")
    page.wait_for_timeout(1000)
    if not confirm_cover_modal(
        page,
        timeout_ms=60000,
        manual_wait_ms=args.manual_cover_confirm_seconds * 1000,
    ):
        raise RuntimeError("Cover crop confirmation did not close. Please click the cover Confirm button manually.")

    title_ok = fill_first(
        page,
        item.title,
        [
            lambda p: p.get_by_placeholder(re.compile(TEXT["title"])),
            "input[placeholder*='\u6807\u9898']",
            "textarea[placeholder*='\u6807\u9898']",
        ],
    )
    if not title_ok:
        raise RuntimeError("Could not find the title field.")

    fill_first(
        page,
        item.description,
        [
            lambda p: p.get_by_placeholder(re.compile(TEXT["description"])),
            lambda p: p.get_by_placeholder(re.compile("\u63cf\u8ff0|\u4ecb\u7ecd|\u8bf4\u70b9")),
            "textarea[placeholder*='\u7b80\u4ecb']",
            "textarea[placeholder*='\u63cf\u8ff0']",
            "textarea",
        ],
    )


def wait_for_upload_settle(page: Page, seconds: int) -> bool:
    print(f"Waiting up to {seconds}s for the submit button to become usable and upload progress to disappear...")
    last_error = ""
    progress_visible = False
    for _ in range(seconds):
        confirm_cover_modal(page, timeout_ms=500, manual_wait_ms=0)
        last_error = submission_error_text(page)
        progress_visible = upload_progress_visible(page)
        if submit_button_ready(page) and not last_error and not progress_visible:
            page.wait_for_timeout(3000)
            last_error = submission_error_text(page)
            progress_visible = upload_progress_visible(page)
            if submit_button_ready(page) and not last_error and not progress_visible:
                return True
        page.wait_for_timeout(1000)
    if last_error:
        print(f"Upload did not settle; visible page error remains: {last_error}")
    elif progress_visible:
        print("Upload did not settle; upload progress is still visible.")
    else:
        print("Submit button did not become clearly usable; continuing with screenshot for inspection.")
    return False


def submit_button_ready(page: Page) -> bool:
    for scope in page_scopes(page):
        try:
            if scope.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const buttons = Array.from(document.querySelectorAll('button, [role="button"], .weui-desktop-btn'));
                    return buttons.some((el) => {
                        const text = (el.innerText || el.textContent || '').trim();
                        const disabled = Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true');
                        return visible(el) && !disabled && /发表音频|发布音频/.test(text);
                    });
                }"""
            ):
                return True
        except Exception:
            continue
    return False


def click_submit(page: Page, mode: str) -> bool:
    if mode == "pause":
        return False
    if mode == "draft":
        labels = [TEXT["save_draft"], "\u5b58\u8349\u7a3f", "\u4fdd\u5b58"]
    elif mode == "publish":
        labels = [TEXT["publish"], "\u53d1\u5e03", "\u7acb\u5373\u53d1\u5e03"]
    else:
        raise ValueError(f"Unsupported submit mode: {mode}")

    clicked = click_first(
        page,
        [
            lambda p, label=label: p.get_by_role("button", name=re.compile(label))
            for label in labels
        ]
        + [lambda p, label=label: p.get_by_text(re.compile(label)) for label in labels],
        timeout=5000,
    )
    if not clicked:
        return False

    page.wait_for_timeout(1200)
    click_first(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(TEXT["confirm"])),
            lambda p: p.get_by_text(TEXT["confirm"], exact=True),
            lambda p: p.get_by_role("button", name=re.compile("\u786e\u8ba4")),
        ],
        timeout=2000,
    )
    return True


def collect_visible_text(page: Page) -> str:
    parts: list[str] = []
    for scope in page_scopes(page):
        try:
            parts.append(scope.evaluate("document.body ? document.body.innerText : ''"))
        except Exception:
            continue
    return "\n".join(part for part in parts if part)


def submission_error_text(page: Page) -> str:
    text = collect_visible_text(page)
    patterns = [
        "\u8bf7\u4e0a\u4f20\u97f3\u9891",
        "\u97f3\u9891\u4fe1\u606f\u4e0d\u7b26\u5408\u8981\u6c42",
        "\u4e0d\u7b26\u5408\u8981\u6c42",
        "\u8bf7\u4fee\u6539",
    ]
    for pattern in patterns:
        if pattern in text:
            return pattern
    return ""


def upload_progress_visible(page: Page) -> bool:
    for scope in page_scopes(page):
        try:
            if scope.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const percentText = /(^|\\s)(?:[1-9]?\\d|100)%(\\s|$)/;
                    return Array.from(document.querySelectorAll('div, span, p, i, em, strong'))
                        .some((el) => visible(el) && percentText.test((el.innerText || el.textContent || '').trim()));
                }"""
            ):
                return True
        except Exception:
            continue
    return False


def manager_frame(page: Page) -> Any:
    for frame in page.frames:
        if "micro/content/post/audioManager" in frame.url:
            return frame
    return page.main_frame


def scroll_manager_to_bottom(scope: Any) -> None:
    scope.evaluate(
        """() => {
            const scrollables = Array.from(document.querySelectorAll('*'))
                .filter((el) => el.scrollHeight > el.clientHeight + 100)
                .sort((a, b) => (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
            if (scrollables[0]) scrollables[0].scrollTop = scrollables[0].scrollHeight;
            if (document.scrollingElement) {
                document.scrollingElement.scrollTop = document.scrollingElement.scrollHeight;
            }
        }"""
    )


def click_manager_page(scope: Any, page_number: int) -> bool:
    return bool(
        scope.evaluate(
            """(pageNumber) => {
                const labels = Array.from(document.querySelectorAll('label.weui-desktop-pagination__num'));
                const target = labels.find((el) => (el.innerText || el.textContent || '').trim() === String(pageNumber));
                if (!target) return false;
                target.click();
                return true;
            }""",
            page_number,
        )
    )


def item_match_needles(item: QueueItem) -> list[str]:
    needles = []
    title = item.title.strip()
    if title:
        needles.append(title)
        for size in (30, 20, 12):
            if len(title) > size:
                needles.append(title[:size])
    episode_no = item.data.get("episode_no", "").strip()
    if re.fullmatch(r"\d{3}", episode_no):
        needles.extend([f"-{episode_no}", f"-{int(episode_no)}"])
    elif episode_no:
        needles.append(episode_no)
    return [needle for needle in dict.fromkeys(needles) if needle]


def text_matches_item(text: str, item: QueueItem) -> bool:
    return any(needle in text for needle in item_match_needles(item))


def text_has_published_item(text: str, item: QueueItem) -> bool:
    # Rows in the audio manager are exposed as text blocks containing title,
    # metrics, status, and actions. Require the row status to be published.
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
    for block in blocks:
        if text_matches_item(block, item) and "\u5df2\u53d1\u8868" in block:
            return True
    return False


def verify_published_in_manager(page: Page, item: QueueItem, pages: int = 2) -> bool:
    page.goto(AUDIO_MANAGER_URL, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(5000)

    scope = manager_frame(page)
    for page_number in range(1, max(1, pages) + 1):
        if page_number > 1:
            scroll_manager_to_bottom(scope)
            if not click_manager_page(scope, page_number):
                return False
            page.wait_for_timeout(4000)
            scope = manager_frame(page)
        text = collect_visible_text(page)
        if text_has_published_item(text, item):
            return True
    return False


def verify_submission_success(
    page: Page,
    item: QueueItem,
    mode: str,
    verify_pages: int,
    verify_wait_seconds: int,
) -> str:
    page.wait_for_timeout(3000)
    error_text = submission_error_text(page)
    if error_text:
        raise RuntimeError(f"Submit failed with visible page error: {error_text}")

    if mode == "draft":
        return "drafted"

    if mode != "publish":
        raise ValueError(f"Unsupported submit mode: {mode}")

    deadline = time.time() + max(0, verify_wait_seconds)
    attempt = 0
    while True:
        attempt += 1
        if verify_published_in_manager(page, item, pages=verify_pages):
            return "uploaded"
        if time.time() >= deadline:
            break
        print(f"Publish not verified as 已发表 yet; waiting before recheck #{attempt + 1}...")
        page.wait_for_timeout(10000)

    raise RuntimeError(
        "Submit click did not verify as published in WeChat audio manager. "
        "Queue status left as error for manual inspection/retry."
    )


def screenshot(page: Page, stem: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{stem}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def write_debug_snapshot(page: Page, stem: str) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "url": page.url,
        "viewport": page.viewport_size,
        "frames": [],
    }
    for frame in page.frames:
        try:
            frame_data = frame.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.visibility !== 'hidden'
                            && style.display !== 'none'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const interesting = Array.from(document.querySelectorAll('button, [role="button"], a, div, span'))
                        .map((el) => {
                            const text = (el.innerText || el.textContent || '').trim();
                            const rect = el.getBoundingClientRect();
                            return {
                                tag: el.tagName,
                                role: el.getAttribute('role'),
                                className: String(el.className || ''),
                                text,
                                visible: visible(el),
                                disabled: Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true'),
                                rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                            };
                        })
                        .filter((item) => item.text.includes('确认') || item.text.includes('编辑音频封面') || item.text.includes('取消'))
                        .slice(-80);
                    return {
                        title: document.title,
                        bodyTextStart: (document.body && document.body.innerText || '').slice(0, 500),
                        interesting,
                    };
                }"""
            )
        except Exception as exc:
            frame_data = {"error": f"{type(exc).__name__}: {exc}"}
        payload["frames"].append({"url": frame.url, "data": frame_data})
    path = DEBUG_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{stem}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def process_item(page: Page, item: QueueItem, args: argparse.Namespace) -> str:
    apply_title_limit(item, args.title_max_chars)
    print(f"\nProcessing {item.data.get('episode_no')}: {item.title}")
    ensure_assets(item, args.download_missing)
    open_publish_form(page)
    fill_form(page, item, args)
    upload_ready = wait_for_upload_settle(page, args.upload_wait)
    shot = screenshot(page, f"filled-{item.data.get('episode_no', item.guid)}")
    print(f"Filled form screenshot: {shot}")

    if args.submit_mode == "pause":
        if args.wait_for_enter:
            print("Inspect the browser. Press Enter here to continue, or Ctrl+C to stop.")
            input()
        else:
            print(f"Non-interactive shell; keeping browser open for {args.pause_seconds}s.")
            time.sleep(args.pause_seconds)
        return "filled"

    if not upload_ready:
        raise RuntimeError("Upload did not become valid before submit; not clicking publish.")

    if click_submit(page, args.submit_mode):
        status = verify_submission_success(
            page,
            item,
            args.submit_mode,
            args.verify_pages,
            args.publish_verify_wait,
        )
        screenshot(page, f"{status}-{item.data.get('episode_no', item.guid)}")
        return status

    raise RuntimeError(f"Could not click submit button for mode: {args.submit_mode}")


def dry_run(items: list[QueueItem], args: argparse.Namespace) -> None:
    preflight_items(items, args, prepare=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload podcast RSS episodes to WeChat Channels audio.")
    parser.add_argument("--queue", type=Path, default=QUEUE_CSV)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--profile", type=Path, default=PROFILE_DIR)
    parser.add_argument("--status", default="pending", help="Queue status to process, or all.")
    parser.add_argument("--episode-no", default=None, help="Only process one episode number, such as 091.")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--download-missing", action="store_true")
    parser.add_argument("--upload-wait", type=int, default=90)
    parser.add_argument("--verify-pages", type=int, default=2, help="Audio manager pages to scan before marking publish as uploaded.")
    parser.add_argument("--title-max-chars", type=int, default=DEFAULT_TITLE_MAX_CHARS, help="Shorten titles to this WeChat limit before submitting.")
    parser.add_argument("--publish-verify-wait", type=int, default=180, help="Seconds to wait for a submitted audio row to become 已发表.")
    parser.add_argument("--pause-seconds", type=int, default=120)
    parser.add_argument("--wait-for-enter", action="store_true")
    parser.add_argument("--manual-cover-confirm-seconds", type=int, default=30)
    parser.add_argument("--no-transcode-mp3", dest="transcode_mp3", action="store_false")
    parser.set_defaults(transcode_mp3=True)
    parser.add_argument("--submit-mode", choices=["pause", "draft", "publish"], default="pause")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight", action="store_true", help="Validate selected queue rows without opening the browser.")
    args = parser.parse_args(argv)

    rows, fieldnames = read_queue(args.queue)
    items = selected_items(rows, args.status, args.limit, args.episode_no)
    if not items:
        print("No queue items matched.")
        return 0
    if args.dry_run:
        dry_run(items, args)
        return 0
    if args.preflight:
        return 0 if preflight_items(items, args, prepare=True) else 1

    playwright, context = launch_context(args)
    page = context.pages[0] if context.pages else context.new_page()
    try:
        goto_audio_manager(page, args.url, login_timeout=300)
        for item in items:
            try:
                status = process_item(page, item, args)
                update_queue_status(args.queue, rows, fieldnames, item, status)
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                shot = screenshot(page, f"error-{item.data.get('episode_no', item.guid)}")
                debug = write_debug_snapshot(page, f"error-{item.data.get('episode_no', item.guid)}")
                note = f"{type(exc).__name__}: {exc}; screenshot={shot}; debug={debug}"
                print(note, file=sys.stderr)
                update_queue_status(args.queue, rows, fieldnames, item, "error", note)
                if not args.download_missing:
                    print("Stopping after error. Fix it or rerun with a narrower --episode-no.")
                    return 1
        return 0
    finally:
        close_context(playwright, context)


if __name__ == "__main__":
    raise SystemExit(main())
