[CmdletBinding()]
param(
    [string]$MessagePrefix = "chore(data): update game data"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$dataFiles = @(
    "return_data_example/nation.json",
    "return_data_example/cities.json",
    "return_data_example/update_metadata.json"
)

Push-Location $projectRoot
try {
    git add -- @dataFiles
    if ($LASTEXITCODE -ne 0) {
        throw "無法暫存遊戲資料。"
    }

    git diff --cached --quiet -- @dataFiles
    if ($LASTEXITCODE -eq 0) {
        Write-Host "沒有可提交的遊戲資料變更。"
        exit 0
    }
    if ($LASTEXITCODE -ne 1) {
        throw "無法檢查已暫存的遊戲資料。"
    }

    $today = Get-Date -Format "yyyy-MM-dd"
    git commit -m "$MessagePrefix ($today)" -- @dataFiles
    if ($LASTEXITCODE -ne 0) {
        throw "Git commit 失敗。"
    }
} finally {
    Pop-Location
}
