# 定时任务 ai-knowledge-local-import 入口（每小时 :05）：
#   1) 读取本机 AI 客户端会话 + 自动扫描 ~/Downloads 和 .inbox 里的官方导出 -> pending/（待审阅）
#   2) 把已审阅的 sources/ 同步到搜索镜像（basic-memory 项目 ai-sources）
#   3) AI 摘要（默认关闭，ai_brain_config.json enable_summarize=true 才运行，只处理 sources/）
#   4) 调用 auto_push.ps1 提交推送
$repo = Split-Path -Parent $PSScriptRoot
$log = Join-Path $repo ".ai_brain\local_import.log"
New-Item -ItemType Directory -Force (Split-Path $log), (Join-Path $repo ".inbox") | Out-Null
Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"; [Console]::OutputEncoding = [Text.Encoding]::UTF8
function Py { if (Get-Command uv -ErrorAction SilentlyContinue) { & uv run --no-project --quiet --with zstandard python @args 2>&1 } else { & python @args 2>&1 } }
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $log -Append -Encoding utf8
Py scripts\ai_brain.py --local --exports | Out-File $log -Append -Encoding utf8
$rc = $LASTEXITCODE; "exit=$rc" | Out-File $log -Append -Encoding utf8
Py scripts\mirror_sources.py | Out-File $log -Append -Encoding utf8
Py scripts\summarize.py --auto | Out-File $log -Append -Encoding utf8
& (Join-Path $PSScriptRoot "auto_push.ps1")