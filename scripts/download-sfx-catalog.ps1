param(
  [string]$Catalog = "catalog/sfx-catalog-200.json",
  [string]$Output = "downloaded-sfx",
  [string]$Category = ""
)

$ErrorActionPreference = "Stop"
$data = Get-Content -Raw -Encoding UTF8 $Catalog | ConvertFrom-Json
$items = $data.items
if ($Category) {
  $items = $items | Where-Object { $_.category -eq $Category }
}

New-Item -ItemType Directory -Force -Path $Output | Out-Null
$report = @()

foreach ($item in $items) {
  $url = $item.wav_url
  if (-not $url) { $url = $item.mp3_url }
  if (-not $url) { $url = $item.direct_url }
  if (-not $url) { $url = $item.preview_ogg_url }
  if (-not $url) { $url = $item.preview_mp3_url }
  if (-not $url) {
    $report += [pscustomobject]@{ id=$item.id; ok=$false; error="no_url" }
    continue
  }

  $uri = [uri]$url
  $ext = [IO.Path]::GetExtension($uri.AbsolutePath)
  if (-not $ext) { $ext = ".bin" }

  $dir = Join-Path $Output $item.category
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $safe = ($item.slug -replace '[^a-zA-Z0-9_-]', '-')
  $name = ("{0:D3}_{1}{2}" -f [int]$item.id, $safe, $ext)
  $dest = Join-Path $dir $name

  try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    Write-Host "OK  $($item.id)  $($item.category)  $name"
    $report += [pscustomobject]@{ id=$item.id; ok=$true; file=$dest }
  }
  catch {
    Write-Warning "FAIL $($item.id) $($item.slug): $($_.Exception.Message)"
    $report += [pscustomobject]@{ id=$item.id; ok=$false; error=$_.Exception.Message }
  }
}

$report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $Output "_download-report.json")
$ok = @($report | Where-Object { $_.ok }).Count
Write-Host "Downloaded $ok / $(@($items).Count)"
