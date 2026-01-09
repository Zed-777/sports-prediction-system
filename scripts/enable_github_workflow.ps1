param(
    [Parameter(Mandatory=$true)][string] $Owner,
    [Parameter(Mandatory=$true)][string] $Repo,
    [Parameter(Mandatory=$true)][string] $WorkflowFile, # e.g., fetch-results.yml
    [string] $Ref = 'main',
    [string] $Token = $env:GITHUB_TOKEN
)

if (-not $Token) {
    Write-Error "A GitHub token is required. Set it in environment as GITHUB_TOKEN or pass via -Token."
    exit 1
}

$base = "https://api.github.com/repos/$Owner/$Repo/actions/workflows/$WorkflowFile"

# Enable workflow
try {
    $headers = @{ Authorization = "Bearer $Token"; 'User-Agent' = 'enable-github-workflow-script' }
    Write-Host "Enabling workflow $WorkflowFile for $Owner/$Repo..."
    $enableResp = Invoke-RestMethod -Uri "$base/enable" -Method Put -Headers $headers -ErrorAction Stop
    Write-Host "Workflow enabled (HTTP 204 indicates success)."
} catch {
    Write-Warning "Enable call failed: $_"
}

# Trigger a workflow_dispatch
try {
    Write-Host "Triggering workflow_dispatch on ref $Ref..."
    $body = @{ ref = $Ref } | ConvertTo-Json
    $dispatchResp = Invoke-RestMethod -Uri "$base/dispatches" -Method Post -Headers $headers -Body $body -ErrorAction Stop
    Write-Host "Workflow dispatch requested. Check GitHub Actions UI for the run."
} catch {
    Write-Warning "Dispatch call failed: $_"
}

Write-Host "Done."