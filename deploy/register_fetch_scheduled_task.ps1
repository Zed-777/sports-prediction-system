# Register a Windows Scheduled Task to run the fetcher daily at 03:00
Param(
    [string]$RepoPath = "C:\Users\zmgdi\OneDrive\Desktop\STATS",
    [string]$TaskName = "SportsForecastFetch"
)

$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command `"cd $RepoPath; python scripts/collect_historical_results.py --fetch-all --auto-optimize 50 --notify`""
$Trigger = New-ScheduledTaskTrigger -Daily -At 03:00AM
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Description 'Fetch results daily and update historical dataset' -Force
Write-Host "Scheduled task '$TaskName' registered to run daily at 03:00."
