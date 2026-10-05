# MotionsSong — 200 Essential Motion SFX Catalog

This folder contains a curated JSON catalog of 200 reusable motion-graphics sound effects.

## Coverage

- Whoosh: 18
- Slide / Swipe: 20
- Click: 20
- Tick / Check / Confirm: 20
- Pop / Element Appear: 10
- Ding / Notification: 10
- Impact / Hit: 14
- Boom / Sub: 8
- Riser / Reverse: 4
- Typing / Keyboard: 20
- Pencil Writing / Drawing: 12
- Pen / Marker Writing: 10
- Brush / Painting: 9
- Camera: 7
- Digital / Glitch: 6
- Logo / Brand Stinger: 12

All catalog items are CC0.

## Download all sounds

Requires Node.js 20+:

```bash
node scripts/download-sfx-catalog.mjs catalog/sfx-catalog-200.json downloaded-sfx
```

The downloader prefers URLs in this order:

1. `wav_url`
2. `mp3_url`
3. `direct_url`
4. `preview_ogg_url`
5. `preview_mp3_url`

It creates one folder per category and writes `_download-report.json` at the end.

### Download only a single URL manually

Every item in the JSON has a direct audio address. For example, with curl:

```bash
curl -L "DIRECT_URL_FROM_JSON" -o sound.wav
```

PowerShell:

```powershell
Invoke-WebRequest -Uri "DIRECT_URL_FROM_JSON" -OutFile "sound.wav"
```

## Source notes

- SFXMint entries provide permanent direct WAV/MP3 links.
- Kenney entries use direct raw GitHub CC0 asset links.
- Freesound drawing/writing entries use public OGG preview links for immediate direct download. The JSON also records the master recording specifications when known. Original master downloads on Freesound require login/OAuth.
- The catalog is metadata/QC curated. Not every file has been human-auditioned in final motion context, so the motion agent should preview candidate sounds before final render.
