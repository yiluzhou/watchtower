from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import httpx

from ..models import CryptoPrice, StockIndex, Commodity, PredictionMarket

YAHOO_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

STOCK_INDICES = [
    ("%5EGSPC", "S&P 500"),
    ("%5EDJI", "Dow Jones"),
]

COMMODITY_DEFS = [
    ("CL%3DF", "WTI Crude Oil", "$/bbl"),
    ("GC%3DF", "Gold", "$/oz"),
    ("HG%3DF", "Copper", "$/lb"),
]


async def fetch_crypto_prices(client: httpx.AsyncClient, ids: list[str]) -> list[CryptoPrice]:
    joined = ",".join(ids)
    url = (
        f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={joined}"
        f"&order=market_cap_desc&per_page=20&page=1&sparkline=false"
        f"&price_change_percentage=24h"
    )
    resp = await client.get(url, headers={"Accept": "application/json"})
    if resp.status_code == 429:
        raise RuntimeError("CoinGecko rate limited (try again in ~1min)")
    resp.raise_for_status()

    prices: list[CryptoPrice] = []
    for r in resp.json():
        last_updated = None
        if r.get("last_updated"):
            try:
                last_updated = datetime.fromisoformat(r["last_updated"].replace("Z", "+00:00"))
            except Exception:
                pass
        prices.append(CryptoPrice(
            id=r["id"],
            symbol=r["symbol"].upper(),
            name=r["name"],
            price_usd=r.get("current_price", 0),
            change_24h=r.get("price_change_percentage_24h", 0) or 0,
            market_cap_usd=r.get("market_cap", 0) or 0,
            volume_24h_usd=r.get("total_volume", 0) or 0,
            last_updated=last_updated,
        ))
    return prices


async def _fetch_yahoo_chart(client: httpx.AsyncClient, symbol: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    resp = await client.get(url, headers={
        "User-Agent": YAHOO_UA,
        "Accept": "application/json",
    })
    resp.raise_for_status()
    data = resp.json()

    chart = data.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo error for {symbol}: {chart['error'].get('description', '')}")

    results = chart.get("result", [])
    if not results:
        raise RuntimeError(f"No results from Yahoo for {symbol}")

    meta = results[0].get("meta", {})
    price = meta.get("regularMarketPrice", 0)
    prev_close = meta.get("previousClose", 0)
    change_pct = meta.get("regularMarketChangePercent", 0)

    if change_pct == 0 and prev_close != 0:
        change_pct = ((price - prev_close) / prev_close) * 100

    if prev_close == 0:
        chart_prev = meta.get("chartPreviousClose", 0)
        if chart_prev != 0:
            prev_close = chart_prev
            if change_pct == 0:
                change_pct = ((price - chart_prev) / chart_prev) * 100

    return {
        "symbol": meta.get("symbol", symbol),
        "price": price,
        "prev_close": prev_close,
        "change_pct": change_pct,
    }


async def fetch_stock_indices(client: httpx.AsyncClient) -> list[StockIndex]:
    async def _fetch_one(symbol: str, name: str) -> StockIndex | None:
        try:
            meta = await _fetch_yahoo_chart(client, symbol)
            return StockIndex(
                symbol=meta["symbol"],
                name=name,
                price=meta["price"],
                prev_close=meta["prev_close"],
                change_pct=meta["change_pct"],
            )
        except Exception:
            return None

    results = await asyncio.gather(*[_fetch_one(sym, name) for sym, name in STOCK_INDICES])
    return [r for r in results if r is not None]


async def fetch_commodities(client: httpx.AsyncClient) -> list[Commodity]:
    async def _fetch_one(symbol: str, name: str, unit: str) -> Commodity | None:
        try:
            meta = await _fetch_yahoo_chart(client, symbol)
            return Commodity(
                symbol=meta["symbol"],
                name=name,
                price=meta["price"],
                prev_close=meta["prev_close"],
                unit=unit,
                change_pct=meta["change_pct"],
            )
        except Exception:
            return None

    results = await asyncio.gather(*[_fetch_one(sym, name, unit) for sym, name, unit in COMMODITY_DEFS])
    return [r for r in results if r is not None]


async def fetch_prediction_markets(client: httpx.AsyncClient) -> list[PredictionMarket]:
    url = (
        "https://gamma-api.polymarket.com/markets"
        "?tag_id=100265&limit=20&closed=false&active=true&order=volume&ascending=false"
    )
    resp = await client.get(url, headers={"Accept": "application/json"})
    resp.raise_for_status()

    markets: list[PredictionMarket] = []
    for r in resp.json():
        question = r.get("question", "")
        if not question:
            continue

        prob = 0.5
        outcome_prices = r.get("outcomePrices", "")
        if outcome_prices:
            try:
                prices = json.loads(outcome_prices)
                if prices:
                    prob = float(prices[0])
            except (json.JSONDecodeError, ValueError, IndexError):
                pass

        vol = 0.0
        try:
            vol = float(r.get("volume", 0))
        except (ValueError, TypeError):
            pass

        cat = "politics"
        tags = r.get("tags", [])
        if tags:
            cat = tags[0].get("slug", "politics")

        end_date = r.get("endDateIso", "")[:10] if r.get("endDateIso") else ""

        markets.append(PredictionMarket(
            title=question,
            probability=prob,
            volume=vol,
            category=cat,
            end_date=end_date,
            slug=r.get("slug", ""),
        ))

    return markets


async def fetch_all_markets(crypto_pairs: list[str]) -> dict:
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        crypto_task = fetch_crypto_prices(client, crypto_pairs)
        stocks_task = fetch_stock_indices(client)
        commodities_task = fetch_commodities(client)
        polymarket_task = fetch_prediction_markets(client)

        results = await asyncio.gather(
            crypto_task, stocks_task, commodities_task, polymarket_task,
            return_exceptions=True,
        )

    crypto = results[0] if not isinstance(results[0], Exception) else []
    stocks = results[1] if not isinstance(results[1], Exception) else []
    commodities = results[2] if not isinstance(results[2], Exception) else []
    polymarket = results[3] if not isinstance(results[3], Exception) else []

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            labels = ["crypto", "stocks", "commodities", "polymarket"]
            errors.append(f"{labels[i]}: {r}")

    return {
        "crypto": crypto if isinstance(crypto, list) else [],
        "stocks": stocks if isinstance(stocks, list) else [],
        "commodities": commodities if isinstance(commodities, list) else [],
        "polymarket": polymarket if isinstance(polymarket, list) else [],
        "errors": errors,
    }
