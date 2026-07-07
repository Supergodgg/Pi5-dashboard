#!/usr/bin/env python3
import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


OUT = Path("/tmp/worldcup-dashboard.js")
CACHE = Path("/tmp/worldcup-dashboard-cache.json")
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
TEAM_ZH = {
    "Argentina": "阿根廷",
    "ARG": "阿根廷",
    "Australia": "澳大利亚",
    "AUS": "澳大利亚",
    "Austria": "奥地利",
    "AUT": "奥地利",
    "Belgium": "比利时",
    "BEL": "比利时",
    "Bolivia": "玻利维亚",
    "BOL": "玻利维亚",
    "Brazil": "巴西",
    "BRA": "巴西",
    "Cameroon": "喀麦隆",
    "CMR": "喀麦隆",
    "Canada": "加拿大",
    "CAN": "加拿大",
    "Chile": "智利",
    "CHI": "智利",
    "China": "中国",
    "CHN": "中国",
    "Colombia": "哥伦比亚",
    "COL": "哥伦比亚",
    "Costa Rica": "哥斯达黎加",
    "CRC": "哥斯达黎加",
    "Croatia": "克罗地亚",
    "CRO": "克罗地亚",
    "Czechia": "捷克",
    "CZE": "捷克",
    "Denmark": "丹麦",
    "DEN": "丹麦",
    "Ecuador": "厄瓜多尔",
    "ECU": "厄瓜多尔",
    "Egypt": "埃及",
    "EGY": "埃及",
    "England": "英格兰",
    "ENG": "英格兰",
    "France": "法国",
    "FRA": "法国",
    "Germany": "德国",
    "GER": "德国",
    "Ghana": "加纳",
    "GHA": "加纳",
    "Greece": "希腊",
    "GRE": "希腊",
    "Hungary": "匈牙利",
    "HUN": "匈牙利",
    "Iran": "伊朗",
    "IRN": "伊朗",
    "Iraq": "伊拉克",
    "IRQ": "伊拉克",
    "Italy": "意大利",
    "ITA": "意大利",
    "Ivory Coast": "科特迪瓦",
    "Cote d'Ivoire": "科特迪瓦",
    "CIV": "科特迪瓦",
    "Japan": "日本",
    "JPN": "日本",
    "Mexico": "墨西哥",
    "MEX": "墨西哥",
    "Morocco": "摩洛哥",
    "MAR": "摩洛哥",
    "Netherlands": "荷兰",
    "NED": "荷兰",
    "New Zealand": "新西兰",
    "NZL": "新西兰",
    "Nigeria": "尼日利亚",
    "NGA": "尼日利亚",
    "Norway": "挪威",
    "NOR": "挪威",
    "Panama": "巴拿马",
    "PAN": "巴拿马",
    "Paraguay": "巴拉圭",
    "PAR": "巴拉圭",
    "Peru": "秘鲁",
    "PER": "秘鲁",
    "Poland": "波兰",
    "POL": "波兰",
    "Portugal": "葡萄牙",
    "POR": "葡萄牙",
    "Qatar": "卡塔尔",
    "QAT": "卡塔尔",
    "Republic of Ireland": "爱尔兰",
    "Ireland": "爱尔兰",
    "IRL": "爱尔兰",
    "Romania": "罗马尼亚",
    "ROU": "罗马尼亚",
    "Saudi Arabia": "沙特阿拉伯",
    "KSA": "沙特阿拉伯",
    "Scotland": "苏格兰",
    "SCO": "苏格兰",
    "Senegal": "塞内加尔",
    "SEN": "塞内加尔",
    "Serbia": "塞尔维亚",
    "SRB": "塞尔维亚",
    "South Korea": "韩国",
    "KOR": "韩国",
    "Spain": "西班牙",
    "ESP": "西班牙",
    "Switzerland": "瑞士",
    "SUI": "瑞士",
    "Tunisia": "突尼斯",
    "TUN": "突尼斯",
    "Ukraine": "乌克兰",
    "UKR": "乌克兰",
    "United States": "美国",
    "USA": "美国",
    "Uruguay": "乌拉圭",
    "URU": "乌拉圭",
    "Wales": "威尔士",
    "WAL": "威尔士",
}


def fetch_json(url, timeout=10):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 dashboard-worldcup-fetcher"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def localize_team_name(name):
    if not name:
        return name
    normalized = " ".join(str(name).split())
    return TEAM_ZH.get(normalized, TEAM_ZH.get(normalized.upper(), normalized))


