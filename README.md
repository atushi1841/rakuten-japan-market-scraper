# Rakuten Market Scraper

Scrape product listings and price statistics from **Rakuten Ichiba** (楽天市場), Japan's largest e-commerce marketplace.

## Features

- **Search products** by keyword (brands, categories, model names)
- **Price statistics mode** (`statsMode`) — returns count/min/max/avg/median price for a keyword, ideal for market price APIs
- Multi-page crawling (each page ~45 products)
- No API key required — direct web scraping

## Input

| Field | Type | Description | Default |
|---|---|---|---|
| `searchKeyword` | string | Keyword to search (e.g. ルイヴィトン, ポケモン, iPhone) | ルイヴィトン |
| `maxItems` | integer | Max products to return | 30 |
| `maxPages` | integer | Search result pages to crawl | 2 |
| `statsMode` | boolean | Return price statistics instead of raw listings | false |

## Output

Each result contains: `title`, `price`, `price_jpy`, `shop`, `review`, `detail_url`.

When `statsMode=true`, returns a single statistics object: `statsType`, `keyword`, `count`, `priceMin`, `priceMax`, `priceAvg`, `priceMedian`, `sampleItems`.

## Use Cases

- Market price research for brands and products
- Price monitoring and comparison
- E-commerce data for resale or analysis

## MCP Registry

This server is registered on the official [MCP Registry](https://registry.modelcontextprotocol.io).
Find it via search: [rakuten-japan-market-scraper](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.rakuten-japan-market-scraper)
