# SSL Verification Bypass Implementation

## Summary

I've implemented SSL verification bypass for tiktoken downloads in Kotaemon to handle certificate verification failures in corporate/restricted network environments.

## Changes Made

### 1. Updated `llm_chunker.py`

**Location**: `libs/kotaemon/kotaemon/indices/splitters/llm_chunker.py`

**Changes**:
- Added `urllib3` import for disabling SSL warnings
- Added automatic SSL warning suppression (urllib3.InsecureRequestWarning)
- Added environment variable check for `KOTAEMON_DISABLE_SSL_VERIFY`
- When enabled, clears `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` environment variables

**Code**:
```python
import urllib3

# Disable SSL warnings for development
try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

# Set environment variables to disable SSL verification for tiktoken downloads
if os.getenv("KOTAEMON_DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["CURL_CA_BUNDLE"] = ""
```

### 2. Created Documentation & Helper Scripts

#### `SSL_VERIFICATION_GUIDE.md`
Comprehensive guide covering:
- Problem explanation
- 6 different solutions (from environment variables to corporate proxy setup)
- Security considerations and warnings
- Troubleshooting tips
- Implementation details

#### `run_with_ssl_disabled.sh` (Linux/macOS)
Quick convenience script to run the application with SSL verification disabled.

**Usage**:
```bash
chmod +x run_with_ssl_disabled.sh
./run_with_ssl_disabled.sh
```

#### `run_with_ssl_disabled.bat` (Windows)
Windows equivalent of the above script.

**Usage**:
```cmd
run_with_ssl_disabled.bat
```

## How to Use

### Quick Start (Development Only)

#### Option 1: Environment Variable
```bash
export KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

#### Option 2: Helper Script
```bash
./run_with_ssl_disabled.sh
```

#### Option 3: Python Code
```python
import os
os.environ["KOTAEMON_DISABLE_SSL_VERIFY"] = "true"

# Then run your application
from kotaemon.indices.splitters import LLMBasedChunker
```

### Recommended Approaches

1. **For Development**: Use the environment variable method
2. **For Production**: Resolve underlying SSL/certificate issues (see solutions 4-6 in guide)
3. **For CI/CD**: Pre-download tiktoken encodings and cache them
4. **For Corporate**: Work with IT to configure proxy or install CA certificates

## Security Notes

⚠️ **Important**: This is for development only. Production systems should:
- Have proper SSL certificates installed
- Use corporate proxy configurations properly
- Never disable SSL verification in production environments

## Testing

The implementation is transparent - no changes needed to existing code. Simply set the environment variable before running:

```bash
KOTAEMON_DISABLE_SSL_VERIFY=true python app.py
```

The LLMBasedChunker will automatically detect this and configure SSL verification bypass for tiktoken downloads.

## Troubleshooting

If you still get SSL errors:
1. Ensure environment variable is set: `echo $KOTAEMON_DISABLE_SSL_VERIFY`
2. Try restarting the Python process (environment variables are read at import time)
3. Check corporate proxy requirements (see SSL_VERIFICATION_GUIDE.md)
4. Consider using local tiktoken cache instead

## Future Improvements

- Add CLI flag: `python app.py --disable-ssl-verify`
- Add configuration file support: `config/ssl.yaml`
- Add automatic detection of SSL issues and helpful error messages
- Create docker image with pre-configured tiktoken cache
