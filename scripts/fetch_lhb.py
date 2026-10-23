#!/usr/bin/env python3
"""拉取东方财富龙虎榜数据，写入 docs/data/ 供静态页面使用。

只用标准库。每个交易日一个 JSON（上榜明细 + 买入前五 + 卖出前五），
另有 index.json 列出可用日期。拉取失败时保留旧文件，不会把站点弄坏。

用法:
    python scripts/fetch_lhb.py            # 最近 2 个交易日
    python scripts/fetch_lhb.py --days 10  # 回补最近 10 个交易日
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# 页面里的「直连东财」用的是同一组字段，两边数据格式一致
DETAIL_COLS = ("SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_ID,EXPLANATION,EXPLAIN,"
               "CLOSE_PRICE,CHANGE_RATE,TURNOVERRATE,BILLBOARD_NET_AMT,"
               "BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_DEAL_AMT,"
               "ACCUM_AMOUNT,DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,FREE_MARKET_CAP,"
               "TRADE_MARKET")
SEAT_COLS = "TRADE_ID,SECURITY_CODE,OPERATEDEPT_NAME,BUY,SELL,NET"

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
EMPTY = 9201  # 东财「返回数据为空」


def get(params, tries=5):
    query = urllib.parse.urlencode({"source": "WEB", "client": "WEB", **params},
                                   safe="(),'=<>")
    req = urllib.request.Request(f"{API}?{query}", headers={
        "User-Agent": UA, "Referer": "https://data.eastmoney.com/"})
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # 网络抖动：退避重试
            if attempt == tries:
                raise
            wait = 3 * 2 ** (attempt - 1)
            print(f"  第 {attempt} 次失败 ({exc!r})，{wait}s 后重试", file=sys.stderr)
            time.sleep(wait)


def rows(report, columns, filt=None, sort=None):
    out, page = [], 1
    while True:
        params = {"reportName": report, "columns": columns,
                  "pageSize": 500, "pageNumber": page}
        if filt:
            params["filter"] = filt
        if sort:
            params["sortColumns"], params["sortTypes"] = sort
        body = get(params)
        result = body.get("result")
        if result is None:
            if body.get("code") == EMPTY:
                return out
            raise RuntimeError(f"{report}: {body.get('code')} {body.get('message')}")
        out += result["data"]
        if page >= result["pages"]:
            return out
        page += 1


def recent_dates(n):
    dates, page = [], 1
    while len(dates) <= n:  # 多拿一天，确保第 n 天是完整出现的
        body = get({"reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
                    "columns": "TRADE_DATE", "pageSize": 500, "pageNumber": page,
                    "sortColumns": "TRADE_DATE", "sortTypes": "-1"})
        data = (body.get("result") or {}).get("data") or []
        for r in data:
            d = r["TRADE_DATE"][:10]
            if d not in dates:
                dates.append(d)
        if not data or page >= body["result"]["pages"]:
            break
        page += 1
    return dates[:n]


def slim(row):
    """金额取整、比率保留 2 位，文件小一半。"""
    out = {}
    for k, v in row.items():
        if isinstance(v, float):
            v = round(v) if abs(v) >= 1000 else round(v, 2)
        out[k] = v
    return out


def fetch_day(date):
    f = f"(TRADE_DATE='{date}')"
    detail = rows("RPT_DAILYBILLBOARD_DETAILSNEW", DETAIL_COLS, f,
                  ("SECURITY_CODE,TRADE_ID", "1,1"))
    buy = rows("RPT_BILLBOARD_DAILYDETAILSBUY", SEAT_COLS, f,
               ("TRADE_ID,BUY", "1,-1"))
    sell = rows("RPT_BILLBOARD_DAILYDETAILSSELL", SEAT_COLS, f,
                ("TRADE_ID,SELL", "1,-1"))
    return {"detail": [slim(r) for r in detail],
            "buy": [slim(r) for r in buy],
            "sell": [slim(r) for r in sell]}


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed, failed = [], []

    for date in recent_dates(args.days):
        print(f"{date} ...", file=sys.stderr)
        try:
            day = fetch_day(date)
        except Exception as exc:
            print(f"  放弃 {date}: {exc!r}", file=sys.stderr)
            failed.append(date)
            continue
        path = DATA / f"{date}.json"
        old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if all(old.get(k) == day[k] for k in ("detail", "buy", "sell")):
            print("  无变化", file=sys.stderr)
            continue
        write_json(path, {"date": date, "updated": now, **day})
        changed.append(date)
        print(f"  已更新: {len(day['detail'])} 条上榜", file=sys.stderr)

    dates = []
    for p in sorted(DATA.glob("????-??-??.json"), reverse=True):
        day = json.loads(p.read_text(encoding="utf-8"))
        dates.append({"d": day["date"], "u": day["updated"],
                      "n": len({r["SECURITY_CODE"] for r in day["detail"]})})
    write_json(DATA / "index.json", {"checked": now, "dates": dates})

    print(f"变化: {changed or '无'}  失败: {failed or '无'}", file=sys.stderr)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"changed={'1' if changed else ''}\n")
    # 全部失败才算失败；部分失败时站点照常用旧数据
    if failed and not changed and len(failed) == len(dates or failed):
        sys.exit(1)


if __name__ == "__main__":
    main()
