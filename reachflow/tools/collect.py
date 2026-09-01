#!/usr/bin/env python3
import json, glob, os, re, sys
B = "/root/.claude/projects/-home-user-aidao-2025-bev-occupancy/1868feeb-ad0e-5524-90bd-11defbed3efa/subagents/workflows"
SEG = {"wf_65aab682-518": "it_orders", "wf_1937da62-ba7": "infobiz",
       "wf_c7c1ea5c-082": "leadgen", "wf_1b16031c-a17": "business"}
def norm(x):
    x = str(x or "").strip()
    x = re.sub(r"^https?://", "", x)
    x = re.sub(r"^(www\.)?(t|telegram)\.me/", "", x)
    x = re.sub(r"^s/", "", x)
    return x.lstrip("@").rstrip("/").split("?")[0]
pool, notes = {}, {}
for j in sorted(glob.glob(B + "/*/journal.jsonl")):
    run = os.path.basename(os.path.dirname(j))
    seg = SEG.get(run, run)
    notes.setdefault(seg, [])
    for line in open(j):
        try: d = json.loads(line)
        except Exception: continue
        if d.get("type") != "result": continue
        r = d.get("result")
        if not isinstance(r, dict): continue
        if r.get("notes"): notes[seg].append(r["notes"])
        for it in r.get("items") or []:
            h = norm(it.get("handle") or it.get("url"))
            if not h or not re.fullmatch(r"[A-Za-z0-9_]{4,64}|\+[\w-]{8,64}|addlist/[\w-]{4,64}", h):
                continue
            k = h.lower()
            it = {**it, "handle": h, "segment": seg}
            prev = pool.get(k)
            if not prev:
                pool[k] = it
            else:
                if len(it.get("why") or "") > len(prev.get("why") or ""):
                    it["segment"] = prev["segment"] if prev["segment"] == seg else prev["segment"] + "+" + seg
                    if prev.get("use_case") != it.get("use_case"): it["use_case"] = "both"
                    pool[k] = it
                elif prev["segment"] != seg and seg not in prev["segment"]:
                    prev["segment"] += "+" + seg
                    if prev.get("use_case") != it.get("use_case"): prev["use_case"] = "both"
json.dump(list(pool.values()), open("raw_pool.json", "w"), ensure_ascii=False, indent=1)
json.dump(notes, open("agent_notes.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print("уникальных:", len(pool))
print("по сегментам:", dict(Counter(v["segment"].split("+")[0] for v in pool.values())))
print("по use_case:", dict(Counter(v.get("use_case", "?") for v in pool.values())))
