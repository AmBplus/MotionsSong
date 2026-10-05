param(
  [string]$Catalog = "catalog/sfx-catalog-originals-200.json",
  [string]$Output = "downloaded-original-sfx",
  [string]$Category = ""
)

$ErrorActionPreference = "Stop"
$data = Get-Content -Raw -Encoding UTF8 $Catalog | ConvertFrom-Json
$items = @($data.items)
if ($Category) {
  $items = @($items | Where-Object { $_.category -eq $Category })
}

$token = $env:FREESOUND_ACCESS_TOKEN
New-Item -ItemType Directory -Force -Path $Output | Out-Null
$report = @()

foreach ($item in $items) {
  $url = $item.original_file.url
  if (-not $url) {
    $report += [pscustomobject]@{ id=$item.id; ok=$false; error="missing original_file.url" }
    continue
  }

  $headers = @{}
  if ($item.requires_oauth) {
    if (-not $token) {
      Write-Host "SKIP $($item.id) $($item.slug) - FREESOUND_ACCESS_TOKEN required"
      $report += [pscustomobject]@{ id=$item.id; ok=$false; skipped=$true; error="FREESOUND_ACCESS_TOKEN required" }
      continue
    }
    $headers["Authorization"] = "Bearer $token"
  }

  $ext = ($item.original_file.format + "").ToLower()
  if ($ext -eq "wave") { $ext = "wav" }
  if (-not $ext) { $ext = "bin" }

  $dir = Join-Path $Output $item.category
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $safe = ($item.slug -replace '[^a-zA-Z0-9_-]', '-')
  $name = ("{0:D3}_{1}.{2}" -f [int]$item.id, $safe, $ext)
  $dest = Join-Path $dir $name

  try {
    Invoke-WebRequest -Uri $url -Headers $headers -OutFile $dest -UseBasicParsing
    Write-Host "OK   $($item.id) $($item.category) $name"
    $report += [pscustomobject]@{ id=$item.id; ok=$true; file=$dest; source=$item.source }
  }
  catch {
    Write-Warning "FAIL $($item.id) $($item.slug): $($_.Exception.Message)"
    $report += [pscustomobject]@{ id=$item.id; ok=$false; error=$_.Exception.Message }
  }
}

$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Output "_download-report.json")
$ok = @($report | Where-Object { $_.ok }).Count
$skipped = @($report | Where-Object { $_.skipped }).Count
Write-Host "Downloaded $ok / $($items.Count); skipped $skipped"
