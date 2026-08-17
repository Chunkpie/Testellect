$repoDir = "d:\TestEllect\scratch\contribution-repo"
if (Test-Path $repoDir) { Remove-Item -Recurse -Force $repoDir }
New-Item -ItemType Directory -Path $repoDir | Out-Null
Set-Location $repoDir
git init
git remote add origin https://github.com/Chunkpie/contribution.git

$email = "zone786k@gmail.com"
$name = "chunkpie"

$startDate = [datetime]"2026-05-03"
$endDate = [datetime]"2026-06-30"
$currentDate = $startDate
$totalCommits = 0

Write-Host "Generating commits from May 3 to June 30..."

while ($currentDate -le $endDate) {
    $rand = Get-Random -Minimum 1 -Maximum 101
    if ($rand -le 10) { $c = Get-Random -Minimum 51 -Maximum 65 }
    elseif ($rand -le 30) { $c = Get-Random -Minimum 21 -Maximum 50 }
    elseif ($rand -le 70) { $c = Get-Random -Minimum 6 -Maximum 20 }
    else { $c = Get-Random -Minimum 1 -Maximum 5 }
    
    for ($j = 0; $j -lt $c; $j++) {
        $hour = Get-Random -Minimum 9 -Maximum 23
        $minute = Get-Random -Minimum 0 -Maximum 59
        $second = Get-Random -Minimum 0 -Maximum 59
        $commitDate = $currentDate.AddHours($hour).AddMinutes($minute).AddSeconds($second).ToString("yyyy-MM-ddTHH:mm:ss")
        
        Add-Content -Path "activity.txt" -Value "Log entry $commitDate"
        git add activity.txt
        $env:GIT_AUTHOR_DATE = $commitDate
        $env:GIT_COMMITTER_DATE = $commitDate
        git commit -m "Activity update" --author "$name <$email>" | Out-Null
        $totalCommits++
    }
    $currentDate = $currentDate.AddDays(1)
}

Write-Host "Generated $totalCommits commits. Pushing to GitHub..."
git branch -M main
git push -u origin main --force
Write-Host "Done!"
