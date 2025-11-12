# Workspace environment helper

This workspace is configured to use the local virtual environment at `.venv-Z1.1`.

What I added:

- `.vscode/settings.json`  pins the Python interpreter to `.venv-Z1.1\Scripts\python.exe` and enables terminal auto-activation.

- `.vscode/activate_venv.ps1`  PowerShell helper the terminal profile can call to activate the venv on new terminals.

- `.vscode/ENVIRONMENT.md`  short instructions.

How to ensure the venv is active in VS Code (PowerShell):

1. Open the Command Palette (Ctrl+Shift+P)  `Python: Select Interpreter`  choose the entry that points to `.venv-Z1.1\Scripts\python.exe`.
2. Reload the window (Developer: Reload Window) so the language server and Problems panel refresh.
3. Open a new integrated terminal  it should auto-activate the venv.

Quick manual commands (PowerShell) to activate and verify:

```powershell
. .\.venv-Z1.1\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

If the interpreter shown is not the `.venv-Z1.1` path, use the Command Palette to reselect the workspace interpreter and reload.
