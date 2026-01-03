# Security Guidelines for MANAK Desktop Application

## Database Credentials Security

### ⚠️ IMPORTANT: Never expose database credentials in logs or source code!

### Current Security Measures:

1. **Environment Variables**: Database credentials are loaded from environment variables
2. **Safe Logging**: Only host and database name are logged, never username/password
3. **Config File**: Sensitive data is centralized in `config.py`

### How to Set Environment Variables:

#### Windows (PowerShell):
```powershell
$env:DB_HOST="217.21.85.154"
$env:DB_DATABASE="u176143338_hallmarkProver"
$env:DB_USER="u176143338_hallmarkProver"
$env:DB_PASSWORD="Rontik10@"
```

#### Windows (Command Prompt):
```cmd
set DB_HOST=217.21.85.154
set DB_DATABASE=u176143338_hallmarkProver
set DB_USER=u176143338_hallmarkProver
set DB_PASSWORD=Rontik10@
```

#### Linux/Mac:
```bash
export DB_HOST="217.21.85.154"
export DB_DATABASE="u176143338_hallmarkProver"
export DB_USER="u176143338_hallmarkProver"
export DB_PASSWORD="Rontik10@"
```

### For Production Deployment:

1. **Never hardcode credentials** in source code
2. **Use environment variables** or secure config files
3. **Rotate credentials regularly**
4. **Monitor access logs** for unauthorized access
5. **Use least privilege principle** for database users

### Logging Security:

- ✅ **Safe**: `host=217.21.85.154, database=u176143338_hallmarkProver`
- ❌ **Never**: `user=u176143338_hallmarkProver, password=Rontik10@`

The application now uses `get_safe_db_config_for_logging()` to ensure no sensitive data appears in logs.
