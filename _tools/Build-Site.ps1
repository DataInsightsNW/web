<#
  Build-Site.ps1 — assembles the deployable site from _src/ into the repo root.

  _src/ is the source of truth. Everything this script writes to the repo root is
  GENERATED and will be overwritten on the next run. Never hand-edit a generated
  file — every one carries a "generated" banner on line 2.

  Run from anywhere:  .\_tools\Build-Site.ps1
#>
[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root   = Split-Path -Parent $PSScriptRoot
$Src    = Join-Path $Root '_src'
$Domain = 'https://datainsightsnorthwest.co.uk'

# Files at the repo root that this build owns. Anything else at the root is
# left strictly alone — CNAME and the Google verification file in particular.
$Protected = @('CNAME', 'googlea4b8db69c89cd24d.html', 'README.md', 'CLAUDE.md', '.git', '.gitignore')

function Write-Step($msg) { if (-not $Quiet) { Write-Host "  $msg" -ForegroundColor DarkGray } }

# Minimal attribute-safe encoder. Page metadata is authored by us, so this only
# has to be correct, not exhaustive — and it avoids depending on System.Web,
# which is not reliably loadable in PowerShell 7.
function ConvertTo-AttrSafe([string]$s) {
    if ($null -eq $s) { return '' }
    # Ampersands first, and only those not already opening an entity.
    $s = [regex]::Replace($s, '&(?!(#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);)', '&amp;')
    $s = $s.Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
    return $s
}

# ---------------------------------------------------------------- partials
$partials = @{}
foreach ($f in Get-ChildItem (Join-Path $Src 'partials') -Filter *.html) {
    $partials[$f.BaseName] = (Get-Content $f.FullName -Raw)
}
foreach ($need in 'head', 'header', 'footer', 'tail') {
    if (-not $partials.ContainsKey($need)) { throw "Missing partial: _src/partials/$need.html" }
}

# ---------------------------------------------------------------- analytics
# Cloudflare Web Analytics beacon. Emitted only when _src/analytics-token.txt
# exists and holds a token, so a half-configured build can never ship a broken
# script tag — and so the privacy notice's claims stay true either way.
#
# The token is not a secret: it is a public site identifier that appears in the
# page source by design, exactly like the Web3Forms access key.
#
# The site is NOT proxied through Cloudflare (the GitHub Pages DNS records are
# grey-cloud / DNS-only), so the automatic server-side version is unavailable
# and the JS beacon is the only option.
$tokenFile = Join-Path $Src 'analytics-token.txt'
$analytics = '<!-- analytics: not configured (no _src/analytics-token.txt) -->'
if (Test-Path $tokenFile) {
    $token = ((Get-Content $tokenFile -Raw) -replace '\s', '')
    if ($token -match '^[0-9a-f]{32}$') {
        $analytics = '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" ' +
                     "data-cf-beacon='{`"token`": `"$token`"}'></script>"
    }
    elseif ($token) {
        throw "analytics-token.txt does not look like a Cloudflare Web Analytics token (expected 32 hex characters, got $($token.Length) chars)"
    }
}

# ---------------------------------------------------------------- pages
$pageFiles = @(Get-ChildItem (Join-Path $Src 'pages') -Filter *.html -Recurse | Sort-Object FullName)
if (-not $pageFiles) { throw 'No pages found in _src/pages' }

$built = [System.Collections.Generic.List[object]]::new()

