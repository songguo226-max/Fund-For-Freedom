from __future__ import annotations

import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config.news_settings import news_settings
from app.infrastructure.news_store import NewsStore
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.integrations.news_data.interface import NewsDataError, RawNewsArticle
from app.integrations.news_data.registry import NewsProviderRegistry
from app.modules.news.classifier import NewsRelation, classify_news
from app.modules.news.dedupe import canonical_title, event_key
from app.modules.news.report_rules import (
    HOTLIST_WEEKLY_RANK_LIMIT,
    RANKED_HOTLIST_SOURCE_IDS,
    WEEKLY_SNAPSHOT_SOURCE_IDS,
    hotlist_rank,
)
from app.modules.news.scorer import score_news


DAILY_SOURCE_ITEM_LIMIT = 7
FETCH_CACHE_VERSION = 5
ACCEPTED_FETCH_CACHE_VERSIONS = {3, 4, 5}
ARTICLE_META_REQUIRED_SOURCE_IDS = {"cls", "eastmoney", "xueqiu"}
STALE_HEALTHY_CACHE_SOURCE_IDS = {"xueqiu"}
LOGGER = logging.getLogger(__name__)
NEWS_REFRESH_LOG_PATH = news_settings.data_dir / "news_refresh.log"
_LOG_HANDLER_MARKER = "_fund_news_refresh_file_handler"


