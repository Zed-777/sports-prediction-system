# Secrets & API keys (Local dev guidance)

This project needs several API keys for data sources (Football-Data, API-Football, SportsData, Odds providers). Do NOT paste keys into public files or pass them to anyone (including assistance sessions). Use one of the secure local approaches below.

Recommended (PowerShell on Windows): PowerShell SecretManagement + SecretStore

- Install SecretManagement/SecretStore if not already installed (PowerShell 5.1/7+):

  ```powershell
  # Ensure the execution policy allows module installation for the current user
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  Install-Module -Name Microsoft.PowerShell.SecretManagement -Force -Scope CurrentUser
  Install-Module -Name Microsoft.PowerShell.SecretStore -Force -Scope CurrentUser
  Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
  ```

- Add a secret to the SecretStore (example):

  ```powershell
  Set-Secret -Name SPORTSDATA_API_KEY -Secret (ConvertTo-SecureString 'YOUR_KEY_HERE' -AsPlainText -Force)
  Set-Secret -Name ODDS_API_KEY -Secret (ConvertTo-SecureString 'YOUR_ODDS_KEY' -AsPlainText -Force)
  ```

- Then run the project command with the helper wrapper `scripts/run_with_secrets.ps1` which loads the secrets into the PowerShell session as environment variables and executes your command:

  ```powershell
  .\scripts\run_with_secrets.ps1 -Command 'python generate_fast_reports.py generate 5 matches for premier-league'
  ```

## Throttle tuning

- If you see many 429 rate-limit errors, consider changing `config/settings.yaml` throttle_by_host values described in `docs/RATE_LIMITING.md` to lower consumption or upgrade your plan.

## Alternatives (if you prefer)

- Persist the secret in the Windows environment with `setx` (less secure than SecretStore) — note `setx` changes are available in new terminals only:

  ```powershell
  setx SPORTSDATA_API_KEY "<your_key_here>" -m
  # Open a new terminal for the change to take effect in the process environment
  ```

- CI / Cloud: use your platform's secrets manager (GitHub Actions Secrets, Azure Key Vault, AWS SecretsManager, Google Secret Manager) — DO NOT put keys in CI logs or public repos.

Why not send the keys to anyone including the assistant?

- Secrets are sensitive. I (this assistant) cannot store secrets or manage them on your behalf. For your safety, never paste or send keys into a chat or email. Use secure tools described above. If you want help implementing the wrapper or verifying it works, I can edit the repository and provide instructions, but I will not accept or store your secrets.

If you want, I can implement additional wrappers that load secrets from other vaults and integrate them into your CI workflow — tell me which vault or environment you want and I will make a PR patch for that environment.

Troubleshooting installation and non-admin commands

- If you receive a prompt to install the NuGet provider, or you see an "Administrator rights are required" error, you can run the following non-admin commands which install providers for the current user:

  ```powershell
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser
  Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
  Install-Module -Name Microsoft.PowerShell.SecretManagement -Repository PSGallery -Force -Scope CurrentUser
  Install-Module -Name Microsoft.PowerShell.SecretStore -Repository PSGallery -Force -Scope CurrentUser
  Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault -Confirm:$false
  ```

  If you still encounter permission errors, try opening PowerShell as Administrator or installing PowerShell 7 and re-running these steps.
