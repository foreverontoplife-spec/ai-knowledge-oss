# 定时任务 ai-knowledge-local-import 入口：读取本机 AI 客户端会话 -> Markdown，然后调用 auto_push.ps1 提交推送
$repo = Split-Path -Parent $PSScriptRoot
$log = Join-Path $repo ".ai_brain\local_import.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"; [Console]::OutputEncoding = [Text.Encoding]::UTF8
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $log -Append -Encoding utf8
if (Get-Command uv -ErrorAction SilentlyContinue) { & uv run --no-project --quiet --with zstandard python scripts\ai_brain.py --local 2>&1 | Out-File $log -Append -Encoding utf8 }
else { & python scripts\ai_brain.py --local 2>&1 | Out-File $log -Append -Encoding utf8 }
"exit=$LASTEXITCODE" | Out-File $log -Append -Encoding utf8
& (Join-Path $PSScriptRoot "auto_push.ps1")
