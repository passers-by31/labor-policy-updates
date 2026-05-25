#!/usr/bin/env python3
"""Chrome 收藏夹 ↔ 爬虫配置 双向同步工具。

用法：
  # 从 config.yaml 导出书签 HTML（首次导入用）
  python crawler/sync_bookmarks.py --mode export

  # 从 Chrome 收藏夹读取并更新爬虫配置
  python crawler/sync_bookmarks.py --mode read

  # 指定收藏夹文件夹名
  python crawler/sync_bookmarks.py --mode read --folder "劳动政策采集"

  # 指定 Chrome 书签文件路径（不自动检测）
  python crawler/sync_bookmarks.py --mode read --bookmarks /path/to/Bookmarks
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_DIR = PROJECT_ROOT / "crawler"
DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_CONFIG_PATH = CRAWLER_DIR / "config.yaml"
DEFAULT_BOOKMARKS_YAML = CRAWLER_DIR / "bookmark_defaults.yaml"
DEFAULT_OUTPUT_YAML = CRAWLER_DIR / "config.yaml"
DEFAULT_OUTPUT_JSON = DATA_DIR / "sources.json"
DEFAULT_OUTPUT_HTML = DATA_DIR / "bookmarks.html"
DEFAULT_FOLDER = "劳动政策采集"

# Chrome 书签 JSON 的可能路径（按平台）
CHROME_PATHS = [
    # macOS
    Path.home() / "Library/Application Support/Google/Chrome/Default/Bookmarks",
    Path.home() / "Library/Application Support/Google/Chrome/Default/AccountBookmarks",
    # macOS 多 Profile
    *sorted(
        Path.home().glob("Library/Application Support/Google/Chrome/Profile */Bookmarks")
    ),
    *sorted(
        Path.home().glob("Library/Application Support/Google/Chrome/Profile */AccountBookmarks")
    ),
    # Linux
    Path.home() / ".config/google-chrome/Default/Bookmarks",
    Path.home() / ".config/chromium/Default/Bookmarks",
    # Windows
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Google/Chrome/User Data/Default/Bookmarks",
]

# ================================================================
#  工具函数
# ================================================================

def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_yaml(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _timestamp() -> int:
    return int(time.time())


def _domain_from_url(url: str) -> str:
    return urlparse(url).hostname or ""


def _slug_from_url(url: str) -> str:
    """从 URL 生成唯一 ID，如 www.mohrss.gov.cn → mohrss-gov-cn"""
    domain = _domain_from_url(url)
    parts = domain.split(".")
    # 去掉 www 和常见 TLD
    parts = [p for p in parts if p not in ("www", "com", "cn", "gov", "org", "net")]
    if not parts:
        parts = [_domain_from_url(url).replace(".", "-")]
    return "-".join(parts)


def _safe_name(name: str) -> str:
    """清理收藏夹名称中的非法文件字符"""
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()


# ================================================================
#  导出：config.yaml → Chrome 书签 HTML
# ================================================================

def export_bookmarks(config_path: Path, output: Path, folder_name: str) -> None:
    """将 config.yaml 中的 sources 导出为 Chrome 可导入的 HTML 书签文件。"""
    cfg = _load_yaml(config_path)
    sources = cfg.get("sources", [])
    if not sources:
        print("⚠️  config.yaml 中未找到 sources 配置")
        sys.exit(1)

    now_ts = _timestamp()
    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<!-- This is an automatically generated file. -->',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>书签</H1>",
        "<DL><p>",
        f'    <DT><H3>{_safe_name(folder_name)}</H3>',
        "    <DL><p>",
    ]

    for src in sources:
        url = src.get("base_url", src.get("url", ""))
        if not url:
            continue
        name = _safe_name(src.get("name", url))
        lines.append(f'        <DT><A HREF="{url}" ADD_DATE="{now_ts}">{name}</A>')

    lines.extend(["    </DL><p>", "</DL><p>"])

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    active = [s for s in sources if s.get("active", True)]
    print(f"✅ 已导出 {len(sources)} 个来源到书签文件（其中 {len(active)} 个活跃）")
    print(f"   文件: {output}")
    print(f"   Chrome 操作: 书签管理器 → 导入书签 → 选择此文件")


# ================================================================
#  读取：Chrome 书签 JSON → config.yaml + sources.json
# ================================================================

def _find_bookmarks_file() -> Path | None:
    """自动检测 Chrome 书签 JSON 文件路径。"""
    for p in CHROME_PATHS:
        if p and p.exists():
            return p
    return None


def _parse_bookmarks_json(path: Path) -> dict:
    """解析 Chrome 书签 JSON 文件，返回 {folder_name: [bookmark]}。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    folders: dict[str, list[dict]] = {}

    def walk(node: dict, parent_name: str = "") -> None:
        node_type = node.get("type", "")
        name = node.get("name", "")

        if node_type == "folder":
            children = node.get("children", [])
            folder_key = name if name else parent_name
            if folder_key not in folders:
                folders[folder_key] = []
            for child in children:
                walk(child, folder_key)
        elif node_type == "url":
            url = node.get("url", "")
            if url and not url.startswith("chrome://") and not url.startswith("javascript:"):
                folders.setdefault(parent_name, []).append({
                    "name": node.get("name", ""),
                    "url": url,
                })

    for root_key in ("bookmark_bar", "other", "synced"):
        root = data.get("roots", {}).get(root_key)
        if root:
            for child in root.get("children", []):
                walk(child)

    return folders


