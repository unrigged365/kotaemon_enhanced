#!/bin/bash
# Quick script to run Kotaemon with SSL verification disabled
# Usage: ./run_with_ssl_disabled.sh

# This is a convenience script for development only
# DO NOT use in production environments

export KOTAEMON_DISABLE_SSL_VERIFY=true

echo "Starting Kotaemon with SSL verification disabled..."
echo "⚠️  WARNING: This configuration should only be used for development!"
echo ""

python app.py "$@"
