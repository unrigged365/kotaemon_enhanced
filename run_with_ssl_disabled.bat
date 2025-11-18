@echo off
REM Quick script to run Kotaemon with SSL verification disabled
REM Usage: run_with_ssl_disabled.bat
REM
REM This is a convenience script for development only
REM DO NOT use in production environments

set KOTAEMON_DISABLE_SSL_VERIFY=true

echo Starting Kotaemon with SSL verification disabled...
echo.
echo WARNING: This configuration should only be used for development!
echo.

python app.py %*
