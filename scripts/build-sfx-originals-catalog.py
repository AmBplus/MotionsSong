#!/usr/bin/env python3
import json, os, re, subprocess, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("catalog/sfx-catalog-originals-250.json")
BASE = "https://sfxmint.com/api/v1"
UA = {"User-Agent":"MotionsSong-Original-SFX-Catalog/1.0"}

CATEGORIES = [
  {"id":"whoosh","count":18,"max_ms":3000,"queries":["whoosh","swoosh","air whoosh","transition whoosh"]},
  {"id":"slide_swipe","count":18,"max_ms":3000,"queries":["slide","swipe","wipe","card slide","paper swipe"]},
  {"id":"click","count":18,"max_ms":1500,"queries":["ui click","button click","mouse click","interface click"]},
  {"id":"tick_check","count":15,"max_ms":1800,"queries":["tick","checkmark","confirm","checkbox success"]},
  {"id":"pop_appear","count":10,"max_ms":2000,"queries":["pop","ui pop","element appear","soft pop"]},
  {"id":"ding_notification","count":8,"max_ms":2500,"queries":["ding","notification","chime","success cue"]},
  {"id":"impact_hit","count":12,"max_ms":4000,"queries":["impact","hit","cinematic impact","soft impact"]},
  {"id":"boom_sub","count":8,"max_ms":6000,"queries":["boom","sub boom","cinematic boom","deep impact"]},
  {"id":"riser_reverse","count":8,"max_ms":7000,"queries":["riser","reverse swell","uplifter","reverse impact"]},
  {"id":"typing_keyboard","count":12,"max_ms":9000,"queries":["typing","keyboard typing","keypress","mechanical keyboard"]},
  {"id":"drawing_writing","count":12,"max_ms":10000,"queries":["pen writing","writing on paper","scribble","marker writing","pencil","drawing"]},
  {"id":"camera","count":6,"max_ms":5000,"queries":["camera shutter","camera focus","camera zoom","photo shutter"]},
  {"id":"digital_glitch","count":7,"max_ms":5000,"queries":["digital glitch","glitch transition","data glitch","technology beep"]},
  {"id":"logo_stinger","count":8,"max_ms":6000,"queries":["logo stinger","brand reveal","sonic logo","short intro sting"]},

  {"id":"bg_room_tone","count":10,"max_ms":30000,"queries":["room tone","interior ambience","quiet room","indoor ambience"]},
  {"id":"bg_office","count":10,"max_ms":30000,"queries":["office ambience","office room","computer office","workspace ambience"]},
  {"id":"bg_city","count":10,"max_ms":30000,"queries":["city ambience","urban ambience","street ambience","traffic ambience"]},
  {"id":"bg_nature","count":12,"max_ms":30000,"queries":["forest ambience","rain ambience","ocean ambience","wind ambience","nature ambience"]},
  {"id":"bg_technology","count":10,"max_ms":30000,"queries":["technology hum","server room","electronic ambience","machine hum","computer hum"]},
  {"id":"bg_cinematic_drone","count":10,"max_ms":30000,"queries":["cinematic drone","dark drone","ambient drone","tension drone"]},
  {"id":"bg_atmosphere_texture","count":10,"max_ms":30000,"queries":["atmosphere","ambient texture","cinematic atmosphere","soundscape texture"]},
  {"id":"bg_crowd_public","count":8,"max_ms":30000,"queries":["crowd ambience","public space ambience","cafe ambience","mall ambience"]},
]

def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def search(cat, q, max_ms):
    params = {
      "q":q, "limit":30, "format":"wav", "max_duration_ms":max_ms,
      "response":"structured", "via":"skill"
    }
    try:
        data = get_json(BASE + "/search?" + urllib.parse.urlencode(params))
        rows = data if isinstance(data, list) else (data.get("candidates") or data.get("results") or [])
        return cat,q,rows
    except Exception:
        return cat,q,[]

def get_detail(slug):
    try:
        return get_json(BASE + "/sounds/" + urllib.parse.quote(slug) + "?via=skill")
    except Exception:
        return {}

