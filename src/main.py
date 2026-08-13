#!/usr/bin/env python3
"""Rakuten Market scraper — Apify Actor. httpx + BS4, SSR only, no Playwright needed."""
import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

try:
    from apify import Actor
except ImportError:
    Actor = None

BASE = "https://search.rakuten.co.jp"


async def fetch(url: str, client: httpx.AsyncClient) -> str:
    resp = await client.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url}")
    return resp.text


def parse_search(html: str) -> list[dict[str, Any]]:
    """検索結果ページの商品カードを抽出。"""
    soup = BeautifulSoup(html, "lxml")
    items: list[dict[str, Any]] = []
    for card in soup.select(".searchresultitem"):
        a = card.select_one('a[href*="item.rakuten.co.jp"]')
        if not a:
            continue
        detail_url = a.get("href", "")
        if detail_url and not detail_url.startswith("http"):
            detail_url = "https://" + detail_url.lstrip("/")

        # 商品名: title属性を持つa要素（商品画像リンク）のtitleが商品名
        title = ""
        for el in card.select("a[title]"):
            t = el.get("title", "").strip()
            if t and "item.rakuten.co.jp" in el.get("href", ""):
                title = t
                break
        if not title:
            # フォールバック: リンク内テキストが長いもの
            for a2 in card.select('a[href*="item.rakuten.co.jp"]'):
                txt = a2.get_text(strip=True)
                if len(txt) > 5:
                    title = txt
                    break

        # 価格（数値+円を含む要素）
        price = ""
        price_num = ""
        for p in card.select("[class*='price']"):
            txt = p.get_text(strip=True)
            m = re.search(r"([\d,]+)円", txt)
            if m:
                price = txt
                price_num = m.group(1)
                break

        # ショップ名（店舗トップへのリンク www.rakuten.co.jp/<shop>）
        shop = ""
        for el in card.select('a[href*="www.rakuten.co.jp/"]'):
            t = el.get_text(strip=True)
            if t and len(t) < 40:
                shop = t
                break

        # レビュー
        review = ""
        rev_el = card.select_one("[class*='review'], [class*='rating']")
        if rev_el:
            review = rev_el.get_text(strip=True)

        items.append({
            "title": title,
            "price": price,
            "price_jpy": price_num,
            "shop": shop,
            "review": review,
            "detail_url": detail_url,
        })
    return items


async def main() -> None:
    actor_input = {}
    if Actor is not None:
        async with Actor:
            actor_input = await Actor.get_input() or {}
            await _run(actor_input)
    else:
        import json as _json
        import sys as _sys
        raw = _sys.stdin.read().strip()
        if raw:
            actor_input = _json.loads(raw)
        await _run(actor_input)


async def _run(actor_input: dict) -> None:
    search_keyword = actor_input.get("searchKeyword", "ポケモン")
    max_items = int(actor_input.get("maxItems", 30))
    max_pages = int(actor_input.get("maxPages", 2))
    stats_mode = bool(actor_input.get("statsMode", False))

    proxy_url = None
    if Actor is not None:
        proxy_cfg = await Actor.create_proxy_configuration(
            actor_proxy_input=actor_input.get("proxyConfiguration")
        )
        if proxy_cfg:
            proxy_url = await proxy_cfg.new_url()

    async with httpx.AsyncClient(
        proxy=proxy_url,
        follow_redirects=True,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        },
    ) as client:
        all_items: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            if page == 1:
                url = f"{BASE}/search/mall/{quote(search_keyword)}/"
            else:
                url = f"{BASE}/search/mall/{quote(search_keyword)}/?p={page}"
            print(f"[INFO] fetching page {page}: {url}")
            try:
                html = await fetch(url, client)
            except Exception as e:
                print(f"[WARN] page {page} failed: {e}")
                break
            items = parse_search(html)
            if not items:
                print(f"[INFO] page {page} empty, stop")
                break
            all_items.extend(items)

        if stats_mode:
            prices: list[int] = []
            for it in all_items:
                pn = it.get("price_jpy", "")
                if pn:
                    prices.append(int(pn.replace(",", "")))
            if prices:
                s = sorted(prices)
                n = len(s)
                median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2
                result = {
                    "statsType": "japan-rakuten-price",
                    "keyword": search_keyword,
                    "count": n,
                    "priceMin": s[0],
                    "priceMax": s[-1],
                    "priceAvg": sum(prices) // n,
                    "priceMedian": median,
                    "sampleItems": all_items[:3],
                    "collectedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
            else:
                result = {
                    "statsType": "japan-rakuten-price",
                    "keyword": search_keyword,
                    "count": 0,
                    "priceMin": None, "priceMax": None,
                    "priceAvg": None, "priceMedian": None,
                    "sampleItems": [],
                    "collectedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
            if Actor is not None:
                await Actor.push_data(result)
            else:
                print(result)
        else:
            for item in all_items[:max_items]:
                if Actor is not None:
                    await Actor.push_data(item)
                else:
                    print(item)

    if Actor is not None:
        await Actor.set_status_message(f"Done: {len(all_items)} items")
    else:
        print(f"DONE {len(all_items)} items")


if __name__ == "__main__":
    asyncio.run(main())
