# SSL Verification Bypass Guide for Kotaemon

This guide explains how to disable SSL verification for tiktoken downloads and other HTTPS requests when facing certificate verification errors.

## Problem

When running LLM-based semantic chunking, you may encounter:
```
HTTPSConnectionPool(...): Max retries exceeded...
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

This typically occurs in corporate environments with firewalls or custom SSL proxies.

## Solutions

### Solution 1: Environment Variable (Recommended for Development)

Set the `KOTAEMON_DISABLE_SSL_VERIFY` environment variable before running the application:

#### On Linux/macOS:
```bash
export KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

#### On Windows (PowerShell):
```powershell
$env:KOTAEMON_DISABLE_SSL_VERIFY="true"
python app.py
```

#### On Windows (Command Prompt):
```cmd
set KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

#### In Docker:
```dockerfile
ENV KOTAEMON_DISABLE_SSL_VERIFY=true
```

#### In WSL (Ubuntu):
```bash
export KOTAEMON_DISABLE_SSL_VERIFY=true
python app.py
```

### Solution 2: Python Code (For Script-based Usage)

Add these lines at the start of your script or in a configuration file:

```python
import os
os.environ["KOTAEMON_DISABLE_SSL_VERIFY"] = "true"

# Then import and use kotaemon
from kotaemon.indices.splitters import LLMBasedChunker
```

### Solution 3: .env File Configuration

Create a `.env` file in your project root with:
```
KOTAEMON_DISABLE_SSL_VERIFY=true
```

Then load it using python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()

# Application code follows
```

### Solution 4: Alternative - Use Local tiktoken Cache

Instead of disabling SSL, download tiktoken encodings once locally:

```python
import os
import tiktoken

# Set cache directory (optional)
os.environ["TIKTOKEN_CACHE_DIR"] = "./tiktoken_cache"

# Download encodings (this will be cached)
encoding = tiktoken.encoding_for_model("gpt-4o-mini")
```

Then commit the cache to your repository or use CI/CD to pre-download it.

### Solution 5: Corporate Proxy Configuration

If you're behind a corporate proxy, configure it:

```python
import os

# Set proxy for requests
os.environ["HTTPS_PROXY"] = "https://your-proxy:port"
os.environ["HTTP_PROXY"] = "http://your-proxy:port"

# For authentication if needed
os.environ["PROXY_USER"] = "username"
os.environ["PROXY_PASS"] = "password"
```

### Solution 6: Install CA Certificates (Permanent Fix)

For permanent solution, install the missing CA certificates:

#### On Linux (Ubuntu/Debian):
```bash
apt-get install ca-certificates
```

#### On macOS:
```bash
brew install ca-certificates
```

#### On Windows:
Install certificates via Windows Certificate Manager or Python's certifi:
```bash
pip install --upgrade certifi
```

## Security Considerations

⚠️ **WARNING**: Disabling SSL verification bypasses important security checks and makes your system vulnerable to Man-in-the-Middle (MITM) attacks.

- **Development Only**: Only use SSL verification bypass in development or internal environments
- **Never in Production**: Production systems should have proper SSL certificates configured
- **Temporary Solution**: Use this as a temporary workaround while setting up proper SSL infrastructure
- **Better Alternatives**: Try solutions 4, 5, or 6 above for more secure approaches

## Implementation in Kotaemon

The LLM-based chunker now includes automatic SSL warning suppression when `KOTAEMON_DISABLE_SSL_VERIFY` is enabled:

```python
# In llm_chunker.py
if os.getenv("KOTAEMON_DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["CURL_CA_BUNDLE"] = ""
```

This safely disables SSL verification for the tiktoken library and requests without affecting other parts of the application.

## Troubleshooting

### Still getting SSL errors?

1. Try restarting Python interpreter (not just the script)
2. Check if the environment variable is actually set: `echo $KOTAEMON_DISABLE_SSL_VERIFY`
3. Try Solution 4 (local cache) instead
4. Check if you're behind a proxy that needs configuration

### Performance Impact?

- **No performance impact** - SSL verification is only needed at connection establishment
- Disabling it may actually improve initial download speed slightly

### Does this affect security for the entire application?

- No - it only affects HTTPS requests made by tiktoken and requests library
- Other secure operations (LLM API calls, etc.) continue to use SSL normally

## Questions or Issues?

If you continue to face SSL issues:
1. Check your firewall/proxy settings with your IT department
2. Request that your organization's SSL certificate be added to system CA bundle
3. Use Solution 5 to configure proxy authentication
