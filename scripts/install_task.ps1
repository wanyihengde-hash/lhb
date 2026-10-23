# Registers the Windows scheduled task "lhb-sync" for the current user.
# Times follow this PC's time zone, which is set to China Standard Time (Beijing):
#   Mon-Fri 16:30-21:30 every 30 minutes, plus Tue-Sat 09:10 for Eastmoney's late corrections.
# Remove with: Unregister-ScheduledTask -TaskName lhb-sync -Confirm:$false
$repo = Split-Path -Parent $PSScriptRoot
$ps = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$script = Join-Path $repo 'scripts\sync_local.ps1'
# conhost --headless keeps a console window from flashing up every half hour
$action = New-ScheduledTaskAction -Execute (Join-Path $env:WINDIR 'System32\conhost.exe') `
  -Argument "--headless `"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WorkingDirectory $repo

$weekdays = 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
$evening = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $weekdays -At '16:30'
$evening.Repetition = (New-ScheduledTaskTrigger -Once -At '16:30' `
  -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Hours 5)).Repetition
$morning = New-ScheduledTaskTrigger -Weekly -DaysOfWeek 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday' -At '09:10'

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName 'lhb-sync' -Force -Action $action -Trigger $evening, $morning -Settings $settings `
  -Description 'Sync Eastmoney LHB data to https://wanyihengde-hash.github.io/lhb/ (repo: C:\Users\Henry\lhb-sync)' |
  Select-Object TaskName, State
