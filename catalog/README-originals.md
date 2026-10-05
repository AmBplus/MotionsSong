# Original Master SFX Catalog

Main catalog: `catalog/sfx-catalog-originals-200.json`

## Guarantees

- 200 original/master audio entries
- No preview or low-quality URLs in this catalog
- 178 entries download directly without an API key or login
- 22 Freesound drawing/writing masters use the official OAuth2 original-download endpoint
- Full technical metadata is recorded where measurable: format, codec, sample rate, bit depth/sample format, channels, bitrate, size, duration
- SFXMint entries also include description, tags, attack/tail, spectral centroid, character labels, loop status, peaks URL and validation checks
- All entries are CC0 1.0

## Professional background sounds

A separate subset is available at `catalog/background-originals.json`.

It includes room tone, office/indoor ambience, city ambience, nature ambience, technology/server/electronic backgrounds, cinematic drones and public/crowd ambience.

## Download public originals

Node.js 20+:

```bash
node scripts/download-original-sfx-catalog.mjs
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download-original-sfx-catalog.ps1
```

Without a Freesound OAuth token, the downloader downloads the 178 public originals and reports the 22 OAuth-only master files as skipped.

## Download one category

Node:

```bash
node scripts/download-original-sfx-catalog.mjs catalog/sfx-catalog-originals-200.json downloaded-original-sfx bg_cinematic_drone
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download-original-sfx-catalog.ps1 -Category drawing_writing
```

## Freesound master originals

Freesound requires OAuth2 for the original uploaded file. Set an access token before running the downloader:

Linux/macOS:

```bash
export FREESOUND_ACCESS_TOKEN="..."
node scripts/download-original-sfx-catalog.mjs
```

PowerShell:

```powershell
$env:FREESOUND_ACCESS_TOKEN = "..."
powershell -ExecutionPolicy Bypass -File .\scripts\download-original-sfx-catalog.ps1
```

The API key alone is not sufficient for Freesound original downloads; the official original-download endpoint requires an OAuth2 bearer access token.
