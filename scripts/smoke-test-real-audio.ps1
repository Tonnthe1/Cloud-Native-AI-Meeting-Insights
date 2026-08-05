param(
    [Parameter(Mandatory = $true)]
    [string]$AudioFile,
    [string]$FrontendBaseUrl = "http://localhost:3000",
    [int]$TimeoutSeconds = $(if ($env:SMOKE_TIMEOUT_SECONDS) { [int]$env:SMOKE_TIMEOUT_SECONDS } else { 1800 })
)

$ErrorActionPreference = "Stop"
$resolvedAudioFile = (Resolve-Path -LiteralPath $AudioFile).Path
$FrontendBaseUrl = $FrontendBaseUrl.TrimEnd("/")

function Write-Log([string]$Message) {
    Write-Host "[real-audio-smoke] $Message"
}

Add-Type -AssemblyName System.Net.Http
$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromMinutes(10)
# Exercise the proxy path that receives Expect: 100-continue from Windows clients.
$client.DefaultRequestHeaders.ExpectContinue = $true

$stream = $null
$multipart = $null
$fileContent = $null
try {
    $stream = [System.IO.File]::OpenRead($resolvedAudioFile)
    $fileContent = New-Object -TypeName System.Net.Http.StreamContent -ArgumentList (, $stream)
    $fileContent.Headers.ContentType = New-Object -TypeName System.Net.Http.Headers.MediaTypeHeaderValue -ArgumentList "audio/wav"
    $multipart = New-Object System.Net.Http.MultipartFormDataContent
    $multipart.Add($fileContent, "file", [System.IO.Path]::GetFileName($resolvedAudioFile))

    $uploadUrl = "$FrontendBaseUrl/api/analyze-meeting"
    Write-Log "Uploading through $uploadUrl"
    $response = $client.PostAsync($uploadUrl, $multipart).GetAwaiter().GetResult()
    $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) {
        throw "Upload failed with HTTP $([int]$response.StatusCode): $responseBody"
    }
    $upload = $responseBody | ConvertFrom-Json
}
finally {
    if ($multipart) { $multipart.Dispose() }
    elseif ($fileContent) { $fileContent.Dispose() }
    elseif ($stream) { $stream.Dispose() }
    $client.Dispose()
}

$meetingId = [int]$upload.meeting_id
Write-Log "Meeting $meetingId was accepted; polling every 3 seconds."
$startedAt = Get-Date
while ($true) {
    $meeting = Invoke-RestMethod -Method Get -Uri "$FrontendBaseUrl/api/meetings/$meetingId" -UseBasicParsing
    $meetingStatus = if ($meeting.status) { [string]$meeting.status } else { "unknown" }
    Write-Log "Meeting $meetingId status: $meetingStatus"

    if ($meetingStatus -eq "completed") {
        $transcript = [string]$meeting.transcript
        if ([string]::IsNullOrWhiteSpace($transcript)) {
            throw "Meeting completed without a transcript."
        }
        Write-Log "Completed with a persisted transcript ($($transcript.Trim().Length) characters)."
        exit 0
    }
    if ($meetingStatus -eq "failed") {
        throw "Meeting processing failed: $($meeting | ConvertTo-Json -Depth 10 -Compress)"
    }
    if (((Get-Date) - $startedAt).TotalSeconds -ge $TimeoutSeconds) {
        throw "Timed out after $TimeoutSeconds seconds waiting for meeting $meetingId."
    }
    Start-Sleep -Seconds 3
}