def ffprobe(url):
    cmd = [
      "ffprobe","-v","error","-show_entries",
      "format=duration,size,bit_rate,format_name:stream=codec_name,codec_type,sample_rate,channels,bits_per_sample,sample_fmt,bit_rate",
      "-of","json",url
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return {}
        j = json.loads(p.stdout or "{}")
        audio = next((x for x in j.get("streams",[]) if x.get("codec_type")=="audio"), {})
        fmt = j.get("format") or {}
        return {
          "format_name":fmt.get("format_name"),
          "codec":audio.get("codec_name"),
          "sample_rate_hz":int(audio.get("sample_rate") or 0) or None,
          "channels":audio.get("channels"),
          "bits_per_sample":audio.get("bits_per_sample") or None,
          "sample_fmt":audio.get("sample_fmt"),
          "bit_rate_bps":int(audio.get("bit_rate") or fmt.get("bit_rate") or 0) or None,
          "size_bytes":int(fmt.get("size") or 0) or None,
          "duration_sec":round(float(fmt.get("duration") or 0),3) if fmt.get("duration") else None,
        }
    except Exception:
        return {}

# search in parallel
results=[]
with ThreadPoolExecutor(max_workers=18) as ex:
    futs=[ex.submit(search,c["id"],q,c["max_ms"]) for c in CATEGORIES for q in c["queries"]]
    for f in as_completed(futs):
        results.append(f.result())

bycat={c["id"]:[] for c in CATEGORIES}
seen_bycat={c["id"]:set() for c in CATEGORIES}
for cat,q,rows in results:
    for row in rows:
        slug=row.get("slug")
        wav=row.get("wav_url")
        lic=(row.get("license") or "").upper()
        if not slug or not wav or slug in seen_bycat[cat] or lic not in ("CC0","CC0-1.0","CC0 1.0"):
            continue
        if "preview" in wav.lower() or "-lq." in wav.lower():
            continue
        seen_bycat[cat].add(slug)
        row["_matched_query"]=q
        bycat[cat].append(row)

used=set()
picked=[]
for c in CATEGORIES:
    rows=bycat[c["id"]]
    rows.sort(key=lambda x:(float(x.get("score") or 0), -(int(x.get("duration_ms") or 99999999))), reverse=True)
    n=0
    for row in rows:
        if row["slug"] in used: continue
        used.add(row["slug"])
        picked.append((c,row))
        n+=1
        if n>=c["count"]: break

# details + ffprobe in parallel
details={}
with ThreadPoolExecutor(max_workers=16) as ex:
    futs={ex.submit(get_detail,row["slug"]):row["slug"] for _,row in picked}
    for f in as_completed(futs):
        details[futs[f]]=f.result()

technical={}
with ThreadPoolExecutor(max_workers=10) as ex:
    futs={ex.submit(ffprobe,row["wav_url"]):row["slug"] for _,row in picked}
    for f in as_completed(futs):
        technical[futs[f]]=f.result()

items=[]
for c,row in picked:
    slug=row["slug"]; d=details.get(slug) or {}; t=technical.get(slug) or {}
    acoustics=d.get("acoustics") or row.get("acoustics") or {}
    item={
      "id":len(items)+1,
      "category":c["id"],
      "slug":slug,
      "title":d.get("title") or row.get("title"),
      "description":d.get("description"),
      "semantic_use":[c["id"]],
      "matched_query":row.get("_matched_query"),
      "tags":d.get("tags") or row.get("tags") or [],
      "source":"SFXMint",
      "source_page":d.get("page_url") or row.get("page_url"),
      "license":"CC0-1.0",
      "original_file":{
        "url":d.get("wav_url") or row.get("wav_url"),
        "format":"WAV",
        **t
      },
      "alternate_mp3_url":d.get("mp3_url") or row.get("mp3_url"),
      "duration_ms":d.get("duration_ms") or row.get("duration_ms"),
      "loopable":d.get("loopable",row.get("loopable")),
      "loop_status":d.get("loop_status"),
      "acoustics":{
        "attack_ms":acoustics.get("attack_ms"),
        "tail_ms":acoustics.get("tail_ms"),
        "centroid_hz":acoustics.get("centroid_hz"),
        "character":acoustics.get("character") or []
      },
      "peaks_url":d.get("peaks_url"),
      "family":d.get("family"),
      "family_url":d.get("family_url"),
      "checks":d.get("checks") or row.get("checks"),
      "metadata_source":"SFXMint full sound metadata + ffprobe of original WAV",
      "is_original_master":True,
      "requires_api_key":False,
      "requires_login":False
    }
    items.append(item)

actual={}
for x in items: actual[x["category"]]=actual.get(x["category"],0)+1
doc={
  "name":"MotionsSong Original Master SFX + Background Catalog",
  "version":"2026-10-05-originals-v1",
  "policy":{
    "original_files_only":True,
    "no_previews":True,
    "direct_download_without_key":True,
    "license":"CC0-1.0 only"
  },
  "requested_count":sum(c["count"] for c in CATEGORIES),
  "count":len(items),
  "category_targets":{c["id"]:c["count"] for c in CATEGORIES},
  "category_actual":actual,
  "items":items
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
print("count",len(items))
print(json.dumps(actual,indent=2))
