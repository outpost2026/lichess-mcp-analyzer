#wrapper for MCP serving - reads .env from project root and forwards env vars
param()
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)\s*$") {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -and -not [Environment]::GetEnvironmentVariable($k, "Process")) {
                [Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
& $python -X utf8 -m lichess_analyzer_mcp.server