def _ensure_refresh_file_logging() -> None:
    for handler in LOGGER.handlers:
        if getattr(handler, _LOG_HANDLER_MARKER, False):
            return
    news_settings.data_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(NEWS_REFRESH_LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    setattr(handler, _LOG_HANDLER_MARKER, True)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


_ensure_refresh_file_logging()


class NewsAggregationService:
    def __init__(
        self,
        *,
        store: NewsStore,
        registry: NewsProviderRegistry,
        rate_limiter: InMemoryRateLimiter,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._rate_limiter = rate_limiter
        self._now = now or (lambda: datetime.now(timezone.utc))

    def refresh(
        self,
        *,
        limit_per_source: int = 30,
        force: bool = False,
        allow_stale_cache: bool = False,
    ) -> dict[str, Any]:
        refresh_started = time.perf_counter()
        LOGGER.info("news.refresh start force=%s limit_per_source=%s", force, limit_per_source)
        self._initialize()
        self._repair_incomplete_article_meta_items()
        source_results: list[dict[str, Any]] = []
        for spec in self._registry.specs():
            source_started = time.perf_counter()
            provider = self._provider_or_none(spec.id)
            if provider is None:
                source_results.append(
                    {
                        "sourceId": spec.id,
                        "sourceName": spec.name,
                        "status": "skipped",
                        "reason": _skip_reason(spec.id),
                        "fetched": 0,
                    }
                )
                LOGGER.info("news.refresh source=%s status=skipped elapsed_ms=%d", spec.id, _elapsed_ms(source_started))
                continue

            cached = self._cached_result(spec.id, spec.cache_minutes, allow_stale=allow_stale_cache)
            if cached is not None and not force:
                source_results.append({**cached, "status": "cached"})
                LOGGER.info(
                    "news.refresh source=%s status=cached fetched=%s elapsed_ms=%d",
                    spec.id,
                    cached.get("fetched"),
                    _elapsed_ms(source_started),
                )
                continue

            if not self._rate_limiter.acquire(spec.id, limit_per_minute=spec.rate_limit_per_minute):
                source_results.append(
                    {
                        "sourceId": spec.id,
                        "sourceName": spec.name,
                        "status": "rate_limited",
                        "reason": f"超过每分钟 {spec.rate_limit_per_minute} 次限制",
                        "fetched": 0,
                    }
                )
                LOGGER.info("news.refresh source=%s status=rate_limited elapsed_ms=%d", spec.id, _elapsed_ms(source_started))
                continue

            try:
                articles = provider.fetch_latest(limit=_provider_limit(spec.id, limit_per_source))
                saved = [self._save_article(article) for article in articles]
                removed_stale = (
                    self._store.delete_incomplete_article_meta_items(spec.id)
                    if spec.id in ARTICLE_META_REQUIRED_SOURCE_IDS and saved
                    else 0
                )
                status = "ok" if saved else "empty"
                result = {
                    "cacheVersion": FETCH_CACHE_VERSION,
                    "sourceId": spec.id,
                    "sourceName": spec.name,
                    "status": status,
                    "reason": "" if saved else "公开页面未解析到新闻条目，可能由前端脚本动态渲染",
                    "fetched": _source_status_count(spec.id, len(saved)),
                    "articleIds": saved,
                    "fetchedAt": self._now().isoformat(),
                }
                if removed_stale:
                    result["repaired"] = {"removedIncompleteItems": removed_stale}
                self._store.set_fetch_cache(spec.id, fetched_at=result["fetchedAt"], payload=result)
                source_results.append(result)
                LOGGER.info(
                    "news.refresh source=%s status=%s fetched=%s saved=%s elapsed_ms=%d",
                    spec.id,
                    status,
                    result["fetched"],
                    len(saved),
                    _elapsed_ms(source_started),
                )
            except NewsDataError as exc:
                source_results.append(
                    {
                        "sourceId": spec.id,
                        "sourceName": spec.name,
                        "status": "error",
                        "reason": str(exc),
                        "fetched": 0,
                    }
                )
                LOGGER.warning("news.refresh source=%s status=error elapsed_ms=%d reason=%s", spec.id, _elapsed_ms(source_started), exc)

        items = self._refresh_items()
        LOGGER.info("news.refresh done sources=%d items=%d elapsed_ms=%d", len(source_results), len(items), _elapsed_ms(refresh_started))
        return {
            "refreshedAt": self._now().isoformat(),
            "sources": source_results,
            "items": items,
        }

    def _initialize(self) -> None:
        self._store.seed_holdings()
        for spec in self._registry.specs():
            self._store.upsert_news_source(spec)
        self._store.disable_news_sources_except({spec.id for spec in self._registry.specs()})

    def _provider_or_none(self, source_id: str):
        try:
            return self._registry.get(source_id)
        except KeyError:
            return None

    def _cached_result(self, source_id: str, cache_minutes: int, *, allow_stale: bool = False) -> dict[str, Any] | None:
        row = self._store.get_fetch_cache(source_id)
        if not row:
            return None
        try:
            fetched_at = datetime.fromisoformat(row["fetched_at"])
        except ValueError:
            return None
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        payload = json.loads(row["payload_json"])
        if payload.get("cacheVersion") not in ACCEPTED_FETCH_CACHE_VERSIONS:
            return None
        article_ids = payload.get("articleIds")
        if not _cache_articles_are_healthy(source_id, article_ids, self._store):
            return None
        cache_age = datetime.now(timezone.utc) - fetched_at
        if cache_age > timedelta(minutes=cache_minutes):
            if not allow_stale and source_id not in STALE_HEALTHY_CACHE_SOURCE_IDS:
                return None
            payload["reason"] = "使用健康旧缓存，避免慢速来源阻塞页面加载"
        raw_count = len(article_ids) if isinstance(article_ids, list) else int(payload.get("fetched") or 0)
        payload["fetched"] = _source_status_count(source_id, raw_count)
        return payload

    def _save_article(self, article: RawNewsArticle) -> str:
        raw_id, _ = self._store.save_raw_payload(
            source_id=article.source_id,
            url=article.url,
            title=article.title,
            payload=article.raw_payload,
        )
        item_id = self._store.save_news_item(
            source_id=article.source_id,
            title=article.title,
            summary=article.summary,
            url=article.url,
            published_at=article.published_at.isoformat() if article.published_at else None,
            author=article.author,
            raw_news_id=raw_id,
        )
        self._process_article(item_id=item_id, article=article)
        self._save_rank_snapshot_if_needed(item_id=item_id, raw_news_id=raw_id, article=article)
        return item_id

    def _process_article(self, *, item_id: str, article: RawNewsArticle) -> None:
        self._process_item(
            item_id=item_id,
            source_id=article.source_id,
            title=article.title,
            summary=article.summary,
        )

    def _process_item(self, *, item_id: str, source_id: str, title: str, summary: str) -> None:
        source = self._source_spec(source_id)
        item = {
            "id": item_id,
            "title": title,
            "summary": summary,
            "source_id": source_id,
        }
        holdings = self._store.list_holdings()
        relations = classify_news(item, holdings)
        score = score_news(
            title=title,
            summary=summary,
            source_reliability_score=source.reliability_score if source else 0,
            relations=relations,
        )
        key = event_key(title, summary)
        event_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self._store.upsert_news_event(
            event_id=event_id,
            canonical_title=canonical_title(title),
            event_key=key,
            best_source_id=source_id,
            importance_score=score.total_score,
        )
        self._store.link_event_article(event_id=event_id, news_item_id=item_id)
        self._store.save_news_score(
            news_item_id=item_id,
            relevance_score=score.relevance_score,
            duration_score=score.duration_score,
            surprise_score=score.surprise_score,
            reliability_score=score.reliability_score,
            total_score=score.total_score,
        )
        self._store.replace_news_relations(item_id, [_relation_dict(relation) for relation in relations])

    def _recent_items_with_scores(self) -> list[dict[str, Any]]:
        items = self._store.list_recent_news_items(limit=100)
        missing = [item for item in items if item.get("total_score") is None]
        for item in missing:
            self._process_item(
                item_id=item["id"],
                source_id=item["source_id"],
                title=item["title"],
                summary=item.get("summary") or "",
            )
        if missing:
            items = self._store.list_recent_news_items(limit=100)
        return items

    def _refresh_items(self) -> list[dict[str, Any]]:
        items = _drop_incomplete_article_meta_items(self._recent_items_with_scores())
        self._backfill_rank_snapshots_from_items(items)
        self._backfill_rank_snapshots_from_cache()
        today = self._local_now().date()
        start = today - timedelta(days=6)
        items = _dedupe_items_by_id(items + _drop_incomplete_article_meta_items(self._cached_hotlist_items()))
        return items + self._weekly_rank_snapshots(start=start, end=today)

    def _repair_incomplete_article_meta_items(self) -> int:
        removed = 0
        source_ids = {spec.id for spec in self._registry.specs()}
        for source_id in sorted(ARTICLE_META_REQUIRED_SOURCE_IDS & source_ids):
            removed += self._store.delete_incomplete_article_meta_items(source_id)
        return removed

    def _cached_hotlist_items(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for source_id in RANKED_HOTLIST_SOURCE_IDS:
            row = self._store.get_fetch_cache(source_id)
            if not row:
                continue
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            article_ids = payload.get("articleIds")
            if not _cache_articles_are_healthy(source_id, article_ids, self._store):
                continue
            result.extend(self._store.list_news_items_by_ids([str(item_id) for item_id in article_ids]))
        return result

    def _weekly_rank_snapshots(self, *, start: date, end: date) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for source_id in sorted(WEEKLY_SNAPSHOT_SOURCE_IDS):
            items.extend(
                self._store.list_rank_snapshots(
                    source_id=source_id,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    rank_limit=HOTLIST_WEEKLY_RANK_LIMIT,
                )
            )
        return _dedupe_rank_snapshots_by_article(items)

    def _save_rank_snapshot_if_needed(self, *, item_id: str, raw_news_id: str, article: RawNewsArticle) -> None:
        if article.source_id not in WEEKLY_SNAPSHOT_SOURCE_IDS:
            return
        rank = _article_hotlist_rank(article)
        if rank is None or rank > DAILY_SOURCE_ITEM_LIMIT:
            return
        local_now = self._local_now()
        self._store.save_rank_snapshot(
            source_id=article.source_id,
            snapshot_date=local_now.date().isoformat(),
            snapshot_at=local_now.isoformat(),
            rank=rank,
            news_item_id=item_id,
            title=article.title,
            summary=article.summary,
            url=article.url,
            published_at=article.published_at.isoformat() if article.published_at else None,
            author=article.author,
            raw_news_id=raw_news_id,
        )

    def _backfill_rank_snapshots_from_items(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            if item.get("source_id") not in WEEKLY_SNAPSHOT_SOURCE_IDS:
                continue
            rank = hotlist_rank(item)
            if rank is None or rank > DAILY_SOURCE_ITEM_LIMIT:
                continue
            snapshot_at = self._local_now()
            if snapshot_at.tzinfo is None:
                snapshot_at = snapshot_at.replace(tzinfo=timezone.utc)
            snapshot_at = snapshot_at.astimezone(_news_timezone())
            self._store.save_rank_snapshot(
                source_id=item["source_id"],
                snapshot_date=snapshot_at.date().isoformat(),
                snapshot_at=snapshot_at.isoformat(),
                rank=rank,
                news_item_id=item["id"],
                title=item["title"],
                summary=item.get("summary") or "",
                url=item["url"],
                published_at=item.get("published_at"),
                author=item.get("author"),
                raw_news_id=item.get("raw_news_id"),
            )

    def _backfill_rank_snapshots_from_cache(self) -> None:
        for source_id in sorted(WEEKLY_SNAPSHOT_SOURCE_IDS):
            row = self._store.get_fetch_cache(source_id)
            if not row:
                continue
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                continue
            article_ids = payload.get("articleIds")
            if not _cache_articles_are_healthy(source_id, article_ids, self._store):
                continue
            for rank, item in enumerate(self._store.list_news_items_by_ids([str(item_id) for item_id in article_ids]), start=1):
                rank = hotlist_rank(item) or rank
                if rank > DAILY_SOURCE_ITEM_LIMIT:
                    break
                self._save_rank_snapshot_from_item(item, rank=rank, fetched_at=row["fetched_at"])

    def _save_rank_snapshot_from_item(self, item: dict[str, Any], *, rank: int, fetched_at: str | None = None) -> None:
        snapshot_at = _parse_datetime(fetched_at) or self._local_now()
        if snapshot_at.tzinfo is None:
            snapshot_at = snapshot_at.replace(tzinfo=timezone.utc)
        snapshot_at = snapshot_at.astimezone(_news_timezone())
        self._store.save_rank_snapshot(
            source_id=item["source_id"],
            snapshot_date=snapshot_at.date().isoformat(),
            snapshot_at=snapshot_at.isoformat(),
            rank=rank,
            news_item_id=item["id"],
            title=item["title"],
            summary=item.get("summary") or "",
            url=item["url"],
            published_at=item.get("published_at"),
            author=item.get("author"),
            raw_news_id=item.get("raw_news_id"),
        )

    def _local_now(self) -> datetime:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(_news_timezone())

    def _source_spec(self, source_id: str):
        for spec in self._registry.specs():
            if spec.id == source_id:
                return spec
        return None


def _relation_dict(relation: NewsRelation) -> dict[str, Any]:
    return {
        "fund_code": relation.fund_code,
        "fund_name": relation.fund_name,
        "relation_type": relation.relation_type,
        "matched_keywords": list(relation.matched_keywords),
        "impact_variables": list(relation.impact_variables),
    }


def _article_hotlist_rank(article: RawNewsArticle) -> int | None:
    raw_rank = article.raw_payload.get("rank") if isinstance(article.raw_payload, dict) else None
    if isinstance(raw_rank, int):
        return raw_rank
    if isinstance(raw_rank, str) and raw_rank.isdigit():
        return int(raw_rank)
    return hotlist_rank({"source_id": article.source_id, "title": article.title, "summary": article.summary})


def _skip_reason(source_id: str) -> str:
    if source_id == "xueqiu":
        return "雪球条款限制直接抓取；需确认授权方式或可接受的第三方公开热榜接口"
    return "尚未确认无需登录、无需Cookie且稳定的公开采集接口"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _dedupe_rank_snapshots_by_article(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("news_item_id") or item.get("url") or item.get("title") or item.get("id"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_items_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("id") or item.get("news_item_id") or item.get("url") or item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _drop_incomplete_article_meta_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if item.get("source_id") not in ARTICLE_META_REQUIRED_SOURCE_IDS or (item.get("published_at") and item.get("author"))
    ]


def _source_status_count(source_id: str, saved_count: int) -> int:
    if source_id in RANKED_HOTLIST_SOURCE_IDS:
        return min(saved_count, DAILY_SOURCE_ITEM_LIMIT)
    return saved_count


def _provider_limit(source_id: str, requested_limit: int) -> int:
    if source_id in RANKED_HOTLIST_SOURCE_IDS:
        return min(requested_limit, DAILY_SOURCE_ITEM_LIMIT)
    return requested_limit


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _cache_articles_are_healthy(source_id: str, article_ids: Any, store: NewsStore) -> bool:
    if not isinstance(article_ids, list) or not article_ids:
        return False
    if source_id not in ARTICLE_META_REQUIRED_SOURCE_IDS:
        return True

    rows = store.list_news_items_by_ids([str(item_id) for item_id in article_ids])
    if len(rows) != len(article_ids):
        return False
    for row in rows:
        if not row.get("published_at") or not row.get("author"):
            return False
    return True

def _news_timezone() -> timezone | ZoneInfo:
    try:
        return ZoneInfo(news_settings.timezone)
    except ZoneInfoNotFoundError:
        if news_settings.timezone == "Asia/Shanghai":
            return timezone(timedelta(hours=8), name="Asia/Shanghai")
        return timezone.utc
