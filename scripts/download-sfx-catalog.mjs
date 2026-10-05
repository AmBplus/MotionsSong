#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";

const catalogPath = process.argv[2] ?? "catalog/sfx-catalog-200.json";
const outDir = process.argv[3] ?? "downloaded-sfx";
const concurrency = Math.max(1, Number(process.env.SFX_CONCURRENCY ?? 6));

const catalog = JSON.parse(await fs.readFile(catalogPath, "utf8"));
await fs.mkdir(outDir, {recursive:true});

function safe(s) {
  return String(s ?? "sound").toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g,"");
}

async function downloadOne(item) {
  const url = item.wav_url || item.mp3_url || item.direct_url || item.preview_ogg_url || item.preview_mp3_url;
  if (!url) return {id:item.id, ok:false, error:"no_url"};
  const cleanUrl = url.split("?")[0];
  const m = cleanUrl.match(/\.(wav|mp3|ogg|aif|aiff|m4a)$/i);
  const ext = m ? "." + m[1].toLowerCase() : ".bin";
  const dir = path.join(outDir, safe(item.category));
  await fs.mkdir(dir, {recursive:true});
  const file = path.join(dir, String(item.id).padStart(3,"0") + "_" + safe(item.slug) + ext);
  const res = await fetch(url);
  if (!res.ok) throw new Error("HTTP " + res.status + " " + url);
  const buf = Buffer.from(await res.arrayBuffer());
  await fs.writeFile(file, buf);
  return {id:item.id, ok:true, file, bytes:buf.length};
}

let next = 0;
const results = [];
async function worker() {
  while (true) {
    const i = next++;
    if (i >= catalog.items.length) return;
    const item = catalog.items[i];
    try {
      const r = await downloadOne(item);
      results.push(r);
      console.log("OK", item.id, item.category, item.slug);
    } catch (e) {
      results.push({id:item.id, ok:false, error:String(e)});
      console.error("FAIL", item.id, item.slug, String(e));
    }
  }
}

await Promise.all(Array.from({length:concurrency}, worker));
await fs.writeFile(path.join(outDir, "_download-report.json"), JSON.stringify(results,null,2));
const ok = results.filter(x=>x.ok).length;
console.log("Downloaded " + ok + "/" + catalog.items.length);
if (ok !== catalog.items.length) process.exitCode = 2;
