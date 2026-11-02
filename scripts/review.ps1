# 审阅待导入的对话：自动导入先进 pending/，你看过之后再移入 sources/
#   powershell -File scripts\review.ps1                     # 列出待审阅文件
#   powershell -File scripts\review.ps1 -Approve all        # 全部通过 -> sources/（同路径；已有旧版本则替换）
#   powershell -File scripts\review.ps1 -Approve pending\claude\2026\2026-11\x.md
#   powershell -File scripts\review.ps1 -Reject  pending\grok\2026\2026-11\y.md   # 移到 pending\_rejected（保留，不会再被导入）
# 移动后由每小时的 auto_push 一起提交推送；也可以手动 git add -A 再提交。
param([string]$Approve, [string]$Reject, [string]$Repo = (Split-Path -Parent $PSScriptRoot))
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$pending = Join-Path $Repo "pending"; $sources = Join-Path $Repo "sources"; $rejected = Join-Path $pending "_rejected"
function Rel($p) { $p.Substring($pending.Length + 1) }
function Pending { if (Test-Path $pending) { Get-ChildItem $pending -Recurse -File -Filter *.md | ? { -not $_.FullName.StartsWith($rejected + "\") } } }
function Resolve($x) {
  if ($x -eq "all") { return Pending }
  $p = if ([IO.Path]::IsPathRooted($x)) { $x } else { Join-Path $Repo $x }
  if (-not (Test-Path $p)) { $p = Join-Path $pending $x }
  if (-not (Test-Path $p)) { Write-Host "找不到: $x"; exit 1 }
  $f = Get-Item $p
  if (-not $f.FullName.StartsWith($pending + "\")) { Write-Host "只能处理 pending\ 里的文件: $x"; exit 1 }
  if ($f.PSIsContainer) { return Get-ChildItem $f.FullName -Recurse -File -Filter *.md | ? { -not $_.FullName.StartsWith($rejected + "\") } }
  $f
}
function MoveTo($f, $root) {
  $dest = Join-Path $root (Rel $f.FullName); $upd = Test-Path $dest
  New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
  Move-Item -LiteralPath $f.FullName $dest -Force
  "{0} {1}" -f ($(if ($upd) { "更新" } else { "新增" })), $dest.Substring($Repo.Length + 1)
}
if ($Approve) { $n = 0; foreach ($f in @(Resolve $Approve)) { MoveTo $f $sources; $n++ }; "通过 $n 个 -> sources\"; exit 0 }
if ($Reject)  { $n = 0; foreach ($f in @(Resolve $Reject))  { MoveTo $f $rejected; $n++ }; "拒绝 $n 个 -> pending\_rejected\"; exit 0 }
$list = @(Pending)
if (-not $list) { "没有待审阅的对话"; exit 0 }
"待审阅 $($list.Count) 个（标 * 的是 sources\ 里已有对话的新版本）："
foreach ($f in $list) {
  $rel = Rel $f.FullName; $mark = if (Test-Path (Join-Path $sources $rel)) { "*" } else { " " }
  $title = (Select-String -LiteralPath $f.FullName -Pattern '^title: ' -List).Line -replace '^title: ', ''
  " $mark pending\$rel  $title"
}