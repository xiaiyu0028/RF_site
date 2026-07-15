[CmdletBinding()]
param(
    [string]$TaskName = "RF Site Data Update",
    [ValidateRange(5, 300)]
    [int]$Timeout = 60
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runnerScript = Join-Path $PSScriptRoot "update_game_data.ps1"
$currentUser = "{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME

if (-not (Test-Path $runnerScript)) {
    throw "找不到本機更新腳本：$runnerScript"
}

$actionArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`" -Timeout $Timeout"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArguments
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At 6:17PM
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

$taskParameters = @{
    TaskName = $TaskName
    Action = $action
    Trigger = $trigger
    Principal = $principal
    Settings = $settings
    Description = "更新 RF 攻略網站的國策與城鎮資料；不會 commit 或 push。"
    Force = $true
}
Register-ScheduledTask @taskParameters | Out-Null

Write-Host "已建立工作排程器：$TaskName（每週三 18:17，以 $currentUser 登入時執行）。"
Write-Host "請確認 RF_EMAIL 與 RF_PASSWORD 是此使用者的持久環境變數。"
