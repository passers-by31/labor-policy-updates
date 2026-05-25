#!/usr/bin/env python3
"""监视 Chrome 收藏夹变化，自动同步到爬虫配置并推送。

用法：
  # 默认监视（自动检测 Chrome 书签文件）
  python crawler/watch_bookmarks.py

  # 指定轮询间隔（秒）
  python crawler/watch_bookmarks.py --interval 15

  # 指定 Chrome 书签文件路径
  python crawler/watch_bookmarks.py --bookmarks /path/to/Bookmarks
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_DIR = PROJECT_ROOT / "crawler"
SYNC_SCRIPT = CRAWLER_DIR / "sync_bookmarks.py"

# Chrome 书签路径（同时支持旧版 Bookmarks 和新版 AccountBookmarks）
CHROME_PATHS = [
    Path.home() / "Library/Application Support/Google/Chrome/Default/Bookmarks",
    Path.home() / "Library/Application Support/Google/Chrome/Default/AccountBookmarks",
    *sorted(
        Path.home().glob("Library/Application Support/Google/Chrome/Profile */Bookmarks")
    ),
    *sorted(
        Path.home().glob("Library/Application Support/Google/Chrome/Profile */AccountBookmarks")
    ),
    Path.home() / ".config/google-chrome/Default/Bookmarks",
    Path.home() / ".config/chromium/Default/Bookmarks",
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Google/Chrome/User Data/Default/Bookmarks",
]

# 自动提交的文件
TRACKED_FILES = [
    "crawler/config.yaml",
    "data/sources.json",
]

POLL_INTERVAL = 10
DEBOUNCE_SECS = 3


def _find_bookmarks() -> Path | None:
    for p in CHROME_PATHS:
        if p and p.exists():
            return p
    return None


def _folder_bookmarks_hash(path: Path, folder: str) -> str:
    """提取指定文件夹的书签内容并计算哈希，忽略 Chrome 的元数据变更。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""

    bookmarks = []

    def walk(node: dict, parent: str = "") -> None:
        t = node.get("type", "")
        n = node.get("name", "")
        if t == "folder":
            for child in node.get("children", []):
                walk(child, n if n else parent)
        elif t == "url":
            u = node.get("url", "")
            if u and not u.startswith(("chrome://", "javascript:")):
                if parent == folder:
                    bookmarks.append(f"{n}|{u}")

    for root_key in ("bookmark_bar", "other", "synced"):
        root = data.get("roots", {}).get(root_key)
        if root:
            for child in root.get("children", []):
                walk(child)

    bookmarks.sort()
    return hashlib.md5("\n".join(bookmarks).encode()).hexdigest()


def _git_is_clean(repo: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True, text=True, timeout=10,
    )
    for line in result.stdout.splitlines():
        f = line.strip().split()[-1] if line.strip() else ""
        # 忽略 tracked files 的修改（这些本来就是我们要提交的）
        if f not in TRACKED_FILES:
            return False
    return True


def _git_commit_and_push(repo: Path) -> bool:
    """自动提交并推送配置变更。"""
    # add tracked files
    subprocess.run(
        ["git", "add"] + TRACKED_FILES,
        cwd=repo, capture_output=True, timeout=10,
    )

    # 检查是否有变更需要提交
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo, capture_output=True, timeout=10,
    )
    if result.returncode == 0:
        return False  # 无变更

    date_str = time.strftime("%Y-%m-%d %H:%M")
    msg = f"chore(config): 自动同步书签配置 {date_str}"
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=repo, capture_output=True, timeout=30,
    )

    subprocess.run(
        ["git", "push"],
        cwd=repo, capture_output=True, timeout=60,
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="监视 Chrome 收藏夹变化，自动同步并推送")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help="轮询间隔（秒）")
    parser.add_argument("--folder", default="劳动政策采集", help="Chrome 收藏夹文件夹名")
    parser.add_argument("--bookmarks", help="Chrome 书签 JSON 文件路径")
    args = parser.parse_args()

    bookmarks_path = Path(args.bookmarks) if args.bookmarks else _find_bookmarks()
    if not bookmarks_path or not bookmarks_path.exists():
        print("❌ 未找到 Chrome 书签文件")
        print(f"   可通过 --bookmarks 指定路径")
        sys.exit(1)

    repo = PROJECT_ROOT
    folder = args.folder
    last_hash = _folder_bookmarks_hash(bookmarks_path, folder)
    print(f"🔍 监视 Chrome 书签文件夹「{folder}」")
    print(f"   书签文件: {bookmarks_path}")
    print(f"   项目目录: {repo}")
    print(f"   轮询间隔: {args.interval}s")
    print(f"   按 Ctrl+C 停止\n")

    while True:
        time.sleep(args.interval)
        current_hash = _folder_bookmarks_hash(bookmarks_path, folder)

        if current_hash and current_hash != last_hash:
            print(f"[{time.strftime('%H:%M:%S')}] 检测到书签变更，等待 {DEBOUNCE_SECS}s 后同步...")
            time.sleep(DEBOUNCE_SECS)

            # 再次检查，避免 Chrome 写入过程中捕获了不完整状态
            current_hash = _folder_bookmarks_hash(bookmarks_path, folder)
            if current_hash == last_hash:
                continue

            print("   运行 sync_bookmarks.py...")
            result = subprocess.run(
                [sys.executable, str(SYNC_SCRIPT),
                 "--mode", "read",
                 "--folder", folder,
                 "--bookmarks", str(bookmarks_path)],
                cwd=repo, capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                print(f"   ❌ 同步失败:\n{result.stderr}")
                continue

            print(f"   {result.stdout.strip().split(chr(10))[-3]}")
            print(f"   {result.stdout.strip().split(chr(10))[-2]}")

            # 检查 git 状态
            if not _git_is_clean(repo):
                print("   ⚠️  工作区有未提交的修改，跳过自动推送")
                last_hash = current_hash
                continue

            if _git_commit_and_push(repo):
                print(f"   ✅ 已提交并推送到远程仓库")
                print(f"   ⏳ GitHub Actions 将自动运行爬虫")
            else:
                print("   配置无变化，跳过提交")

            last_hash = current_hash


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 已停止监视")
