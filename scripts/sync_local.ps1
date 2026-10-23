# Local sync: fetch Eastmoney LHB data, then commit and push if a day file changed.
# GitHub Pages republishes docs/ automatically after each push.
# Run by the Windows scheduled task "lhb-sync" (see scripts/install_task.ps1).
# Log: ..\sync.log
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$log = Join-Path $repo 'sync.log'
function Log($msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Out-File -Append -Encoding utf8 $log }

if ((Test-Path $log) -and (Get-Item $log).Length -gt 200KB) {
  $tail = Get-Content $log -Encoding utf8 -Tail 300
  $tail | Out-File -Encoding utf8 $log
}

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'

git pull --rebase --autostash --quiet 2>&1 | ForEach-Object { Log "pull: $_" }
& python scripts\fetch_lhb.py --days 2 2>&1 | ForEach-Object { Log "fetch: $_" }
if ($LASTEXITCODE -ne 0) { Log 'fetch failed'; exit 1 }

# index.json changes on every run (check time); only publish when a day file changed
$changed = @(git status --porcelain -- docs/data | Where-Object { $_ -notmatch 'index\.json$' })
if ($changed.Count -eq 0) {
  git checkout -- docs/data/index.json 2>$null
  Log 'no change'
  exit 0
}
git add docs/data
git commit -q -m "data: $(Get-Date -Format 'yyyy-MM-dd HH:mm') local"
git push -q 2>&1 | ForEach-Object { Log "push: $_" }
if ($LASTEXITCODE -ne 0) { Log 'push failed'; exit 1 }
Log "pushed: $($changed -join ', ')"
