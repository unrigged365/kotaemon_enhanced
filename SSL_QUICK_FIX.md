# SSL Verification Bypass - Quick Reference

## The Problem
```
HTTPSConnectionPool(...): Max retries exceeded...
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

## Quick Fix (Development Only)

### Linux/macOS
```bash
export KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

### Windows (PowerShell)
```powershell
$env:KOTAEMON_DISABLE_SSL_VERIFY="true"
python app.py
```

### Windows (Command Prompt)
```cmd
set KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

### Docker
```dockerfile
ENV KOTAEMON_DISABLE_SSL_VERIFY=true
```

### WSL/Ubuntu
```bash
export KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

## Using Helper Scripts

### Linux/macOS
```bash
chmod +x run_with_ssl_disabled.sh
./run_with_ssl_disabled.sh
```

### Windows
```cmd
run_with_ssl_disabled.bat
```

## In Python Code
```python
import os
os.environ["KOTAEMON_DISABLE_SSL_VERIFY"] = "true"

# Then import and use
from kotaemon.indices.splitters import LLMBasedChunker
```

## Via .env File
1. Copy `.env.example.ssl` to `.env`
2. Set `KOTAEMON_DISABLE_SSL_VERIFY=true`
3. Load with: `from dotenv import load_dotenv; load_dotenv()`

---

## ⚠️ IMPORTANT SECURITY WARNINGS

- **Development Only**: This is unsafe for production
- **Temporary Solution**: Use this while implementing proper fixes
- **Better Alternatives**: See SSL_VERIFICATION_GUIDE.md for permanent solutions
- **Corporate Networks**: Work with IT to install proper certificates instead

## More Information

See `SSL_VERIFICATION_GUIDE.md` for:
- 6 different solutions
- Corporate proxy configuration
- Installing CA certificates properly
- Troubleshooting tips
- Security considerations
