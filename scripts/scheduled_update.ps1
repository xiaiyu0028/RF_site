<#
給 Windows 工作排程器使用的包裝腳本：
  1. 執行 update_game_data.ps1 抓取最新國策 / 城鎮 / 城內地點資料
  2. 成功才執行 commit_game_data.ps1
  3. git push 到遠端（push 後 GitHub Pages 會自動部署）；加上 -NoPush 則只 commit 在本機
加上 -DryRun 則只驗證抓取結果，不寫檔、不 commit，適合測試排程設定。
所有輸出寫入 logs/update_yyyyMMdd_HHmmss.log，失敗時以非 0 結束碼離開，
工作排程器的「上次執行結果」即可看出成敗。
#>
[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$DryRun,
    [ValidateRange(1, 3650)]
    [int]$KeepLogDays = 90
)

# 不用 Stop：PowerShell 5.1 在 2>&1 轉向原生程式 stderr 時會產生 ErrorRecord，
# 設為 Stop 會讓 git 的進度訊息被當成例外中斷。成敗一律以 $LASTEXITCODE 判斷。
$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("update_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

# 子程序輸出統一用 UTF-8，避免中文在 log 裡變亂碼
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

function Write-Log {
    param([string]$Message)
    Write-Host $Message
    Add-Content -Path $logFile -Value $Message -Encoding UTF8
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments = @()
    )
    Write-Log ""
    Write-Log ("[{0:HH:mm:ss}] ▶ {1}" -f (Get-Date), $Name)
    & $FilePath @Arguments 2>&1 | ForEach-Object { Write-Log "$_" }
    $code = $LASTEXITCODE
    Write-Log ("[{0:HH:mm:ss}] {1} 結束碼：{2}" -f (Get-Date), $Name, $code)
    return $code
}

function Invoke-ChildScript {
    param([string]$Name, [string]$ScriptName, [string[]]$ExtraArguments = @())
    # 以獨立 powershell.exe 執行，子腳本內的 ErrorActionPreference = Stop 才不會受外層轉向影響
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    return Invoke-Step -Name $Name -FilePath "powershell.exe" `
        -Arguments (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $scriptPath) + $ExtraArguments)
}

Push-Location $projectRoot
$exitCode = 0
try {
    Write-Log ("===== RF 遊戲資料排程更新 {0:yyyy-MM-dd HH:mm:ss} =====" -f (Get-Date))

    $updateArgs = if ($DryRun) { @("-DryRun") } else { @() }
    $exitCode = Invoke-ChildScript -Name "更新遊戲資料" -ScriptName "update_game_data.ps1" -ExtraArguments $updateArgs
    if ($exitCode -ne 0) {
        Write-Log "更新失敗，略過 commit / push。"
        return
    }
    if ($DryRun) {
        Write-Log "DryRun 模式：只驗證，不 commit / push。"
        return
    }

    $exitCode = Invoke-ChildScript -Name "提交遊戲資料" -ScriptName "commit_game_data.ps1"
    if ($exitCode -ne 0) {
        Write-Log "Commit 失敗，略過 push。"
        return
    }

    if (-not $NoPush) {
        $exitCode = Invoke-Step -Name "推送到遠端" -FilePath "git" -Arguments @("push")
        if ($exitCode -ne 0) {
            Write-Log "Push 失敗。"
            return
        }
    } else {
        Write-Log ""
        Write-Log "已指定 -NoPush，資料只 commit 在本機。"
    }
} catch {
    Write-Log "未預期的錯誤：$_"
    $exitCode = 1
} finally {
    Pop-Location
    Write-Log ""
    Write-Log ("===== 結束，結束碼 {0} =====" -f $exitCode)

    # 清掉過期 log
    Get-ChildItem -Path $logDir -Filter "update_*.log" -File |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepLogDays) } |
        Remove-Item -Force

    # 放在 finally 裡，確保上面提早 return 時也會回傳正確的結束碼
    exit $exitCode
}