foreach ($pf in $pageFiles) {
    $raw = Get-Content $pf.FullName -Raw

    # Metadata block: an HTML comment at the top holding key: value lines.
    if ($raw -notmatch '(?s)^\s*<!--\s*(.*?)-->\s*(.*)$') {
        throw "$($pf.Name): missing leading <!-- key: value --> metadata block"
    }
    $metaText = $Matches[1]
    $content  = $Matches[2]

    $meta = @{}
    foreach ($line in $metaText -split "`r?`n") {
        if ($line -match '^\s*([a-zA-Z_]+)\s*:\s*(.*?)\s*$') { $meta[$Matches[1]] = $Matches[2] }
    }
    foreach ($need in 'title', 'description', 'slug', 'nav') {
        if (-not $meta.ContainsKey($need) -or [string]::IsNullOrWhiteSpace($meta[$need])) {
            throw "$($pf.Name): metadata '$need' is required"
        }
    }

    $slug = $meta['slug']
    if ($Protected -contains $slug) { throw "$($pf.Name): slug '$slug' collides with a protected file" }

    # Homepage canonical is the bare domain, not /index.html — otherwise the
    # homepage competes with itself in search.
    $canonical = if ($slug -eq 'index.html') { "$Domain/" } else { "$Domain/$slug" }

    # Optional per-page JSON-LD, held in _src/partials/schema-<name>.html
    $schema = ''
    if ($meta.ContainsKey('schema') -and $meta['schema']) {
        $key = "schema-$($meta['schema'])"
        if (-not $partials.ContainsKey($key)) { throw "$($pf.Name): no partial for schema '$($meta['schema'])'" }
        $schema = $partials[$key]
    }

    # Asset URLs are root-relative everywhere, so a page's folder depth does not
    # affect its links — pages can live in /insights/ without any path rewriting.
    $head = $partials['head']
    $head = $head.Replace('{{TITLE}}',       (ConvertTo-AttrSafe $meta['title']))
    $head = $head.Replace('{{DESCRIPTION}}', (ConvertTo-AttrSafe $meta['description']))
    $head = $head.Replace('{{CANONICAL}}',   $canonical)

    # A page kept out of the sitemap must also tell crawlers directly — the
    # sitemap is a hint, the meta tag is the instruction.
    $noindex = ($meta.ContainsKey('noindex') -and $meta['noindex'] -eq 'true')
    $head = $head.Replace('{{ROBOTS}}', $(if ($noindex) { 'noindex, follow' } else { 'index, follow, max-image-preview:large' }))
    $head = $head.Replace('{{OG_IMAGE}}',    "$Domain/assets/social-card.png")
    $head = $head.Replace('{{SCHEMA}}',      $schema)

    # Active nav item, resolved at build time so it works without JavaScript.
    # Marked with aria-current only — styling hangs off the attribute, so this
    # never has to merge with an existing class list (the CTA link has one).
    $header = $partials['header']
    $navKey = $meta['nav']
    $header = $header -replace "data-nav=`"$([regex]::Escape($navKey))`"", "data-nav=`"$navKey`" aria-current=`"page`""

    $html = @(
        '<!DOCTYPE html>'
        '<!-- GENERATED by _tools/Build-Site.ps1 from _src/ — do not edit this file directly. -->'
        '<html lang="en-GB">'
        $head
        '<body id="top">'
        $header
        $content.TrimEnd()
        $partials['footer']
        $partials['tail'].Replace('{{ANALYTICS}}', $analytics)
        '</body>'
        '</html>'
    ) -join "`n"

    if ($html -match '\{\{([A-Z_]+)\}\}') {
        throw "${slug}: unreplaced token {{$($Matches[1])}} — build aborted"
    }

    $out = Join-Path $Root $slug
    $dir = Split-Path -Parent $out
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($out, $html, (New-Object System.Text.UTF8Encoding $false))

    $built.Add([pscustomobject]@{
        Slug      = $slug
        Priority  = if ($meta.ContainsKey('priority')) { $meta['priority'] } else { '0.6' }
        NoIndex   = ($meta.ContainsKey('noindex') -and $meta['noindex'] -eq 'true')
        Canonical = $canonical
    })
    Write-Step "page  $slug"
}

# ---------------------------------------------------------------- assets
$assetsOut = Join-Path $Root 'assets'
if (-not (Test-Path $assetsOut)) { New-Item -ItemType Directory -Path $assetsOut -Force | Out-Null }
foreach ($f in Get-ChildItem (Join-Path $Src 'assets') -File) {
    Copy-Item $f.FullName (Join-Path $assetsOut $f.Name) -Force
    Write-Step "asset assets/$($f.Name)"
}

# Brand marks: favicon and logo stay at the root (conventional, and the live
# site already links them there); the rest go to assets/.
$brand = Join-Path $Src 'brand'
foreach ($f in Get-ChildItem $brand -File) {
    $dest = if ($f.Name -in 'favicon.svg', 'logo.svg') { Join-Path $Root $f.Name } else { Join-Path $assetsOut $f.Name }
    Copy-Item $f.FullName $dest -Force
    Write-Step "brand $($f.Name)"
}

foreach ($f in Get-ChildItem (Join-Path $Src 'static') -File) {
    Copy-Item $f.FullName (Join-Path $Root $f.Name) -Force
    Write-Step "static $($f.Name)"
}

# ---------------------------------------------------------------- sitemap
$today = (Get-Date).ToString('yyyy-MM-dd')
$urls = foreach ($p in ($built | Where-Object { -not $_.NoIndex } | Sort-Object { [double]$_.Priority } -Descending)) {
    "  <url>`n    <loc>$($p.Canonical)</loc>`n    <lastmod>$today</lastmod>`n    <changefreq>monthly</changefreq>`n    <priority>$($p.Priority)</priority>`n  </url>"
}
$sitemap = "<?xml version=`"1.0`" encoding=`"UTF-8`"?>`n<urlset xmlns=`"http://www.sitemaps.org/schemas/sitemap/0.9`">`n$($urls -join "`n")`n</urlset>`n"
[System.IO.File]::WriteAllText((Join-Path $Root 'sitemap.xml'), $sitemap, (New-Object System.Text.UTF8Encoding $false))
Write-Step "sitemap.xml ($($built.Count) pages, $(($built | Where-Object { -not $_.NoIndex }).Count) indexed)"

# The old flat stylesheet is superseded by assets/styles.css. Leave a copy in
# place so any external link or cached reference does not 404.
$legacy = Join-Path $Root 'styles.css'
if (Test-Path $legacy) {
    Copy-Item (Join-Path $Src 'assets/styles.css') $legacy -Force
    Write-Step 'styles.css (legacy path kept in sync)'
}

if (-not $Quiet) {
    Write-Host ''
    Write-Host "Built $($built.Count) pages -> $Root" -ForegroundColor Green
}
