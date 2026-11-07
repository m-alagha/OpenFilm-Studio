@echo off
rem One-command development start for Windows (cmd or PowerShell). Requires uv and Node.js 22+.
cd /d "%~dp0.."
uv run --project backend --frozen --extra dev python scripts\dev.py %*
