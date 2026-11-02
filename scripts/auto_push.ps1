# 整个 ai-knowledge 仓库自动提交并推送（定时任务 ai-knowledge-autopush 每小时调用）
# 有改动才 commit；先 pull --rebase 再 push；日志写入 .ai_brain/auto_push.log（已 gitignore）
# 如设置了环境变量 HTTPS_PROXY（例如 http://127.0.0.1:7890），git 会自动走代理
$repo = Split-Path -Parent $PSScriptRoot
$log = Join-Path $repo ".ai_brain\auto_push.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function L($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File $log -Append -Encoding utf8 }
Set-Location $repo
$git = @()
if ($env:HTTPS_PROXY) { $git = @("-c", "http.proxy=$($env:HTTPS_PROXY)"); L "使用代理" }
try {
  git add -A 2>&1 | Out-Null
  git diff --cached --quiet
  if ($LASTEXITCODE -ne 0) {
    $out = git commit -q -m "auto: $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>&1
    if ($LASTEXITCODE -ne 0) { L "commit 失败: $out"; exit 1 }
    L "已提交"
  }
  $out = git @git pull --rebase --autostash -q origin main 2>&1
  if ($LASTEXITCODE -ne 0) { L "pull --rebase 失败: $out"; git rebase --abort 2>&1 | Out-Null; exit 2 }
  $ahead = git rev-list --count origin/main..HEAD
  if ([int]$ahead -gt 0) {
    $out = git @git push -q origin main 2>&1
    if ($LASTEXITCODE -ne 0) { L "push 失败（网络/代理?）: $out"; exit 3 }
    L "已推送 $ahead 个提交，HEAD=$(git rev-parse --short HEAD)"
  } else { L "无新内容" }
} catch { L "异常: $_"; exit 9 }
