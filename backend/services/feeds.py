from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import feedparser
import httpx

from ..models import NewsItem, ThreatLevel

GLOBAL_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("AP News", "https://rsshub.app/apnews/topics/apf-topnews"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/"),
    ("Politico", "https://rss.politico.com/politics-news.xml"),
    ("Foreign Policy", "https://foreignpolicy.com/feed/"),
]

THREAT_KEYWORDS: list[tuple[ThreatLevel, str, list[str]]] = [
    (ThreatLevel.CRITICAL, "conflict", [
        "nuclear", "missile strike", "war declared", "invasion", "airstrike kills",
        "coup", "assassination", "mass casualty", "chemical weapon", "dirty bomb",
        "martial law", "genocide",
    ]),
    (ThreatLevel.HIGH, "security", [
        "attack", "bombing", "explosion", "shooting", "killed", "hostage",
        "terrorist", "conflict", "offensive", "troops deployed", "sanctions",
        "ceasefire", "escalation", "warship", "military exercises",
    ]),
    (ThreatLevel.HIGH, "disaster", [
        "earthquake", "tsunami", "hurricane", "typhoon", "flood kills",
        "wildfire", "eruption", "catastrophic",
    ]),
    (ThreatLevel.MEDIUM, "politics", [
        "election", "protest", "crisis", "emergency", "shutdown",
        "impeachment", "indicted", "arrested", "detained", "expelled",
        "diplomatic", "summit", "agreement",
    ]),
    (ThreatLevel.MEDIUM, "economy", [
        "recession", "crash", "collapse", "default", "bankrupt",
        "inflation", "unemployment spike", "rate hike", "supply chain",
    ]),
    (ThreatLevel.MEDIUM, "cyber", [
        "hack", "breach", "ransomware", "cyberattack", "data leak",
        "malware", "phishing campaign", "zero-day",
    ]),
    (ThreatLevel.LOW, "general", [
        "trade deal", "policy", "reform", "budget", "statement",
        "meeting", "conference", "report",
    ]),
]


def classify_threat(title: str) -> tuple[ThreatLevel, str]:
    lower = title.lower()
    for level, category, words in THREAT_KEYWORDS:
        for kw in words:
            if kw in lower:
                return level, category
    return ThreatLevel.INFO, "general"


def _local_feed_urls(city: str, country: str) -> list[tuple[str, str]]:
    city_encoded = city.replace(" ", "+")
    city_path = quote(city)
    return [
        ("Google News Local",
         f"https://news.google.com/rss/search?q={city_encoded}+news&hl=en&gl={country}&ceid={country}:en"),
        ("Google News Country",
         f"https://news.google.com/rss/headlines/section/geo/{city_path}"),
    ]


async def _fetch_single_feed(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    is_local: bool,
    cutoff: datetime,
) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        resp = await client.get(url, headers={"User-Agent": "watchtower/1.0 (Python RSS reader)"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception:
        return items

    for entry in feed.entries:
        title = getattr(entry, "title", "")
        if not title:
            continue

        pub = datetime.now(timezone.utc)
        for attr in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, attr, None)
            if parsed:
                try:
                    pub = datetime(*parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
                break

        if pub < cutoff:
            continue

        level, cat = classify_threat(title)
        link = getattr(entry, "link", "")

        items.append(NewsItem(
            title=title,
            source=name,
            published=pub,
            url=link,
            threat_level=level,
            category=cat,
            is_local=is_local,
        ))

    return items


async def _fetch_feeds(
    sources: list[tuple[str, str]],
    is_local: bool,
) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        tasks = [
            _fetch_single_feed(client, name, url, is_local, cutoff)
            for name, url in sources
        ]
        results = await asyncio.gather(*tasks)

    all_items: list[NewsItem] = []
    for batch in results:
        all_items.extend(batch)

    # Sort: critical first, then by time
    all_items.sort(key=lambda x: (-x.threat_level, x.published), reverse=False)
    all_items.sort(key=lambda x: (-x.threat_level,))

    # Proper sort: by threat_level descending, then published descending
    all_items.sort(key=lambda x: (-x.threat_level, -x.published.timestamp()))

    # Dedup by first 40 chars of title
    seen: set[str] = set()
    deduped: list[NewsItem] = []
    for item in all_items:
        key = item.title[:40].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


async def fetch_global_news() -> list[NewsItem]:
    return await _fetch_feeds(GLOBAL_FEEDS, is_local=False)


async def fetch_local_news(city: str, country: str) -> list[NewsItem]:
    return await _fetch_feeds(_local_feed_urls(city, country), is_local=True)
