$ErrorActionPreference = "Stop"

$scriptPath = "E:\E\任务\task-platform\web\backend\run_fetch.bat"
$taskName = "YantaiRebarFetcher"

Write-Host "Creating scheduled task..."
Write-Host ""

# Check if exists
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Task exists, removing..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory "E:\E\任务\task-platform\web\backend"

# Create trigger - 9am daily
$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Create principal
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily scraper for Yantai rebar prices"

Write-Host ""
Write-Host "=========================================="
Write-Host "Scheduled task created successfully!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Task Name: $taskName"
Write-Host "Schedule: Daily at 09:00"
Write-Host "Script: $scriptPath"
Write-Host ""
Write-Host "Management commands:"
Write-Host '  View task: Get-ScheduledTask -TaskName "YantaiRebarFetcher"'
Write-Host '  Run now: Start-ScheduledTask -TaskName "YantaiRebarFetcher"'
Write-Host '  Delete task: Unregister-ScheduledTask -TaskName "YantaiRebarFetcher" -Confirm:$false'
Write-Host ""