#!/usr/bin/env python3
"""Обогащение Telegram-ресурсов публичными данными t.me.

Вход: файл со ссылками/хэндлами (по одному в строке) или JSON-массив с полем handle.
Выход: JSON-массив записей.

Что достаём:
  t.me/<h>    -> status, kind (CHANNEL/GROUP), title, members/subscribers, description
  t.me/s/<h>  -> last_post_date, posts_7d, posts_30d  (работает только для каналов;
                 у групп публичной ленты нет — там эти поля остаются null)
"""
import json, re, subprocess, sys, html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
NOW = datetime.now(timezone.utc)

def norm(x):
    x = str(x or "").strip()
    x = re.sub(r"^https?://", "", x)
    x = re.sub(r"^(www\.)?(t|telegram)\.me/", "", x)
    x = re.sub(r"^s/", "", x)
    x = x.lstrip("@").rstrip("/")
    return x.split("?")[0]

def fetch(url):
    for _ in range(3):
        p = subprocess.run(["curl", "-sS", "-m", "30", "-A", UA, url], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout:
            return p.stdout
    return ""

def meta(h, key):
    m = re.search(r'<meta property="og:%s" content="([^"]*)"' % key, h)
    return html.unescape(m.group(1)) if m else ""

def enrich(handle):
    h = norm(handle)
    rec = {"handle": h, "url": f"https://t.me/{h}", "status": "NETFAIL", "kind": None,
           "title": None, "size": None, "description": None,
           "last_post_date": None, "posts_7d": None, "posts_30d": None}
    page = fetch(rec["url"])
    if not page:
        return rec
    title, desc = meta(page, "title"), meta(page, "description")
    extra_m = re.search(r'tgme_page_extra">([^<]*)', page)
    extra = extra_m.group(1) if extra_m else ""
    rec["title"], rec["description"] = title, desc[:400]
    if not title or title == f"Telegram: Contact @{h}":
        rec["status"] = "DEAD_OR_PRIVATE"
        return rec
    rec["status"] = "LIVE" if extra else "LIVE_NOCOUNT"
    if "subscriber" in extra:
        rec["kind"] = "CHANNEL"
    elif "member" in extra or "online" in extra:
        rec["kind"] = "GROUP"
    num = re.sub(r"\D", "", extra.split("subscriber")[0].split("member")[0]) if extra else ""
    rec["size"] = int(num) if num else None

    if rec["kind"] == "CHANNEL":
        feed = fetch(f"https://t.me/s/{h}")
        dates = []
        for m in re.finditer(r'<time datetime="([^"]+)"', feed):
            try:
                dates.append(datetime.fromisoformat(m.group(1).replace("Z", "+00:00")))
            except ValueError:
                pass
        if dates:
            rec["last_post_date"] = max(dates).date().isoformat()
            rec["posts_7d"] = sum(1 for d in dates if NOW - d <= timedelta(days=7))
            rec["posts_30d"] = sum(1 for d in dates if NOW - d <= timedelta(days=30))
    return rec

def main():
    raw = open(sys.argv[1], encoding="utf-8").read().strip()
    if raw.startswith("["):
        handles = [r.get("handle") or r.get("url") for r in json.loads(raw)]
    else:
        handles = [l for l in raw.splitlines() if l.strip()]
    handles = sorted({norm(x) for x in handles if norm(x) and re.fullmatch(r"[A-Za-z0-9_]{4,64}|\+[\w-]{8,64}|addlist/[\w-]{4,64}", norm(x))})
    sys.stderr.write(f"enriching {len(handles)} handles\n")
    with ThreadPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(enrich, handles))
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    live = sum(1 for r in out if r["status"].startswith("LIVE"))
    sys.stderr.write(f"live={live} dead={len(out)-live}\n")

if __name__ == "__main__":
    main()
