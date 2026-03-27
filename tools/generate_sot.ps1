param(
    [string]$Root = "K:\DEVKIT\projects\adg-ops",
    [string]$Version = "beta4.0",
    [switch]$IncludeData
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "Root path not found: $Root"
}

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$snapshotsDir = Join-Path $rootPath "snapshots"

if (-not (Test-Path -LiteralPath $snapshotsDir)) {
    New-Item -ItemType Directory -Path $snapshotsDir | Out-Null
}

$outFile = Join-Path $snapshotsDir ("snapshotstateoftruth_{0}_{1}.txt" -f $Version, $timestamp)

$excludeDirs = @(
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "snapshots"
)

# Por defecto NO metemos /data para que el SOT no pese toneladas.
# Si quieres incluirlo, ejecuta con -IncludeData
if (-not $IncludeData) {
    $excludeDirs += "data"
}

$excludeFiles = @(
    ".DS_Store"
)

$includeExts = @(
    ".html", ".js", ".css", ".py", ".ps1", ".json", ".md", ".yml", ".yaml", ".txt"
)

function Test-SkipPath {
    param([string]$FullName)

    $parts = $FullName -split '[\\/]'
    foreach ($part in $parts) {
        if ($excludeDirs -contains $part) {
            return $true
        }
    }
    return $false
}

function Test-IncludeFile {
    param([System.IO.FileInfo]$File)

    if ($excludeFiles -contains $File.Name) {
        return $false
    }

    return $includeExts -contains $File.Extension.ToLower()
}

$files = Get-ChildItem -LiteralPath $rootPath -Recurse -File |
    Where-Object {
        -not (Test-SkipPath $_.FullName) -and (Test-IncludeFile $_)
    } |
    Sort-Object FullName

$header = @()
$header += "SOT VERSION: $Version"
$header += "GENERATED AT: $(Get-Date -Format s)"
$header += "ROOT: $rootPath"
$header += "INCLUDE DATA FOLDER: $($IncludeData.IsPresent)"
$header += "TOTAL FILES: $($files.Count)"
$header += ("=" * 100)
$header += ""

Set-Content -LiteralPath $outFile -Value $header -Encoding UTF8

foreach ($file in $files) {
    $relative = $file.FullName.Substring($rootPath.Length).TrimStart('\')
    $separator = "#" * 100

    Add-Content -LiteralPath $outFile -Value ""
    Add-Content -LiteralPath $outFile -Value $separator
    Add-Content -LiteralPath $outFile -Value ("FILE: {0}" -f $relative)
    Add-Content -LiteralPath $outFile -Value $separator
    Add-Content -LiteralPath $outFile -Value ""

    try {
        $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    }
    catch {
        try {
            $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding Default
        }
        catch {
            $content = "<<ERROR READING FILE: $($_.Exception.Message)>>"
        }
    }

    Add-Content -LiteralPath $outFile -Value $content
    Add-Content -LiteralPath $outFile -Value ""
    Add-Content -LiteralPath $outFile -Value ""
}

Write-Host ""
Write-Host "SOT created:" -ForegroundColor Green
Write-Host $outFile -ForegroundColor Cyan
Write-Host ""
Write-Host "Files included: $($files.Count)" -ForegroundColor Yellow
Write-Host "Data folder included: $($IncludeData.IsPresent)" -ForegroundColor Yellow