def _load_defaults(path: Path) -> dict:
    """加载 bookmark_defaults.yaml。"""
    if path.exists():
        return _load_yaml(path)
    return {"defaults": {}, "overrides": {}}


def _build_source_from_bookmark(
    bookmark: dict,
    defaults_cfg: dict,
    overrides: dict,
    domain_id_map: dict,
) -> dict:
    """将单个书签 + 默认配置合并为爬虫 source 配置项。"""
    url = bookmark["url"].rstrip("/")
    name = bookmark["name"] or url
    domain = _domain_from_url(url)
    src_id = domain_id_map.get(domain, _slug_from_url(url))

    # 基础字段
    base: dict = {
        "id": src_id,
        "name": name,
        "base_url": url,
        "encoding": defaults_cfg.get("encoding", "utf-8"),
        "region": defaults_cfg.get("region", "全国"),
        "active": True,
        "crawl_interval_hours": defaults_cfg.get("crawl_interval_hours", 48),
    }

    # 应用域名覆盖规则
    override = overrides.get(domain, {})
    if override:
        base.update(override)

    # list_pages：若有覆盖则用覆盖，否则从默认生成
    if "list_pages" not in base:
        list_sel = defaults_cfg.get("list_selector", "ul.list-list li a, ul.list li a")
        max_pgs = defaults_cfg.get("max_pages", 1)
        base["list_pages"] = [
            {
                "url": url,
                "name": name,
                "list_selector": list_sel,
                "max_pages": max_pgs,
            }
        ]

    # detail_rules：若有覆盖则用覆盖，否则用默认
    if "detail_rules" not in base:
        base["detail_rules"] = defaults_cfg.get("detail_rules", {
            "title_selector": "div.content-title h1, div.article-title h1, h1",
            "content_selector": "div.TRS_Editor, div.content-body, div.article-content",
        })

    return base


