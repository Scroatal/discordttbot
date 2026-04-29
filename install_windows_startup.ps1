$ErrorActionPreference = "Stop"

$TaskName = "DiscordTikTokBot"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $RepoDir "run_bot.ps1"
$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $Runner)) {
    throw "Could not find runner script: $Runner"
}

$action = New-ScheduledTaskAction `
    -Execute $PowerShell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`"" `
    -WorkingDirectory $RepoDir

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Runs the Discord TikTok kktiktok converter bot at Windows logon." `
    -Force | Out-Null

Write-Output "Installed scheduled task: $TaskName"
Write-Output "Runner: $Runner"
Write-Output "Logs: $(Join-Path $RepoDir 'logs')"
