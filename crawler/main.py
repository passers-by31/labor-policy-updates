"""爬虫入口：读取配置、协调爬虫、输出结果。"""

import argparse
import logging
import os
import sys

import yaml

from crawler.spiders.base import Spider
from crawler.spiders.mohrss import MohrssSpider
from crawler.spiders.govcn import GovcnSpider
from crawler.spiders.nhsa import NhsaSpider
from crawler.spiders.national import NationalSpider
from crawler.middleware.rate_limiter import RateLimiter
from crawler.middleware.user_agent import UserAgentPool
from crawler.filters.relevance import RelevanceFilter
from crawler.output.json_writer import merge_and_write

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crawler")


def load_config(path: str) -> dict:
    """加载 YAML 配置文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_spider(
    source_cfg: dict,
    rate_limiter: RateLimiter,
    ua_pool: UserAgentPool,
    timeout: int,
) -> Spider | None:
    """根据配置构建对应的爬虫实例。"""
    source_id = source_cfg["id"]
    spider_map = {
        "mohrss": MohrssSpider,
        "govcn": GovcnSpider,
        "nhsa": NhsaSpider,
    }
    cls = spider_map.get(source_id, NationalSpider)
    return cls(source_cfg, rate_limiter, ua_pool, timeout=timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="劳动政策爬虫")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--output", default="../data", help="输出目录")
    args = parser.parse_args()

    cfg = load_config(args.config)
    general = cfg.get("general", {})
    timeout = general.get("request_timeout", 30)
    ua_list = general.get("user_agents", [])

    rate_limiter = RateLimiter()
    ua_pool = UserAgentPool(ua_list)
    # keywords.yaml 与 config.yaml 在同一目录
    config_dir = os.path.dirname(os.path.abspath(args.config))
    kw_path = os.path.join(config_dir, "keywords.yaml")
    relevance_filter = RelevanceFilter(kw_path)

    stats = {"total_sites": 0, "success_sites": 0, "new_policies": 0}

    all_new_policies = []

    for source_cfg in cfg.get("sources", []):
        if not source_cfg.get("active", False):
            logger.info("跳过非活跃站点: %s", source_cfg.get("id"))
            continue

        stats["total_sites"] += 1
        source_id = source_cfg["id"]
        logger.info("开始爬取: %s (%s)", source_cfg.get("name"), source_id)

        try:
            spider = build_spider(source_cfg, rate_limiter, ua_pool, timeout)
            policies = spider.crawl()
            logger.info("爬取完成: %s, 获取 %d 条原始数据", source_id, len(policies))

            # 相关性过滤
            relevant = []
            for p in policies:
                ok, score = relevance_filter.is_relevant(
                    p.get("title", ""),
                    p.get("content", ""),
                    p.get("tags"),
                )
                if ok:
                    relevant.append(p)

            logger.info("相关性过滤后: %d 条", len(relevant))
            all_new_policies.extend(relevant)
            stats["success_sites"] += 1
            stats["new_policies"] += len(relevant)

        except Exception as e:
            logger.error("爬取失败 %s: %s", source_id, e, exc_info=True)

    # 输出
    if all_new_policies:
        changelog = merge_and_write(all_new_policies, args.output)
        logger.info("写入完成: 新增 %d 条, 总计 %d 条",
                     changelog["newCount"], changelog["totalCount"])
    else:
        logger.info("无新政策数据")

    # 打印摘要（供 CI 捕获）
    print(f"::notice::爬取完成: "
          f"成功={stats['success_sites']}/{stats['total_sites']}, "
          f"新增={stats['new_policies']}")


if __name__ == "__main__":
    main()
