<# 注册 ai-knowledge 的两个每小时定时任务（用户级，无需管理员，后台隐藏运行）
   ai-knowledge-local-import  每小时 :05  导入本机新对话
   ai-knowledge-autopush      每小时 :35  提交并推送到 GitHub
   用法: powershell -ExecutionPolicy Bypass -File scripts\install_tasks.ps1 [-DryRun] #>
param([switch]$DryRun)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$tasks = @(
  @{ Name = "ai-knowledge-local-import"; Script = "run_local_import.ps1"; Minute = 5 },
  @{ Name = "ai-knowledge-autopush";     Script = "auto_push.ps1";        Minute = 35 }
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
foreach ($t in $tasks) {
  $file = Join-Path $PSScriptRoot $t.Script
  if (-not (Test-Path $file)) { throw "找不到脚本: $file" }
  $arg = "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$file`""
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $repo
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes($t.Minute) -RepetitionInterval (New-TimeSpan -Hours 1)
  if ($DryRun) { Write-Host "[DryRun] 将注册 $($t.Name)：每小时 :$('{0:D2}' -f $t.Minute)，powershell.exe $arg"; continue }
  Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
  Write-Host "已注册 $($t.Name)（每小时 :$('{0:D2}' -f $t.Minute)）"
}
if (-not $DryRun) { Write-Host "查看：Get-ScheduledTask ai-knowledge-* | Get-ScheduledTaskInfo" }