$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $RepoDir "logs"
$VenvPython = Join-Path $RepoDir ".venv\Scripts\python.exe"
$Requirements = Join-Path $RepoDir "requirements.txt"
$EnvFile = Join-Path $RepoDir ".env"
$LogFile = Join-Path $LogDir ("bot-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $RepoDir

function Write-BotLog {
    param([string]$Message)
    $line = "[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "] " + $Message
    Add-Content -LiteralPath $LogFile -Value $line
    Write-Output $line
}

function Invoke-NativeLogged {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $FilePath @Arguments 2>&1 | ForEach-Object {
            $line = $_.ToString()
            Add-Content -LiteralPath $LogFile -Value $line
            Write-Output $line
        }
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
}

Write-BotLog "Starting Discord TikTok bot runner from $RepoDir"

if (-not (Test-Path $VenvPython)) {
    Write-BotLog "Creating local virtual environment."
    Invoke-NativeLogged -FilePath "python" -Arguments @("-m", "venv", ".venv") | Out-Null
}

Write-BotLog "Installing/updating dependencies."
Invoke-NativeLogged -FilePath $VenvPython -Arguments @("-m", "pip", "install", "-r", $Requirements) | Out-Null

if (-not (Test-Path $EnvFile)) {
    "DISCORD_BOT_TOKEN=put-your-discord-bot-token-here" | Set-Content -LiteralPath $EnvFile
    Write-BotLog "Created .env with placeholder token. Replace it before running the bot."
    exit 1
}

$envText = Get-Content -Raw -LiteralPath $EnvFile
if ($envText -match "put-your-discord-bot-token-here" -or $envText -notmatch "DISCORD_BOT_TOKEN=\S+") {
    Write-BotLog ".env does not contain a usable DISCORD_BOT_TOKEN."
    exit 1
}

while ($true) {
    Write-BotLog "Launching bot."
    $exitCode = Invoke-NativeLogged -FilePath $VenvPython -Arguments @("main.py")
    Write-BotLog "Bot exited with code $exitCode. Restarting in 10 seconds."
    Start-Sleep -Seconds 10
}
