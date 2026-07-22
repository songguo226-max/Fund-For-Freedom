from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
NEWS_DATA_DIR = PROJECT_ROOT / "data" / "news"


@dataclass(frozen=True)
class SeedHolding:
    name: str
    code: str | None = None
    lookup_query: str | None = None
    tags: tuple[str, ...] = ()
    source: str = "manual"


@dataclass(frozen=True)
class NewsSettings:
    data_dir: Path = NEWS_DATA_DIR
    sqlite_path: Path = NEWS_DATA_DIR / "news.sqlite"
    raw_dir: Path = NEWS_DATA_DIR / "raw"
    refresh_cache_minutes: int = 10
    daily_summary_hour: int = 8
    weekly_report_day: str = "sunday"
    timezone: str = "Asia/Shanghai"
    default_action: str = "不操作"
    seed_holdings: tuple[SeedHolding, ...] = field(
        default_factory=lambda: (
            SeedHolding(
                code="100055",
                name="富国全球科技互联网股票(QDII)A",
                lookup_query="100055",
                tags=("fund", "qdii", "technology", "internet"),
            ),
            SeedHolding(
                name="易方达沪深300指数精选增强A",
                lookup_query="易方达沪深300指数精选增强A",
                tags=("fund", "csi300", "index-enhanced"),
            ),
            SeedHolding(
                name="天弘中证500指数增强A",
                lookup_query="天弘中证500指数增强A",
                tags=("fund", "csi500", "index-enhanced"),
            ),
            SeedHolding(
                name="华夏有色金属ETF联接A",
                lookup_query="华夏有色金属ETF联接A",
                tags=("fund", "materials", "metals"),
            ),
            SeedHolding(
                name="国泰黄金ETF联接A",
                lookup_query="国泰黄金ETF联接A",
                tags=("fund", "gold"),
            ),
            SeedHolding(
                name="长城全球新能源汽车股票(QDII-LOF)A",
                lookup_query="长城全球新能源汽车股票(QDII-LOF)A",
                tags=("fund", "qdii", "new-energy-vehicle"),
            ),
            SeedHolding(
                name="景顺长城国证机器人产业ETF联接A",
                lookup_query="景顺长城国证机器人产业ETF联接A",
                tags=("fund", "robotics"),
            ),
            SeedHolding(
                name="建信新兴市场优选混合(QDII)A",
                lookup_query="建信新兴市场优选混合(QDII)A",
                tags=("fund", "qdii", "emerging-markets"),
            ),
            SeedHolding(
                name="广发纳斯达克100ETF联接(QDII)A",
                lookup_query="广发纳斯达克100ETF联接(QDII)A",
                tags=("fund", "qdii", "nasdaq100"),
            ),
            SeedHolding(
                name="国泰CES半导体芯片行业ETF联接A",
                lookup_query="国泰CES半导体芯片行业ETF联接A",
                tags=("fund", "semiconductor"),
            ),
            SeedHolding(
                name="银华互联网主题灵活配置混合C",
                lookup_query="银华互联网主题灵活配置混合C",
                tags=("fund", "internet"),
            ),
        )
    )


news_settings = NewsSettings()
