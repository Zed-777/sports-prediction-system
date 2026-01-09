Param(
    [string]$Command = 'python scripts/check_api_keys.py'
)

<#
  Securely load API keys from PowerShell SecretManagement and run a command in the current session with them available as environment variables.

  Example:
    .\scripts\run_with_secrets.ps1 -Command 'python generate_fast_reports.py generate 5 matches for premier-league'

  This script does NOT store or log the secrets. It only loads them into the current PowerShell session environment for the duration of the command.
#>

try {
    Import-Module Microsoft.PowerShell.SecretManagement -ErrorAction SilentlyContinue
} catch {
    # Nothing to do if module not installed; the script will continue and envs may already be set via setx or other means
}

# If SecretManagement is not installed, print a helpful set of commands and exit to avoid confusion
if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.SecretManagement)) {
    Write-Host "Microsoft.PowerShell.SecretManagement module not found. Run the following commands to install (non-admin):"
    Write-Host "    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12"
    Write-Host "    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser"
    Write-Host "    Set-PSRepository -Name PSGallery -InstallationPolicy Trusted"
    Write-Host "    Install-Module -Name Microsoft.PowerShell.SecretManagement -Repository PSGallery -Force -Scope CurrentUser"
    Write-Host "    Install-Module -Name Microsoft.PowerShell.SecretStore -Repository PSGallery -Force -Scope CurrentUser"
    Write-Host '    Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault -Confirm:$false'
    Write-Host "After these steps, re-run this script."
    exit 2
}

$secretsToLoad = @(
    'SPORTSDATA_API_KEY',
    'ODDS_API_KEY',
    'API_FOOTBALL_KEY',
    'FOOTBALL_DATA_API_KEY'
)

foreach ($name in $secretsToLoad) {
    try {
        $sec = Get-Secret -Name $name -ErrorAction SilentlyContinue
        if ($sec -ne $null) {
            $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
            $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
            [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
            Set-Item -Path Env:$name -Value $plain
        }
    } catch {
        # Secret not present or SecretManagement not available. Ignore and continue; the command may read keys from other locations.
    }
}

if (-not (Get-SecretVault -ErrorAction SilentlyContinue)) {
    Write-Host "No SecretVault registered. If you want to use SecretStore, register it with:"
    Write-Host "  Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault"
    Write-Host "If the input prompts you for configuration, follow the prompts to configure SecretStore."
}

Write-Host "Running command with secrets (if available): $Command"
Invoke-Expression $Command