def team_display_name(team):
    candidates = [
        team.get("shortDisplayName"),
        team.get("displayName"),
        team.get("name"),
        team.get("abbreviation"),
    ]
    for candidate in candidates:
        localized = localize_team_name(candidate)
        if localized and localized != candidate:
            return localized
    return localize_team_name(next((item for item in candidates if item), ""))


def event_start_at(event):
    raw_date = event.get("date")
    if not raw_date:
        return ""
    try:
        event_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ""
    return event_dt.strftime("%m-%d %H:%M")


def event_date(event):
    raw_date = event.get("date")
    if not raw_date:
        return None
    try:
        return datetime.fromisoformat(raw_date.replace("Z", "+00:00")).astimezone().date()
    except ValueError:
        return None


def event_to_match(event):
    competition = (event.get("competitions") or [{}])[0]
    competitors = competition.get("competitors") or []
    if len(competitors) < 2:
        return None

    home = next((item for item in competitors if item.get("homeAway") == "home"), competitors[0])
    away = next((item for item in competitors if item.get("homeAway") == "away"), competitors[1])
    home_name = team_display_name(home.get("team", {})) or "主队"
    away_name = team_display_name(away.get("team", {})) or "客队"
    home_score = home.get("score")
    away_score = away.get("score")

    status = event.get("status", {})
    status_type = status.get("type", {})
    state = status_type.get("state") or ""
    description = status_type.get("shortDetail") or status_type.get("description") or ""
    clock = status.get("displayClock") or ""
    period = status.get("period")
    venue = competition.get("venue", {}).get("shortName") or competition.get("venue", {}).get("fullName") or ""

    if state in ("in", "post") and home_score is not None and away_score is not None:
        teams = f"{away_name} {away_score} - {home_score} {home_name}"
    else:
        teams = f"{away_name} vs {home_name}"

    detail_parts = []
    start_at = event_start_at(event)
    if start_at:
        detail_parts.append(start_at)
    if description:
        detail_parts.append(description)
    if state == "in" and clock:
        detail_parts.append(clock)
    elif period and state == "in":
        detail_parts.append(f"P{period}")
    if venue:
        detail_parts.append(venue)

    return {
        "teams": teams,
        "meta": " · ".join(detail_parts) or "--",
        "state": state or "pre",
        "updatedAt": datetime.now().astimezone().strftime("%H:%M:%S"),
    }


def collect_matches():
    now = datetime.now()
    date_targets = [now - timedelta(days=1), now, now + timedelta(days=1)]
    start_date = date_targets[0].astimezone().date()
    end_date = date_targets[-1].astimezone().date()
    query_dates = [target.strftime("%Y%m%d") for target in date_targets]
    urls = [f"{ESPN_BASE}?dates={query_dates[0]}-{query_dates[-1]}"]
    urls.extend(f"{ESPN_BASE}?dates={query_date}" for query_date in query_dates)
    urls.append(ESPN_BASE)
    errors = []
    matches = []
    seen = set()
    for url in urls:
        try:
            data = fetch_json(url)
            for event in data.get("events") or []:
                match_date = event_date(event)
                if match_date and not (start_date <= match_date <= end_date):
                    continue
                event_id = event.get("id") or event.get("uid")
                if event_id and event_id in seen:
                    continue
                match = event_to_match(event)
                if match:
                    if event_id:
                        seen.add(event_id)
                    matches.append(match)
        except Exception as exc:
            errors.append(str(exc))

    if matches:
        return {
            "updatedAt": datetime.now().astimezone().strftime("%H:%M:%S"),
            "source": "ESPN",
            "matches": matches[:20],
            "range": "yesterday_today_tomorrow",
            "queryDates": query_dates,
            "errors": errors,
        }

    if CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if cached.get("range") == "yesterday_today_tomorrow":
                return cached
        except Exception:
            pass

    return {
        "updatedAt": datetime.now().astimezone().strftime("%H:%M:%S"),
        "source": "Local",
        "range": "yesterday_today_tomorrow",
        "queryDates": query_dates,
        "matches": [
            {"teams": "等待世界杯赛程更新", "meta": "暂无近三天实时数据", "state": "pre"},
        ],
        "errors": errors[-3:],
    }


def write_dashboard_js(payload):
    OUT.write_text(
        "window.__WORLDCUP__ = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    if payload.get("source") != "Local":
        CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_once():
    payload = collect_matches()
    write_dashboard_js(payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Fetch World Cup scoreboard data for the dashboard.")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    while True:
        run_once()
        if not args.loop:
            return 0
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
