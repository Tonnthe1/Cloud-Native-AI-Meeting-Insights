param(
    [string]$InstallDir = $(if ($env:MEETING_INSIGHTS_INSTALL_DIR) { $env:MEETING_INSIGHTS_INSTALL_DIR } else { Join-Path $HOME "meeting-insights" }),
    [string]$Ref = $(if ($env:MEETING_INSIGHTS_REF) { $env:MEETING_INSIGHTS_REF } else { "main" })
)

$ErrorActionPreference = "Stop"
$RepositoryUrl = if ($env:MEETING_INSIGHTS_REPOSITORY_URL) { $env:MEETING_INSIGHTS_REPOSITORY_URL } else { "https://github.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights.git" }
if (-not $env:MEETING_INSIGHTS_PREBUILT) { $env:MEETING_INSIGHTS_PREBUILT = "true" }

function Write-Log([string]$Message) {
    Write-Host "[meeting-insights-installer] $Message"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required: https://git-scm.com/downloads"
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required: https://docs.docker.com/desktop/"
}
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not running." }
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Compose v2 is required." }

if ((Test-Path $InstallDir) -and -not (Test-Path (Join-Path $InstallDir ".git"))) {
    throw "$InstallDir already exists and is not a Git repository. Choose another InstallDir."
}

if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
    Write-Log "Cloning Meeting Insights into $InstallDir."
    & git clone --branch $Ref --depth 1 $RepositoryUrl $InstallDir
    if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }
}
else {
    Write-Log "Using existing checkout at $InstallDir."
    $changes = & git -C $InstallDir status --porcelain
    if (-not $changes) {
        & git -C $InstallDir fetch --depth 1 origin $Ref
        if ($LASTEXITCODE -ne 0) { throw "Git fetch failed." }
        & git -C $InstallDir checkout --quiet --detach FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { throw "Git checkout failed." }
    }
    else {
        Write-Log "Checkout has local changes; leaving them untouched."
    }
}

& (Join-Path $InstallDir "scripts/quickstart.ps1") up
if ($LASTEXITCODE -ne 0) { throw "Meeting Insights startup failed." }
