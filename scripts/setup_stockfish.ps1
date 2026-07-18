param(
    [string]$Variant = "sse41-popcnt"
)

$Repo = "https://github.com/official-stockfish/Stockfish/releases/download/sf_18"
$ZipFile = "$env:TEMP\stockfish.zip"
$Target = Join-Path -Path $PSScriptRoot -ChildPath "..\stockfish"

if (-not (Test-Path -LiteralPath $Target)) {
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
}

$Url = "$Repo/stockfish-windows-x86-64-$Variant.zip"
Write-Output "Stahuji Stockfish 18 ($Variant)..."
Write-Output "URL: $Url"

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($Url, $ZipFile)
    Write-Output "OK: $((Get-Item $ZipFile).Length) bytes"
    Expand-Archive -Path $ZipFile -DestinationPath "$env:TEMP\stockfish_extract" -Force
    Copy-Item -Path "$env:TEMP\stockfish_extract\stockfish\stockfish-windows-x86-64-$Variant.exe" -Destination (Join-Path $Target "stockfish.exe") -Force
    Write-Output "Stockfish ready: $(Join-Path $Target 'stockfish.exe')"
    Remove-Item -Path $ZipFile -Force
    Remove-Item -Path "$env:TEMP\stockfish_extract" -Recurse -Force
} catch {
    Write-Error "Selhalo: $($_.Exception.Message)"
    exit 1
}
