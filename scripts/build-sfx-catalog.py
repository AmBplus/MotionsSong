#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from pathlib import Path

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

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"MotionsSong-SFX-Catalog/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)

def search(q, max_ms):
    params = {
        "q": q,
        "limit": 20,
        "format": "wav",
        "max_duration_ms": max_ms,
        "response": "structured",
        "via": "skill",
    }
    data = get(BASE + "?" + urllib.parse.urlencode(params))
    if isinstance(data, list):
        return data
    return data.get("candidates") or data.get("results") or []

def quality_hint(row):
    a = row.get("acoustics") or {}
    tail = a.get("tail_ms")
    centroid = a.get("centroid_hz")
    attack = a.get("attack_ms")
    return {
        "attack_ms": attack,
        "tail_ms": tail,
        "centroid_hz": centroid,
        "character": a.get("character") or [],
        "short_transient": bool(attack is not None and tail is not None and attack <= 120 and tail <= 1200),
    }

used = set()
items = []
for cat in CATEGORIES:
    pool = []
    seen_local = set()
    for q in cat["queries"]:
        try:
            rows = search(q, cat["max_ms"])
        except Exception:
            rows = []
        for row in rows:
            slug = row.get("slug")
            wav = row.get("wav_url")
            mp3 = row.get("mp3_url")
            if not slug or not wav or slug in used or slug in seen_local:
                continue
            if (row.get("license") or "").upper() not in ("CC0","CC0-1.0","CC0 1.0"):
                continue
            seen_local.add(slug)
            row["_matched_query"] = q
            pool.append(row)
    pool.sort(key=lambda x: (float(x.get("score") or 0), -(int(x.get("duration_ms") or 999999))), reverse=True)
    picked = pool[:cat["count"]]
    for row in picked:
        used.add(row["slug"])
        items.append({
            "id": len(items)+1,
            "category": cat["id"],
            "slug": row["slug"],
            "title": row.get("title"),
            "matched_query": row.get("_matched_query"),
            "tags": row.get("tags") or [],
            "duration_ms": row.get("duration_ms"),
            "loopable": row.get("loopable"),
            "license": "CC0-1.0",
            "wav_url": row.get("wav_url"),
            "mp3_url": row.get("mp3_url"),
            "page_url": row.get("page_url"),
            "source": "SFXMint",
            "quality_hint": quality_hint(row),
        })

if len(items) < 200:
    fallback_queries = ["transition","ui","notification","whoosh","click","impact","typing","drawing","camera","glitch","stinger","scratch"]
    for q in fallback_queries:
        if len(items) >= 200:
            break
        try:
            rows = search(q, 7000)
        except Exception:
            continue
        for row in rows:
            if len(items) >= 200:
                break
            slug=row.get("slug")
            if not slug or slug in used or not row.get("wav_url"):
                continue
            if (row.get("license") or "").upper() not in ("CC0","CC0-1.0","CC0 1.0"):
                continue
            used.add(slug)
            items.append({
                "id": len(items)+1,
                "category": "fallback_motion",
                "slug": slug,
                "title": row.get("title"),
                "matched_query": q,
                "tags": row.get("tags") or [],
                "duration_ms": row.get("duration_ms"),
                "loopable": row.get("loopable"),
                "license": "CC0-1.0",
                "wav_url": row.get("wav_url"),
                "mp3_url": row.get("mp3_url"),
                "page_url": row.get("page_url"),
                "source": "SFXMint",
                "quality_hint": quality_hint(row),
            })

doc = {
    "name": "MotionsSong 200 Essential Motion SFX",
    "generated_from": "SFXMint public CC0 API",
    "license_policy": "CC0-1.0 only",
    "download_priority": "wav_url",
    "count": len(items),
    "categories": {c["id"]: c["count"] for c in CATEGORIES},
    "items": items[:200],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {min(len(items),200)} items to {OUT}")
