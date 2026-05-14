$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cacheDir = Join-Path $scriptDir ".npm-cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

$env:NPM_CONFIG_CACHE = $cacheDir
npx -y @modelcontextprotocol/inspector python (Join-Path $scriptDir "mcp_server.py")
