#!/bin/bash
# Start HermitClaw with Python 3.11 (modern TLS support)
# The system Python 3.9 has LibreSSL 2.8.3 which can't do TLS 1.3,
# causing web search failures. Python 3.11 has OpenSSL 3.6.1.

cd "$(dirname "$0")"
exec .venv311/bin/python3.11 hermitclaw/main.py "$@"
