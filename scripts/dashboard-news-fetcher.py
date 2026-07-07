#!/usr/bin/env python3
import argparse
import html
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path


OUT = Path("/tmp/world-news-dashboard.js")
CACHE = Path("/tmp/world-news-dashboard-cache.json")

CHINA_HOT_SOURCES = [
    {"name": "百度热搜", "url": "https://top.baidu.com/board?tab=realtime", "weight": 120},
    {"name": "微博热搜", "url": "https://s.weibo.com/top/summary?cate=realtimehot", "weight": 110},
]


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def fetch_html(url, timeout=10):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 dashboard-news-fetcher",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_baidu_hot(source):
    text = fetch_html(source["url"])
    titles = []
    for pattern in [
        r'"word"\s*:\s*"([^"]+)"',
        r'"query"\s*:\s*"([^"]+)"',
        r'class="c-single-text-ellipsis">([^<]+)<',
    ]:
        for title in re.findall(pattern, text):
            title = clean_text(title)
            if title and title not in titles:
                titles.append(title)
        if len(titles) >= 10:
            break
    return hot_items_from_titles(titles, source)


def fetch_weibo_hot(source):
    text = fetch_html(source["url"])
    titles = []
    for title in re.findall(r'<td class="td-02">.*?<a[^>]*>(.*?)</a>', text, flags=re.S):
        title = clean_text(title)
        if title and title not in titles and "更多" not in title:
            titles.append(title)
    return hot_items_from_titles(titles, source)


def hot_items_from_titles(titles, source):
    now = time.time()
    items = []
    for index, title in enumerate(titles[:20], start=1):
        items.append({
            "title": title,
            "source": source["name"],
            "link": source["url"],
            "publishedTs": now - index,
            "published": datetime.now().astimezone().strftime("%H:%M"),
            "weight": source["weight"] - index,
        })
    return items


def fetch_china_hot():
    items = []
    errors = []
    for source in CHINA_HOT_SOURCES:
        try:
            if source["name"] == "百度热搜":
                items.extend(fetch_baidu_hot(source))
            elif source["name"] == "微博热搜":
                items.extend(fetch_weibo_hot(source))
        except Exception as exc:
            errors.append(f"{source['name']}: {exc}")
    return items, errors


def normalize_key(title):
    title = title.lower()
    title = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", title)
    words = [word for word in title.split() if len(word) > 2]
    return " ".join(words[:8]) or title[:40]


def score(item):
    age_hours = max(0, (time.time() - item.get("publishedTs", 0)) / 3600)
    recency = max(0, 72 - age_hours)
    return item.get("weight", 0) + recency


def collect_news(limit=10):
    all_items, errors = fetch_china_hot()

    seen = set()
    deduped = []
    for item in sorted(all_items, key=score, reverse=True):
        key = normalize_key(item["title"])
        if key in seen:
            continue
        seen.add(key)
        item["rank"] = len(deduped) + 1
        deduped.append(item)
        if len(deduped) >= limit:
            break

    if not deduped and CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            allowed_sources = {source["name"] for source in CHINA_HOT_SOURCES}
            if all(item.get("source") in allowed_sources for item in cached.get("items", [])):
                return cached
        except Exception:
            pass

    payload = {
        "updatedAt": datetime.now().astimezone().strftime("%H:%M"),
        "errors": errors[-3:],
        "items": deduped,
    }
    if deduped:
        CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_dashboard_js(payload):
    OUT.write_text(
        "window.__WORLD_NEWS__ = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )


def run_once():
    payload = collect_news()
    write_dashboard_js(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Fetch China hot news feeds for the dashboard.")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=600)
    args = parser.parse_args()

    while True:
        run_once()
        if not args.loop:
            return 0
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
