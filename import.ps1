# 不带参数：扫描"下载"文件夹；带参数：只处理该文件。
# powershell -ExecutionPolicy Bypass -File import.ps1 [C:\path\export.zip]
param([string]$Export)
Set-Location $PSScriptRoot
git pull --rebase
if ($Export) { python scripts\ai_brain.py --file $Export.Trim('"') --push }
else { python scripts\ai_brain.py --push }
Read-Host "完成，回车关闭"
