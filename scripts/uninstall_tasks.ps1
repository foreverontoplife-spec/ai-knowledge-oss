<# 删除 ai-knowledge 的两个定时任务。用法: powershell -ExecutionPolicy Bypass -File scripts\uninstall_tasks.ps1 [-DryRun] #>
param([switch]$DryRun)
foreach ($n in "ai-knowledge-local-import", "ai-knowledge-autopush") {
  if (-not (Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue)) { Write-Host "未找到 $n，跳过"; continue }
  if ($DryRun) { Write-Host "[DryRun] 将删除 $n"; continue }
  Unregister-ScheduledTask -TaskName $n -Confirm:$false; Write-Host "已删除 $n"
}