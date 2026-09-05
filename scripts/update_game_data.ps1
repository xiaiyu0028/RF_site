[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateRange(5, 300)]
    [int]$Timeout = 60,
    [ValidateSet("off", "visitable", "all")]
    [string]$CitySites = "off",
    [ValidateRange(0.0, 5.0)]
    [double]$CitySitesDelay = 0.35
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) {
    $venvPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}

if ([string]::IsNullOrWhiteSpace($env:RF_EMAIL) -or [string]::IsNullOrWhiteSpace($env:RF_PASSWORD)) {
    throw "找不到 RF_EMAIL 或 RF_PASSWORD。請先在目前使用者環境設定帳號資訊。"
}

$arguments = @(
    (Join-Path $PSScriptRoot "update_game_data.py"),
    "--timeout",
    $Timeout
)
if ($DryRun) {
    $arguments += "--dry-run"
}
if ($CitySites -ne "off") {
    $arguments += @("--city-sites", $CitySites, "--city-sites-delay", $CitySitesDelay)
}

& $python @arguments
exit $LASTEXITCODE
