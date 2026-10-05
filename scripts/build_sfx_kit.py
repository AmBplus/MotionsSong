#!/usr/bin/env python3
import json, math, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "sfx-categories.json"
OUT = ROOT / "sfx"
DIST = ROOT / "dist"
API = "https://freesound.org/apiv2/search/"
TOKEN = os.environ.get("FREESOUND_API_KEY", "").strip()

if not TOKEN:
    raise SystemExit("Missing FREESOUND_API_KEY")

def api_get(params):
    q = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(API + "?" + q, headers={"Authorization": f"Token {TOKEN}", "User-Agent":"MotionsSong-SFX-Kit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def safe_name(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70] or "sound"

def score(item, query, max_duration):
    sr = float(item.get("samplerate") or 0)
    bd = int(item.get("bitdepth") or 0)
    dur = float(item.get("duration") or 0)
    rating = float(item.get("avg_rating") or 0)
    ratings = int(item.get("num_ratings") or 0)
    downloads = int(item.get("num_downloads") or 0)
    ftype = (item.get("type") or "").lower()
    tags = " ".join(item.get("tags") or []).lower()
    name = (item.get("name") or "").lower()
    quality = 0
    quality += 2.0 if sr >= 48000 else 1.2 if sr >= 44100 else -1.0
    quality += 1.0 if bd >= 24 else 0.5 if bd >= 16 else 0
    quality += 0.8 if ftype in {"wav","flac","aif","aiff"} else 0
    quality += min(1.5, math.log10(downloads + 1) / 3)
    quality += min(1.0, rating / 5)
    quality += min(0.5, math.log10(ratings + 1) / 4)
    if dur <= 0 or dur > max_duration:
        quality -= 4
    qwords = [x for x in re.findall(r"[a-z0-9]+", query.lower()) if len(x) > 2]
    overlap = sum(1 for w in qwords if w in tags or w in name)
    quality += min(1.5, overlap * 0.5)
    return round(quality, 3)

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent":"MotionsSong-SFX-Kit/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f)

def ffprobe_ok(path):
    try:
        subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return True
    except Exception:
        return False

def main():
    cfg = json.loads(CONFIG.read_text())
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    DIST.mkdir(parents=True, exist_ok=True)
    chosen_ids = set()
    index = []
    sources = ["# MotionsSong SFX Sources\n", "All bundled sounds are selected as **Creative Commons 0** from Freesound.\n"]

    fields = "id,name,tags,username,license,duration,samplerate,bitdepth,channels,type,filesize,previews,avg_rating,num_ratings,num_downloads,url,description"

    for category, spec in cfg.items():
        catdir = OUT / category
        catdir.mkdir(parents=True, exist_ok=True)
        candidates = {}
        for query in spec["queries"]:
            data = api_get({
                "query": query,
                "filter": f'license:"Creative Commons 0" duration:[0.05 TO {spec["max_duration"]}] samplerate:[44100 TO *]',
                "sort": "downloads_desc",
                "fields": fields,
                "page_size": 60,
                "group_by_pack": 1
            })
            for item in data.get("results", []):
                if item["id"] in chosen_ids:
                    continue
                s = score(item, query, spec["max_duration"])
                old = candidates.get(item["id"])
                if not old or s > old[0]:
                    candidates[item["id"]] = (s, item, query)
            time.sleep(0.2)

        ranked = sorted(candidates.values(), key=lambda x: x[0], reverse=True)
        selected = []
        for s, item, query in ranked:
            if len(selected) >= spec["count"]:
                break
            previews = item.get("previews") or {}
            url = previews.get("preview-hq-ogg") or previews.get("preview-hq-mp3")
            if not url:
                continue
            ext = ".ogg" if "ogg" in url else ".mp3"
            filename = f"{category}_{len(selected)+1:02d}_{safe_name(item['name'])}_{item['id']}{ext}"
            path = catdir / filename
            try:
                download(url, path)
                if path.stat().st_size < 1500 or not ffprobe_ok(path):
                    path.unlink(missing_ok=True)
                    continue
            except Exception as e:
                print("download failed", item["id"], e, file=sys.stderr)
                path.unlink(missing_ok=True)
                continue

            chosen_ids.add(item["id"])
            selected.append(item)
            rec = {
                "category": category,
                "file": str(path.relative_to(ROOT)).replace("\\","/"),
                "semantic_label": safe_name(item["name"]),
                "freesound_id": item["id"],
                "source_url": item.get("url"),
                "author": item.get("username"),
                "license": item.get("license"),
                "duration": item.get("duration"),
                "original_type": item.get("type"),
                "original_samplerate": item.get("samplerate"),
                "original_bitdepth": item.get("bitdepth"),
                "channels": item.get("channels"),
                "avg_rating": item.get("avg_rating"),
                "num_ratings": item.get("num_ratings"),
                "num_downloads": item.get("num_downloads"),
                "tags": item.get("tags") or [],
                "selection_score": s,
                "matched_query": query,
                "asset_kind": "Freesound HQ preview",
                "preview_codec_note": "HQ OGG is ~192kbps; HQ MP3 fallback is ~128kbps"
            }
            index.append(rec)
            sources.append(f"- **{filename}** — Freesound #{item['id']} by {item.get('username')} — CC0 — {item.get('url')}\n")

        print(category, len(selected))

    (OUT / "sfx-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "SOURCES.md").write_text("".join(sources), encoding="utf-8")

    zbase = DIST / "MotionsSong-SFX-Kit"
    zpath = shutil.make_archive(str(zbase), "zip", ROOT, "sfx")
    print(f"Built {len(index)} sounds -> {zpath}")

if __name__ == "__main__":
    main()
