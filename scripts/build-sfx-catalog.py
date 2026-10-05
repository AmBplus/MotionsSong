#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = Path("catalog/sfx-catalog-200.json")
BASE = "https://sfxmint.com/api/v1/search"

CATEGORIES = [
    {"id":"whoosh","count":18,"max_ms":2500,"queries":["whoosh","swoosh","air whoosh","short transition whoosh"]},
    {"id":"slide_swipe","count":18,"max_ms":2500,"queries":["slide","swipe","card slide","fast wipe","paper swipe"]},
    {"id":"click","count":18,"max_ms":1200,"queries":["ui click","button click","mouse click","interface click","soft click"]},
    {"id":"tick_check","count":14,"max_ms":1400,"queries":["tick","checkmark","confirm tick","checkbox","success tick"]},
    {"id":"pop_appear","count":12,"max_ms":1800,"queries":["pop","ui pop","element appear","soft pop","bubble pop"]},
    {"id":"ding_notification","count":10,"max_ms":2200,"queries":["ding","notification","chime","success notification"]},
    {"id":"impact_hit","count":14,"max_ms":3500,"queries":["impact","hit","cinematic impact","soft impact","punch hit"]},
    {"id":"boom_sub","count":8,"max_ms":5000,"queries":["boom","sub boom","cinematic boom","deep hit"]},
    {"id":"riser_reverse","count":10,"max_ms":6500,"queries":["riser","reverse swell","uplifter","reverse impact"]},
    {"id":"typing_keyboard","count":12,"max_ms":7000,"queries":["typing","keyboard typing","keypress","computer keyboard"]},
    {"id":"pencil_writing","count":12,"max_ms":7000,"queries":["pencil writing","pencil drawing","pencil scratch","handwriting pencil"]},
    {"id":"pen_marker_writing","count":10,"max_ms":7000,"queries":["pen writing","marker writing","felt pen","handwriting pen"]},
    {"id":"brush_drawing","count":10,"max_ms":7000,"queries":["brush stroke","paint brush","drawing brush","paint stroke"]},
    {"id":"scratch_scribble","count":8,"max_ms":5000,"queries":["scribble","paper scratch","scratch writing","rough drawing"]},
    {"id":"camera","count":8,"max_ms":4000,"queries":["camera shutter","camera click","camera focus","photo shutter"]},
    {"id":"digital_glitch","count":8,"max_ms":4000,"queries":["digital glitch","glitch transition","data glitch","technology beep"]},
    {"id":"logo_stinger","count":10,"max_ms":5500,"queries":["logo stinger","logo reveal","sonic logo","short intro sting","brand reveal"]},
]

def fetch_search(cat_id, q, max_ms):
    params = {
        "q": q, "limit": 20, "format": "wav",
        "max_duration_ms": max_ms, "response": "structured", "via": "skill"
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"MotionsSong-SFX-Catalog/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.load(r)
        rows = data if isinstance(data, list) else (data.get("candidates") or data.get("results") or [])
        return cat_id, q, rows
    except Exception as e:
        return cat_id, q, []

def qhint(row):
    a=row.get("acoustics") or {}
    attack=a.get("attack_ms"); tail=a.get("tail_ms")
    return {
        "attack_ms":attack, "tail_ms":tail, "centroid_hz":a.get("centroid_hz"),
        "character":a.get("character") or [],
        "short_transient": bool(attack is not None and tail is not None and attack<=120 and tail<=1200)
    }

jobs=[]
cat_by_id={c["id"]:c for c in CATEGORIES}
with ThreadPoolExecutor(max_workers=16) as ex:
    futures=[]
    for c in CATEGORIES:
        for q in c["queries"]:
            futures.append(ex.submit(fetch_search,c["id"],q,c["max_ms"]))
    for fut in as_completed(futures):
        jobs.append(fut.result())

rows_by_cat={c["id"]:[] for c in CATEGORIES}
seen_by_cat={c["id"]:set() for c in CATEGORIES}
for cat_id,q,rows in jobs:
    for row in rows:
        slug=row.get("slug")
        if not slug or not row.get("wav_url") or slug in seen_by_cat[cat_id]:
            continue
        if (row.get("license") or "").upper() not in ("CC0","CC0-1.0","CC0 1.0"):
            continue
        seen_by_cat[cat_id].add(slug)
        row["_matched_query"]=q
        rows_by_cat[cat_id].append(row)

used=set()
items=[]
for c in CATEGORIES:
    pool=rows_by_cat[c["id"]]
    pool.sort(key=lambda x:(float(x.get("score") or 0), -(int(x.get("duration_ms") or 999999))), reverse=True)
    picked=[]
    for row in pool:
        if row["slug"] in used:
            continue
        picked.append(row)
        used.add(row["slug"])
        if len(picked)>=c["count"]:
            break
    for row in picked:
        items.append({
            "id":len(items)+1, "category":c["id"], "slug":row["slug"],
            "title":row.get("title"), "matched_query":row.get("_matched_query"),
            "tags":row.get("tags") or [], "duration_ms":row.get("duration_ms"),
            "loopable":row.get("loopable"), "license":"CC0-1.0",
            "wav_url":row.get("wav_url"), "mp3_url":row.get("mp3_url"),
            "page_url":row.get("page_url"), "source":"SFXMint",
            "quality_hint":qhint(row)
        })

doc={
    "name":"MotionsSong 200 Essential Motion SFX",
    "generated_from":"SFXMint public CC0 API",
    "license_policy":"CC0-1.0 only",
    "download_priority":"wav_url",
    "requested_count":200,
    "count":len(items),
    "category_targets":{c["id"]:c["count"] for c in CATEGORIES},
    "category_actual":{},
    "items":items[:200],
}
for x in doc["items"]:
    doc["category_actual"][x["category"]]=doc["category_actual"].get(x["category"],0)+1
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
print("catalog items:",len(doc["items"]))
print(json.dumps(doc["category_actual"],indent=2))
