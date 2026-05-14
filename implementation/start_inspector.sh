#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$ROOT_DIR/.npm-cache"
NPM_CONFIG_CACHE="$ROOT_DIR/.npm-cache" npx -y @modelcontextprotocol/inspector python "$ROOT_DIR/mcp_server.py"
