#!/usr/bin/env python3
"""Сборка каталога: кандидаты от discovery + факты с t.me -> chats.csv / chats.md."""
import json, csv, sys, re
from collections import defaultdict

cands = json.load(open(sys.argv[1], encoding="utf-8"))     # raw_candidates.json
facts = {r["handle"].lower(): r for r in json.load(open(sys.argv[2], encoding="utf-8"))}
out_csv, out_md = sys.argv[3], sys.argv[4]

def norm(x):
    x = str(x or "").strip()
    x = re.sub(r"^https?://", "", x)
    x = re.sub(r"^(www\.)?(t|telegram)\.me/", "", x)
    x = re.sub(r"^s/", "", x)
    return x.lstrip("@").rstrip("/").split("?")[0]

SEG_TITLE = {
    "it_orders": "IT-заказы и подряды",
    "infobiz": "Инфобиз, запуски, онлайн-школы",
    "leadgen": "Лидген, трафик, продажи",
    "business": "Бизнес-сообщества и отраслевые ниши",
}
USE_TITLE = {"take_orders": "берём заказы", "sell_pilot": "продаём пилот", "both": "и то и другое", "research": "исследование"}

rows = []
for c in cands:
    h = norm(c.get("handle") or c.get("url"))
    f = facts.get(h.lower(), {})
    status = f.get("status", "UNVERIFIED")
    rows.append({
        "handle": h,
        "url": f"https://t.me/{h}",
        "title": f.get("title") or c.get("title") or "",
        "kind": f.get("kind") or (c.get("kind") or "").upper(),
        "size": f.get("size") or "",
        "status": status,
        "segment": c.get("segment", ""),
        "subsegment": c.get("subsegment", ""),
        "use_case": c.get("use_case", ""),
        "last_post_date": f.get("last_post_date") or "",
        "posts_30d": f.get("posts_30d") if f.get("posts_30d") is not None else "",
        "confidence": c.get("confidence", ""),
        "why": (c.get("why") or "").replace("\n", " ").strip(),
        "source": c.get("source", ""),
    })

# дедуп: одна запись на handle, побеждает более информативная
best = {}
for r in rows:
    k = r["handle"].lower()
    prev = best.get(k)
    if not prev or (len(r["why"]) > len(prev["why"])):
        if prev:
            r["segment"] = prev["segment"] if prev["segment"] == r["segment"] else f'{prev["segment"]}+{r["segment"]}'
            if prev["use_case"] != r["use_case"]:
                r["use_case"] = "both"
        best[k] = r
rows = list(best.values())

def band(r):
    """Полоса по ПУБЛИЧНЫМ метаданным. Это прокси, а не ORDER_SCORE/PILOT_SCORE:
    настоящие сигналы спроса и боли видны только внутри чата."""
    size = r["size"] if isinstance(r["size"], int) else 0
    if r["kind"] == "CHANNEL":
        p30 = r["posts_30d"] if isinstance(r["posts_30d"], int) else None
        if p30 == 0:
            return "C"
        if p30 is not None and p30 >= 4 and size >= 1000:
            return "A"
        return "B"
    if r["kind"] == "GROUP":
        if size >= 1000:
            return "A"
        if size >= 200:
            return "B"
        return "C"
    return "B"

for r in rows:
    r["band"] = band(r) if str(r["status"]).startswith("LIVE") else ""

folders = [r for r in rows if r["handle"].startswith("addlist/")]
live = [r for r in rows if str(r["status"]).startswith("LIVE") and not r["handle"].startswith("addlist/")]
dead = [r for r in rows if not str(r["status"]).startswith("LIVE")]
BAND_ORDER = {"A": 0, "B": 1, "C": 2, "": 3}
live.sort(key=lambda r: (r["segment"], r["use_case"], BAND_ORDER[r["band"]],
                         -(r["size"] if isinstance(r["size"], int) else 0)))

fields = ["handle","url","title","kind","size","status","band","segment","subsegment","use_case",
          "last_post_date","posts_30d","confidence","why","source"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for r in live + folders + dead:
        w.writerow(r)

by_seg = defaultdict(lambda: defaultdict(list))
for r in live:
    by_seg[r["segment"].split("+")[0]][r["use_case"]].append(r)

L = []
L.append("# Каталог Telegram-сообществ\n")
L.append(f"Всего проверено ссылок: **{len(rows)}**. Живых на момент проверки: **{len(live)}**, "
         f"мёртвых или приватных: **{len(dead)}**.\n")
L.append("Числа участников и даты постов сняты с публичных страниц t.me скриптом `tools/verify_tg.sh` / `tools/enrich_tg.py`. "
         "У групп публичной ленты нет, поэтому `последний пост` заполнен только у каналов.\n")
L.append("**Полоса A/B/C здесь — прокси по публичным метаданным** (размер, свежесть постов), а не `ORDER_SCORE`/`PILOT_SCORE` "
         "из `playbook/scoring.md`: настоящие сигналы спроса и боли видны только внутри чата, после вступления. "
         "C у канала означает «ни одного поста за 30 дней», C у группы — меньше 200 участников.\n")
for seg in ["it_orders", "infobiz", "leadgen", "business"]:
    if seg not in by_seg:
        continue
    L.append(f"\n## {SEG_TITLE.get(seg, seg)}\n")
    for use in ["take_orders", "both", "sell_pilot", "research"]:
        items = by_seg[seg].get(use)
        if not items:
            continue
        L.append(f"\n### {USE_TITLE.get(use, use)} ({len(items)})\n")
        L.append("| П | Ресурс | Тип | Участников | Последний пост | Зачем нам |")
        L.append("|---|---|---|---:|---|---|")
        for r in items:
            name = (r["title"] or r["handle"]).replace("|", "/")[:60]
            L.append(f'| {r["band"]} | [{name}]({r["url"]}) `@{r["handle"]}` | {r["kind"] or "?"} | '
                     f'{r["size"] or "—"} | {r["last_post_date"] or "—"} | {r["why"][:150]} |')
if folders:
    L.append(f"\n## Папки-подборки t.me/addlist ({len(folders)})\n")
    L.append("Каждая ссылка добавляет в Telegram сразу пачку чатов. Число участников у папок не показывается — "
             "это ограничение самих страниц addlist, а не пропуск в данных.\n")
    L.append("| Папка | Сегмент | Зачем нам |")
    L.append("|---|---|---|")
    for r in folders:
        L.append(f'| [{(r["title"] or r["handle"]).replace("|","/")[:50]}]({r["url"]}) | {r["segment"]} | {r["why"][:130]} |')

if dead:
    L.append(f"\n## Не подтвердились ({len(dead)})\n")
    L.append("Публичной страницы нет: закрыт, переименован или удалён. Оставлены для истории, в работу не берём.\n")
    L.append("| Ресурс | Сегмент | Что о нём было известно |")
    L.append("|---|---|---|")
    for r in sorted(dead, key=lambda x: x["segment"]):
        L.append(f'| `@{r["handle"]}` | {r["segment"]} | {r["why"][:120]} |')
open(out_md, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"live={len(live)} dead={len(dead)} -> {out_csv}, {out_md}")
