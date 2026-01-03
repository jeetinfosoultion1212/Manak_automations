# MySQL Connector Build Fix

## Problem
When building the executable with PyInstaller, the MySQL connector authentication plugins were not being included, causing this error in the built .exe:

```
❌ Database connection failed: Authentication plugin 'mysql_native_password' is not supported
```

The application worked fine when running from source (`py manak_desktop_app.py`) but failed in the built executable.

## Root Cause
PyInstaller doesn't automatically detect and include MySQL connector's authentication plugin modules. These are dynamically loaded at runtime, so PyInstaller's dependency scanner misses them.

## Solution

### 1. Updated `build_exe.py` (lines 54-92)
Added missing MySQL connector modules to `hiddenimports`:

```python
hiddenimports=[
    # ... existing imports ...
    'mysql.connector',
    'mysql.connector.locales',
    'mysql.connector.locales.eng',
    'mysql.connector.plugins',                          # NEW
    'mysql.connector.plugins.mysql_native_password',    # NEW - Main auth plugin
    'mysql.connector.plugins.caching_sha2_password',    # NEW - Alternative auth
    'mysql.connector.cursor',                           # NEW
    'mysql.connector.pooling',                          # NEW
    'mysql.connector.errors',                           # NEW
    'job_cards_processor',                              # NEW
    'delivery_voucher_processor',                       # NEW
    'weight_capture_processor',                         # NEW
],
hookspath=['.'],  # Use hooks from current directory
```

### 2. Created `hook-mysql.connector.py`
A PyInstaller hook file that automatically collects all MySQL connector modules and plugins:

```python
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all mysql.connector submodules
hiddenimports = collect_submodules('mysql.connector')

# Ensure authentication plugins are included
hiddenimports += [
    'mysql.connector.plugins.mysql_native_password',
    'mysql.connector.plugins.caching_sha2_password',
    'mysql.connector.plugins.sha256_password',
]

# Collect all data files and binaries
datas, binaries, hiddenimports2 = collect_all('mysql.connector')
```

## How to Rebuild

1. **Clean previous builds** (optional but recommended):
   ```bash
   rmdir /s /q build dist
   del manak_desktop_app.spec
   ```

2. **Run the build script**:
   ```bash
   py build_exe.py
   ```

3. **Test the executable**:
   ```bash
   dist\manak_desktop_app\manak_desktop_app.exe
   ```

## Verification

After rebuilding, the executable should:
- ✅ Connect to MySQL database successfully
- ✅ Load job statuses from database
- ✅ Scan Fire Assaying portal
- ✅ Process bulk jobs without authentication errors

## Files Modified
- `build_exe.py` - Added MySQL connector modules to hiddenimports
- `hook-mysql.connector.py` - Created new PyInstaller hook file

## Date
2025-12-14

## Notes
- The hook file (`hook-mysql.connector.py`) must be in the same directory as `build_exe.py`
- PyInstaller will automatically use hooks from the `hookspath` directory
- This fix ensures ALL MySQL connector modules are included, not just the ones we explicitly use
