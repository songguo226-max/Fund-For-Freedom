from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.news_settings import SeedHolding, news_settings
from app.integrations.news_data.interface import NewsSourceSpec


SCHEMA_VERSION = 2


class NewsStore:
    def __init__(self, sqlite_path: Path | None = None, raw_dir: Path | None = None) -> None:
        self.sqlite_path = sqlite_path or news_settings.sqlite_path
        self.raw_dir = raw_dir or news_settings.raw_dir

    def initialize(self) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute("DELETE FROM schema_meta WHERE version <> ?", (SCHEMA_VERSION,))
            conn.execute("INSERT OR IGNORE INTO schema_meta (version) VALUES (?)", (SCHEMA_VERSION,))

    def seed_holdings(self, holdings: tuple[SeedHolding, ...] = news_settings.seed_holdings) -> None:
        self.initialize()
        for holding in holdings:
            self.upsert_holding(
                code=holding.code,
                name=holding.name,
                lookup_query=holding.lookup_query,
                tags=list(holding.tags),
                source=holding.source,
            )

    def upsert_news_source(self, spec: NewsSourceSpec) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_sources (
                    id, name, tier, reliability_score, adapter, enabled, cache_minutes,
                    rate_limit_per_minute, requires_login, homepage, terms_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    tier = excluded.tier,
                    reliability_score = excluded.reliability_score,
                    adapter = excluded.adapter,
                    enabled = excluded.enabled,
                    cache_minutes = excluded.cache_minutes,
                    rate_limit_per_minute = excluded.rate_limit_per_minute,
                    requires_login = excluded.requires_login,
                    homepage = excluded.homepage,
                    terms_note = excluded.terms_note
                """,
                (
                    spec.id,
                    spec.name,
                    spec.tier.value,
                    spec.reliability_score,
                    spec.adapter,
                    int(spec.enabled),
                    spec.cache_minutes,
                    spec.rate_limit_per_minute,
                    int(spec.requires_login),
                    spec.homepage,
                    spec.terms_note,
                ),
            )

    def list_news_sources(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM news_sources WHERE enabled = 1 ORDER BY tier, name").fetchall()
        return [dict(row) for row in rows]

    def disable_news_sources_except(self, source_ids: set[str]) -> None:
        self.initialize()
        with self._connect() as conn:
            if not source_ids:
                conn.execute("UPDATE news_sources SET enabled = 0")
                return
            placeholders = ",".join("?" for _ in source_ids)
            conn.execute(
                f"UPDATE news_sources SET enabled = 0 WHERE id NOT IN ({placeholders})",
                tuple(source_ids),
            )

    def upsert_holding(
        self,
        *,
        code: str | None,
        name: str,
        lookup_query: str | None = None,
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        source: str = "manual",
    ) -> int:
        self.initialize()
        now = _now()
        normalized_code = code.strip() if code else None
        identity = normalized_code or name
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM holdings WHERE COALESCE(code, name) = ? OR name = ?",
                (identity, name),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE holdings
                    SET code = ?, name = ?, lookup_query = ?, aliases_json = ?, tags_json = ?,
                        source = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        normalized_code,
                        name,
                        lookup_query,
                        json.dumps(aliases or [], ensure_ascii=False),
                        json.dumps(tags or [], ensure_ascii=False),
                        source,
                        now,
                        existing["id"],
                    ),
                )
                return int(existing["id"])
            cursor = conn.execute(
                """
                INSERT INTO holdings (
                    code, name, lookup_query, aliases_json, tags_json, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_code,
                    name,
                    lookup_query,
                    json.dumps(aliases or [], ensure_ascii=False),
                    json.dumps(tags or [], ensure_ascii=False),
                    source,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_holdings(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM holdings ORDER BY id").fetchall()
        return [_decode_json_columns(dict(row), "aliases_json", "tags_json") for row in rows]

    def replace_watchlist(self, items: list[dict[str, Any]], *, origin: str = "favorite") -> None:
        self.initialize()
        now = _now()
        with self._connect() as conn:
            conn.execute("DELETE FROM watchlist_items WHERE origin = ?", (origin,))
            for position, item in enumerate(items):
                code = str(item.get("code") or "").strip()
                name = str(item.get("name") or code).strip()
                if not code and not name:
                    continue
                conn.execute(
                    """
                    INSERT INTO watchlist_items (code, name, type, origin, position, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code or None,
                        name,
                        str(item.get("type") or ""),
                        origin,
                        position,
                        now,
                    ),
                )

    def list_watchlist(self, origin: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        sql = "SELECT * FROM watchlist_items"
        params: tuple[str, ...] = ()
        if origin:
            sql += " WHERE origin = ?"
            params = (origin,)
        sql += " ORDER BY origin, position, name"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_fetch_cache(self, source_id: str) -> dict[str, Any] | None:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM fetch_cache WHERE source_id = ?", (source_id,)).fetchone()
        return dict(row) if row else None

    def list_news_items_by_ids(self, item_ids: list[str]) -> list[dict[str, Any]]:
        self.initialize()
        if not item_ids:
            return []
        placeholders = ",".join("?" for _ in item_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT news_items.*, news_sources.name AS source_name, news_sources.tier AS source_tier
                , news_scores.relevance_score, news_scores.duration_score, news_scores.surprise_score
                , news_scores.reliability_score, news_scores.total_score
                FROM news_items
                JOIN news_sources ON news_sources.id = news_items.source_id
                LEFT JOIN news_scores ON news_scores.news_item_id = news_items.id
                WHERE news_items.id IN ({placeholders})
                """,
                item_ids,
            ).fetchall()
            relations_by_item = self._relations_by_item(conn, item_ids)
        rows_by_id = {row["id"]: dict(row) for row in rows}
        result = []
        for item_id in item_ids:
            item = rows_by_id.get(item_id)
            if not item:
                continue
            item["relations"] = relations_by_item.get(item["id"], [])
            result.append(item)
        return result

    def delete_incomplete_article_meta_items(self, source_id: str) -> int:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, url FROM news_items
                WHERE source_id = ?
                  AND (published_at IS NULL OR published_at = '' OR author IS NULL OR author = '')
                """,
                (source_id,),
            ).fetchall()
            item_ids = [row["id"] for row in rows]
            if not item_ids:
                return 0
            placeholders = ",".join("?" for _ in item_ids)
            conn.execute(f"DELETE FROM event_articles WHERE news_item_id IN ({placeholders})", item_ids)
            conn.execute(f"DELETE FROM news_scores WHERE news_item_id IN ({placeholders})", item_ids)
            conn.execute(f"DELETE FROM news_relations WHERE news_item_id IN ({placeholders})", item_ids)
            conn.execute(f"DELETE FROM news_rank_snapshots WHERE news_item_id IN ({placeholders})", item_ids)
            conn.execute(f"DELETE FROM news_items WHERE id IN ({placeholders})", item_ids)
            return len(item_ids)

    def set_fetch_cache(self, source_id: str, *, fetched_at: str, payload: dict[str, Any]) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fetch_cache (source_id, fetched_at, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    payload_json = excluded.payload_json
                """,
                (source_id, fetched_at, json.dumps(payload, ensure_ascii=False)),
            )

    def save_raw_payload(self, *, source_id: str, url: str, title: str, payload: dict[str, Any]) -> tuple[str, Path]:
        self.initialize()
        payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        path = self.raw_dir / source_id / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(payload_text, encoding="utf-8")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO raw_news (
                    id, source_id, fetched_at, url, title, raw_payload_hash, raw_payload_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (digest, source_id, _now(), url, title, digest, str(path)),
            )
        return digest, path

    def save_news_item(self, *, source_id: str, title: str, summary: str, url: str, published_at: str | None, author: str | None, raw_news_id: str) -> str:
        self.initialize()
        normalized_text_hash = hashlib.sha256(f"{title}\n{summary}".lower().encode("utf-8")).hexdigest()
        item_id = hashlib.sha256(f"{source_id}\n{url}\n{title}".encode("utf-8")).hexdigest()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_items (
                    id, source_id, title, summary, url, published_at, author,
                    normalized_text_hash, raw_news_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    summary = excluded.summary,
                    url = excluded.url,
                    published_at = excluded.published_at,
                    author = excluded.author,
                    normalized_text_hash = excluded.normalized_text_hash,
                    raw_news_id = excluded.raw_news_id
                """,
                (
                    item_id,
                    source_id,
                    title,
                    summary,
                    url,
                    published_at,
                    author,
                    normalized_text_hash,
                    raw_news_id,
                    _now(),
                ),
            )
            duplicate_ids = [
                row["id"]
                for row in conn.execute(
                    """
                    SELECT id FROM news_items
                    WHERE source_id = ?
                      AND normalized_text_hash = ?
                      AND id <> ?
                    """,
                    (source_id, normalized_text_hash, item_id),
                ).fetchall()
            ]
            for duplicate_id in duplicate_ids:
                conn.execute("DELETE FROM event_articles WHERE news_item_id = ?", (duplicate_id,))
                conn.execute("DELETE FROM news_scores WHERE news_item_id = ?", (duplicate_id,))
                conn.execute("DELETE FROM news_relations WHERE news_item_id = ?", (duplicate_id,))
                conn.execute("DELETE FROM news_items WHERE id = ?", (duplicate_id,))
        return item_id

    def save_rank_snapshot(
        self,
        *,
        source_id: str,
        snapshot_date: str,
        snapshot_at: str,
        rank: int,
        news_item_id: str,
        title: str,
        summary: str,
        url: str,
        published_at: str | None,
        author: str | None,
        raw_news_id: str | None,
    ) -> str:
        self.initialize()
        snapshot_id = hashlib.sha256(f"{source_id}\n{snapshot_date}\n{rank}".encode("utf-8")).hexdigest()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_rank_snapshots (
                    id, source_id, snapshot_date, snapshot_at, rank, news_item_id,
                    title, summary, url, published_at, author, raw_news_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, snapshot_date, rank) DO UPDATE SET
                    snapshot_at = excluded.snapshot_at,
                    news_item_id = excluded.news_item_id,
                    title = excluded.title,
                    summary = excluded.summary,
                    url = excluded.url,
                    published_at = excluded.published_at,
                    author = excluded.author,
                    raw_news_id = excluded.raw_news_id
                """,
                (
                    snapshot_id,
                    source_id,
                    snapshot_date,
                    snapshot_at,
                    rank,
                    news_item_id,
                    title,
                    summary,
                    url,
                    published_at,
                    author,
                    raw_news_id,
                    _now(),
                ),
            )
        return snapshot_id

    def list_rank_snapshots(
        self,
        *,
        source_id: str,
        start_date: str,
        end_date: str,
        rank_limit: int,
    ) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT snapshots.id, snapshots.news_item_id, snapshots.source_id,
                       snapshots.title, snapshots.summary, snapshots.url,
                       COALESCE(snapshots.published_at, snapshots.snapshot_at) AS published_at, snapshots.author,
                       snapshots.snapshot_date AS rank_snapshot_date,
                       snapshots.rank AS rank_snapshot_rank,
                       news_sources.name AS source_name, news_sources.tier AS source_tier,
                       news_scores.relevance_score, news_scores.duration_score,
                       news_scores.surprise_score, news_scores.reliability_score,
                       news_scores.total_score
                FROM news_rank_snapshots AS snapshots
                JOIN news_sources ON news_sources.id = snapshots.source_id
                LEFT JOIN news_scores ON news_scores.news_item_id = snapshots.news_item_id
                WHERE news_sources.enabled = 1
                  AND snapshots.source_id = ?
                  AND snapshots.snapshot_date BETWEEN ? AND ?
                  AND snapshots.rank <= ?
                ORDER BY snapshots.snapshot_date DESC, snapshots.rank ASC
                """,
                (source_id, start_date, end_date, rank_limit),
            ).fetchall()
            item_ids = [row["news_item_id"] for row in rows]
            relations_by_item = self._relations_by_item(conn, item_ids)
        result = []
        for row in rows:
            item = dict(row)
            item["relations"] = relations_by_item.get(item["news_item_id"], [])
            result.append(item)
        return result

    def upsert_news_event(self, *, event_id: str, canonical_title: str, event_key: str, best_source_id: str, importance_score: float) -> None:
        self.initialize()
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_events (
                    id, canonical_title, event_key, best_source_id, importance_score, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_key) DO UPDATE SET
                    best_source_id = excluded.best_source_id,
                    importance_score = excluded.importance_score,
                    updated_at = excluded.updated_at
                """,
                (event_id, canonical_title, event_key, best_source_id, importance_score, now, now),
            )

    def link_event_article(self, *, event_id: str, news_item_id: str) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO event_articles (event_id, news_item_id) VALUES (?, ?)",
                (event_id, news_item_id),
            )

    def save_news_score(
        self,
        *,
        news_item_id: str,
        relevance_score: int,
        duration_score: int,
        surprise_score: int,
        reliability_score: int,
        total_score: int,
    ) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO news_scores (
                    news_item_id, relevance_score, duration_score, surprise_score,
                    reliability_score, total_score
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(news_item_id) DO UPDATE SET
                    relevance_score = excluded.relevance_score,
                    duration_score = excluded.duration_score,
                    surprise_score = excluded.surprise_score,
                    reliability_score = excluded.reliability_score,
                    total_score = excluded.total_score
                """,
                (
                    news_item_id,
                    relevance_score,
                    duration_score,
                    surprise_score,
                    reliability_score,
                    total_score,
                ),
            )

    def replace_news_relations(self, news_item_id: str, relations: list[dict[str, Any]]) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM news_relations WHERE news_item_id = ?", (news_item_id,))
            for relation in relations:
                conn.execute(
                    """
                    INSERT INTO news_relations (
                        news_item_id, fund_code, fund_name, relation_type,
                        matched_keywords_json, impact_variables_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        news_item_id,
                        relation.get("fund_code"),
                        relation["fund_name"],
                        relation["relation_type"],
                        json.dumps(relation.get("matched_keywords", []), ensure_ascii=False),
                        json.dumps(relation.get("impact_variables", []), ensure_ascii=False),
                    ),
                )

    def list_recent_news_items(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT news_items.*, news_sources.name AS source_name, news_sources.tier AS source_tier
                , news_scores.relevance_score, news_scores.duration_score, news_scores.surprise_score
                , news_scores.reliability_score, news_scores.total_score
                FROM news_items
                JOIN news_sources ON news_sources.id = news_items.source_id
                LEFT JOIN news_scores ON news_scores.news_item_id = news_items.id
                WHERE news_sources.enabled = 1
                ORDER BY COALESCE(news_items.published_at, news_items.created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            item_ids = [row["id"] for row in rows]
            relations_by_item = self._relations_by_item(conn, item_ids)
        result = []
        for row in rows:
            item = dict(row)
            item["relations"] = relations_by_item.get(item["id"], [])
            result.append(item)
        return result

    def _relations_by_item(self, conn: sqlite3.Connection, item_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not item_ids:
            return {}
        placeholders = ",".join("?" for _ in item_ids)
        rows = conn.execute(
            f"SELECT * FROM news_relations WHERE news_item_id IN ({placeholders}) ORDER BY fund_name",
            item_ids,
        ).fetchall()
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            item = _decode_json_columns(dict(row), "matched_keywords_json", "impact_variables_json")
            result.setdefault(item["news_item_id"], []).append(item)
        return result

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_json_columns(row: dict[str, Any], *columns: str) -> dict[str, Any]:
    for column in columns:
        value = row.pop(column, "[]")
        target = column.removesuffix("_json")
        try:
            row[target] = json.loads(value or "[]")
        except json.JSONDecodeError:
            row[target] = []
    return row


_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT NOT NULL,
    lookup_query TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    tags_json TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(code),
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT '',
    origin TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL,
    reliability_score INTEGER NOT NULL,
    adapter TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    cache_minutes INTEGER NOT NULL DEFAULT 10,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 12,
    requires_login INTEGER NOT NULL DEFAULT 0,
    homepage TEXT NOT NULL,
    terms_note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS raw_news (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES news_sources(id),
    fetched_at TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    raw_payload_hash TEXT NOT NULL,
    raw_payload_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_cache (
    source_id TEXT PRIMARY KEY REFERENCES news_sources(id),
    fetched_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_items (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES news_sources(id),
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    published_at TEXT,
    author TEXT,
    normalized_text_hash TEXT NOT NULL,
    raw_news_id TEXT REFERENCES raw_news(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_rank_snapshots (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES news_sources(id),
    snapshot_date TEXT NOT NULL,
    snapshot_at TEXT NOT NULL,
    rank INTEGER NOT NULL,
    news_item_id TEXT NOT NULL REFERENCES news_items(id),
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    published_at TEXT,
    author TEXT,
    raw_news_id TEXT REFERENCES raw_news(id),
    created_at TEXT NOT NULL,
    UNIQUE(source_id, snapshot_date, rank)
);

CREATE INDEX IF NOT EXISTS idx_news_rank_snapshots_period
ON news_rank_snapshots(source_id, snapshot_date, rank);

CREATE TABLE IF NOT EXISTS news_events (
    id TEXT PRIMARY KEY,
    canonical_title TEXT NOT NULL,
    event_key TEXT NOT NULL UNIQUE,
    best_source_id TEXT REFERENCES news_sources(id),
    importance_score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_articles (
    event_id TEXT NOT NULL REFERENCES news_events(id),
    news_item_id TEXT NOT NULL REFERENCES news_items(id),
    PRIMARY KEY (event_id, news_item_id)
);

CREATE TABLE IF NOT EXISTS news_scores (
    news_item_id TEXT PRIMARY KEY REFERENCES news_items(id),
    relevance_score INTEGER NOT NULL,
    duration_score INTEGER NOT NULL,
    surprise_score INTEGER NOT NULL,
    reliability_score INTEGER NOT NULL,
    total_score INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS news_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id TEXT NOT NULL REFERENCES news_items(id),
    fund_code TEXT,
    fund_name TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    matched_keywords_json TEXT NOT NULL DEFAULT '[]',
    impact_variables_json TEXT NOT NULL DEFAULT '[]'
);

"""
