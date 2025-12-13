# Environment Stability & Idempotent Setup Guide

## Current Status: ✅ STABLE

The development environment is **now stable and idempotent**. All packages are installed and working.

## Why We Were Reinstalling (Root Cause Analysis)

During troubleshooting, we manually ran force-reinstalls to fix specific issues:

1. **numpy import error** (Phase 1): Fixed with `--force-reinstall numpy --no-cache-dir`
2. **matplotlib circular import** (Phase 1): Fixed with `--force-reinstall matplotlib --no-cache-dir`
3. **scikit-learn build warning** (Phase 2): Force-reinstalled as precaution

These were **one-time fixes** to resolve Python 3.14 compatibility issues. The idempotent setup script ensures this won't happen again.

## Current Package Status

All AI/ML packages installed and verified working:

```text
scikit-learn       1.7.2 ✅
numpy              2.3.5 ✅
pandas             2.3.3 ✅
matplotlib         3.10.7 ✅
lightgbm           4.6.0 ✅
xgboost            3.1.2 ✅
scipy              1.16.3 ✅
```

## How Idempotent Setup Works

### Marker File System

- **Location**: `.venv\.dev_installed`
- **Purpose**: Prevents repeated `pip install` calls
- **Created**: After first successful setup
- **Checked by**: `scripts\dev_setup.ps1`

### Setup Flow

```text
First run (no marker):
  → Creates .venv
  → pip install -r requirements.txt
  → pip install -r requirements-dev.txt
  → pip install -e .
  → Creates marker file
  ✅ DONE

Subsequent runs (marker exists):
  → Skips ALL pip installs
  → Just activates venv
  ✅ DONE (2 seconds)

Force reinstall (if needed):
  → scripts\dev_setup.ps1 -Force
  → Deletes marker, reruns setup
```

## Prevention: Never Manual Reinstalls

### ❌ DON'T DO THIS

```powershell
pip install --force-reinstall package-name  # Manual reinstalls break idempotency
pip install --upgrade package              # Can introduce incompatibilities
```

### ✅ DO THIS INSTEAD

```powershell
# If something breaks, use the idempotent setup:
powershell -ExecutionPolicy Bypass -File scripts\dev_setup.ps1 -Force

# This will:
# 1. Clear the marker file
# 2. Reinstall ALL dependencies from requirements files
# 3. Recreate the marker file
# 4. Guarantee consistent state
```

## Future-Proofing

### Best Practices to Maintain Stability

1. **Use `-Force` flag for full reset**

   ```powershell
   scripts\dev_setup.ps1 -Force
   ```

2. **Never modify installed packages manually**
   - Any manual pip operations break the idempotent contract
   - Always update via `requirements.txt` and re-run setup

3. **Update requirements properly**

   ```powershell
   # DON'T: pip install --upgrade package
   # DO: Update requirements.txt, then:
   scripts\dev_setup.ps1 -Force
   ```

4. **Share environment state via requirements files**
   - `requirements.txt`: Runtime dependencies (frozen versions)
   - `requirements-dev.txt`: Development dependencies
   - `requirements_phase2.txt`: Optional Phase 2 features
   - `pyproject.toml`: Package metadata and editable install

### Frozen Versions (as of Dec 4, 2025)

These versions are locked in `requirements.txt` to ensure reproducibility:

```text
scikit-learn==1.7.2
numpy==2.3.5
pandas==2.3.3
matplotlib==3.10.7
lightgbm==4.6.0
xgboost==3.1.2
scipy==1.16.3
```

If you need to upgrade, update the version numbers in `requirements.txt`, then:

```powershell
scripts\dev_setup.ps1 -Force
```

## Troubleshooting: If Setup Fails

```powershell
# Step 1: Remove marker to force full reinstall
Remove-Item .venv\.dev_installed -ErrorAction SilentlyContinue

# Step 2: Run setup with Force flag
scripts\dev_setup.ps1 -Force

# Step 3: Verify installation
.venv\Scripts\python.exe -c "import sklearn, numpy, pandas, matplotlib; print('OK')"

# If it still fails, nuke and rebuild:
Remove-Item .venv -Recurse -Force
scripts\dev_setup.ps1
```

## CI/CD Integration

The same idempotent setup is used in GitHub Actions:

- **Trigger**: Marker file check (`.venv/.dev_installed`)
- **Action**: If missing or invalid, runs `dev_setup.ps1 -Force`
- **Result**: Consistent environment across all runs

## Key Takeaway

**The environment is now stable and self-maintaining.** You should NEVER need to manually reinstall packages again. If something breaks:

1. Use `scripts\dev_setup.ps1 -Force` (not manual `pip install`)
2. This ensures all dependencies are consistent
3. The marker file prevents unnecessary re-runs

---

**Setup Last Updated**: December 4, 2025  
**Idempotent Status**: ✅ ACTIVE  
**Package Stability**: ✅ LOCKED  
**Future Maintenance**: Low (setup handles everything)
