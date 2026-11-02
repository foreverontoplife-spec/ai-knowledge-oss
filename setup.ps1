<# ai-knowledge 一键安装
   用法: powershell -ExecutionPolicy Bypass -File setup.ps1 [-DryRun] [-NoTasks]
   -DryRun  只显示将要做什么，不做任何改动
   -NoTasks 不注册定时任务 #>
param([switch]$DryRun, [switch]$NoTasks)
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
Set-Location $repo
function Step($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }
function Do-It($desc, [scriptblock]$sb) { if ($DryRun) { Write-Host "[DryRun] $desc" } else { Write-Host $desc; & $sb } }

Step "1. 检查环境"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "未找到 Python。请从 https://www.python.org 安装 Python 3.9 或更高版本，安装时勾选 Add to PATH，然后重新运行。" -ForegroundColor Red; exit 1 }
$ver = (& python -c "import sys;print('%d.%d'%sys.version_info[:2])").Trim()
if ([version]$ver -lt [version]"3.9") { Write-Host "Python 版本是 $ver，需要 3.9 或更高版本。" -ForegroundColor Red; exit 1 }
Write-Host "Python $ver ✓"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "未找到 Git。请从 https://git-scm.com 安装后重新运行。" -ForegroundColor Red; exit 1 }
Write-Host "Git ✓"
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) { Write-Host "uv ✓" } else { Write-Host "未找到 uv（可选，basic-memory 需要）：powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Yellow }

Step "2. 安装依赖（requirements.txt）"
if ($uv) { Do-It "uv pip install --system -r requirements.txt" { uv pip install --system -r requirements.txt; if ($LASTEXITCODE) { python -m pip install --user -r requirements.txt } } }
else     { Do-It "python -m pip install --user -r requirements.txt" { python -m pip install --user -r requirements.txt } }

Step "3. 创建文件夹结构"
$dirs = @("sources\claude","sources\chatgpt","sources\deepseek","sources\grok","brain\0-Inbox","brain\1-Projects","brain\2-Areas","brain\3-Resources","brain\4-Archive",".ai_brain","scripts")
foreach ($d in $dirs) { if (-not (Test-Path $d)) { Do-It "创建 $d" { New-Item -ItemType Directory -Force $d | Out-Null } } }
Write-Host "文件夹结构 ✓"

Step "4. 定时任务"
if ($NoTasks) { Write-Host "已跳过（-NoTasks）" }
else { & (Join-Path $repo "scripts\install_tasks.ps1") -DryRun:$DryRun }

Step "5. 首次导入本机会话"
Do-It "python scripts\ai_brain.py --local" { $env:PYTHONIOENCODING = "utf-8"; python scripts\ai_brain.py --local }

Write-Host "`n完成。提醒：导入的对话是私人数据，你自己的仓库请设为 Private。" -ForegroundColor Green