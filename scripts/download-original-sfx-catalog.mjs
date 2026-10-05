#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";

const catalogPath = process.argv[2] ?? "catalog/sfx-catalog-originals-200.json";
const outDir = process.argv[3] ?? "downloaded-original-sfx";
const category = process.argv[4] ?? "";
const token = process.env.FREESOUND_ACCESS_TOKEN ?? "";
const concurrency = Math.max(1, Number(process.env.SFX_CONCURRENCY ?? 5));

const catalog = JSON.parse(await fs.readFile(catalogPath, "utf8"));
let items = catalog.items;
if (category) items = items.filter(x => x.category === category);

await fs.mkdir(outDir, {recursive:true});

function safe(s) {
  return String(s ?? "sound").toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g,"");
}

async function one(item) {
  const url = item?.original_file?.url;
  if (!url) return {id:item.id, ok:false, error:"missing original_file.url"};

  const headers = {};
  if (item.requires_oauth) {
    if (!token) return {id:item.id, ok:false, skipped:true, error:"FREESOUND_ACCESS_TOKEN required"};
    headers.Authorization = "Bearer " + token;
  }

  const res = await fetch(url, {headers, redirect:"follow"});
  if (!res.ok) throw new Error("HTTP " + res.status + " " + url);

  const disposition = res.headers.get("content-disposition") ?? "";
  let ext = (item.original_file.format ?? "").toLowerCase();
  if (ext === "wave") ext = "wav";
  if (!ext || ext.length > 6) {
    const u = new URL(res.url);
    const m = u.pathname.match(/\.([a-z0-9]{2,5})$/i);
    ext = m ? m[1].toLowerCase() : "bin";
  }

  const dir = path.join(outDir, safe(item.category));
  await fs.mkdir(dir, {recursive:true});
  const file = path.join(dir, String(item.id).padStart(3,"0") + "_" + safe(item.slug) + "." + ext);
  const buf = Buffer.from(await res.arrayBuffer());
  await fs.writeFile(file, buf);
  return {id:item.id, ok:true, file, bytes:buf.length, source:item.source};
}

let next = 0;
const results = [];
async function worker() {
  while (true) {
    const i = next++;
    if (i >= items.length) return;
    const item = items[i];
    try {
      const r = await one(item);
      results.push(r);
      if (r.ok) console.log("OK", item.id, item.category, item.slug);
      else console.log("SKIP", item.id, item.category, item.slug, r.error);
    } catch (e) {
      results.push({id:item.id, ok:false, error:String(e)});
      console.error("FAIL", item.id, item.slug, String(e));
    }
  }
}

await Promise.all(Array.from({length:concurrency}, worker));
await fs.writeFile(path.join(outDir, "_download-report.json"), JSON.stringify(results,null,2));

const ok = results.filter(x=>x.ok).length;
const skipped = results.filter(x=>x.skipped).length;
console.log("Downloaded " + ok + "/" + items.length + "; skipped " + skipped);
if (results.some(x=>!x.ok && !x.skipped)) process.exitCode = 2;
