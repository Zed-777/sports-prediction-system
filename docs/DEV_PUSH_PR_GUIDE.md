# How to push the local branch and open a PR (PowerShell)

This project was initialized locally and a branch was created. To push the branch to GitHub and open a PR, follow these steps.

1) Add the GitHub remote (only if not already set):

```powershell
# Replace <GIT_REMOTE_URL> with your GitHub repository URL (HTTPS or SSH)
git remote add origin <GIT_REMOTE_URL>
```

2) Push the current branch (the command printed earlier shows the branch name; replace BRANCH_NAME if needed):

```powershell
# Replace BRANCH_NAME with the branch printed in the console
git push -u origin BRANCH_NAME
```

3) Open a Pull Request

Option A (recommended): use GitHub web UI
- After pushing, visit your repository page on GitHub. You should see a banner to create a pull request for the recently pushed branch. Click "Compare & pull request" and submit.

Option B: use GitHub CLI

```powershell
# Requires GitHub CLI (gh) installed and authenticated
gh pr create --fill --base main --head BRANCH_NAME
```

Option C: open the PR URL manually (construct using owner/repo)

```powershell
# Replace owner/repo with your repository path and BRANCH_NAME accordingly
Start-Process "https://github.com/owner/repo/pull/new/BRANCH_NAME"
```

Notes:
- Pushing requires authentication (SSH key or Personal Access Token configured for HTTPS). If you get an authentication error, follow GitHub's guidance to set up credentials.
- The CI workflow file was added at `.github/workflows/python-tests.yml` and will run automatically for pushed branches and PRs.

If you want, I can attempt to push for you (requires that the environment has access to your GitHub credentials). Otherwise, run the commands above locally and then tell me the PR URL so I can monitor CI results.