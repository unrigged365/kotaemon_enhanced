#!/usr/bin/env python
"""Wrapper to run the app with SSL verification disabled"""
import ssl
import os
import sys

# Disable SSL verification globally for requests
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

# Monkey patch SSL
ssl._create_default_https_context = ssl._create_unverified_context

# Now import and run the app
from app import app as gradio_app

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    gradio_app.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
    )
