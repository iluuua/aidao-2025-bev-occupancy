import json, subprocess, sys, time
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
def get(url):
    for _ in range(3):
        p = subprocess.run(["curl","-sS","-m","40","-A",UA,"-H","Accept: application/json",url],capture_output=True,text=True)
        if p.returncode==0 and p.stdout.strip().startswith("["):
            return json.loads(p.stdout)
        time.sleep(2)
    return []
rows={}
for lng in ["ru","en"]:
    for off in range(0,1000,100):
        data=get(f"https://combot.org/api/chart/{lng}?limit=100&offset={off}")
        if not data: break
        for d in data:
            u=(d.get("u") or "").strip()
            if not u: continue
            rows[u.lower()]={"handle":u,"title":d.get("t",""),"size":d.get("s"),"lang":d.get("l",""),"src_lang":lng}
        sys.stderr.write(f"{lng} off={off} total={len(rows)}\n")
        if len(data)<100: break
json.dump(list(rows.values()),open("combot_all.json","w"),ensure_ascii=False,indent=0)
print("collected", len(rows))