def read_bookmarks(
    bookmarks_path: Path | None,
    defaults_path: Path,
    folder_name: str,
    output_yaml: Path,
    output_json: Path,
    config_path: Path,
) -> None:
    """读取 Chrome 书签并生成爬虫配置。"""
    # 1. 查找书签文件
    if bookmarks_path:
        bm_file = bookmarks_path
    else:
        bm_file = _find_bookmarks_file()

    if not bm_file or not bm_file.exists():
        print("❌ 未找到 Chrome 书签文件")
        print("   请通过 --bookmarks 参数指定路径，或确保 Chrome 已安装且有书签数据")
        print(f"   检测的路径:\n" + "\n".join(f"     - {p}" for p in CHROME_PATHS if p))
        sys.exit(1)

    print(f"📖 读取书签文件: {bm_file}")

    # 2. 解析书签
    folders = _parse_bookmarks_json(bm_file)

    if folder_name not in folders:
        available = list(folders.keys())
        print(f"❌ 未找到文件夹「{folder_name}」")
        print(f"   可用文件夹: {', '.join(available) if available else '无'}")
        sys.exit(1)

    bookmarks = folders[folder_name]
    if not bookmarks:
        print(f"⚠️  文件夹「{folder_name}」为空")
        sys.exit(1)

    print(f"📌 在「{folder_name}」中找到 {len(bookmarks)} 个书签")

    # 3. 加载默认配置
    defaults_cfg = _load_defaults(defaults_path)
    defaults = defaults_cfg.get("defaults", {})
    overrides = defaults_cfg.get("overrides", {})
    domain_id_map = defaults_cfg.get("domain_id_map", {})

    # 4. 生成 sources
    sources = []
    seen_ids: dict[str, int] = {}
    for bm in bookmarks:
        src = _build_source_from_bookmark(bm, defaults, overrides, domain_id_map)
        # 去重 ID
        src_id = src["id"]
        if src_id in seen_ids:
            seen_ids[src_id] += 1
            src["id"] = f"{src_id}-{seen_ids[src_id]}"
        else:
            seen_ids[src_id] = 0
        sources.append(src)

    # 5. 写入 config.yaml（保留 general 和 province_defaults）
    existing_cfg = _load_yaml(config_path) if config_path.exists() else {}
    new_cfg = {
        "general": existing_cfg.get("general", {
            "output_dir": "../data",
            "request_timeout": 30,
            "max_retries": 3,
            "batch_size": 50,
        }),
        "sources": sources,
        "province_defaults": existing_cfg.get("province_defaults", {}),
    }

    # 保留 user_agents 和部分 general 字段
    if not new_cfg["general"].get("user_agents"):
        new_cfg["general"]["user_agents"] = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        ]

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_yaml, "w", encoding="utf-8") as f:
        yaml.dump(new_cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    # 6. 生成 sources.json（前端用）
    json_sources = []
    for src in sources:
        json_sources.append({
            "id": src["id"],
            "name": src["name"],
            "url": src["base_url"],
            "region": src.get("region", "全国"),
            "level": "national",
        })

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(json_sources, f, ensure_ascii=False, indent=2)
        f.write("\n")

    active_count = sum(1 for s in sources if s.get("active", True))
    print(f"✅ 配置已生成")
    print(f"   爬虫配置: {output_yaml}（{len(sources)} 个来源，{active_count} 个活跃）")
    print(f"   前端数据: {output_json}")


# ================================================================
#  入口
# ================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Chrome 收藏夹 ↔ 爬虫配置同步工具")
    parser.add_argument(
        "--mode",
        choices=["export", "read"],
        default="export",
        help="export: config.yaml → Chrome 书签 HTML | read: 书签 → config.yaml",
    )
    parser.add_argument("--folder", default=DEFAULT_FOLDER, help="Chrome 收藏夹文件夹名")
    parser.add_argument(
        "--bookmarks",
        help="Chrome 书签 JSON 文件路径（read 模式用，默认自动检测）",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="爬虫 config.yaml 路径")
    parser.add_argument(
        "--output-yaml", default=str(DEFAULT_OUTPUT_YAML), help="输出的 config.yaml 路径"
    )
    parser.add_argument(
        "--output-json", default=str(DEFAULT_OUTPUT_JSON), help="输出的 sources.json 路径"
    )
    parser.add_argument(
        "--output-html", default=str(DEFAULT_OUTPUT_HTML), help="导出的书签 HTML 路径"
    )

    args = parser.parse_args()
    config_path = Path(args.config)

    if args.mode == "export":
        if not config_path.exists():
            print(f"❌ 配置文件不存在: {config_path}")
            sys.exit(1)
        export_bookmarks(
            config_path=config_path,
            output=Path(args.output_html),
            folder_name=args.folder,
        )
    else:
        bookmarks_path = Path(args.bookmarks) if args.bookmarks else None
        read_bookmarks(
            bookmarks_path=bookmarks_path,
            defaults_path=Path(DEFAULT_BOOKMARKS_YAML),
            folder_name=args.folder,
            output_yaml=Path(args.output_yaml),
            output_json=Path(args.output_json),
            config_path=config_path,
        )


if __name__ == "__main__":
    main()
