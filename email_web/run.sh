#!/usr/bin/env bash

# Navigate to project root (just in case)
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Export environment variables
export FLASK_APP=app.py
export FLASK_ENV=development   # or production

# Run Flask on a stable port
flask run --host=127.0.0.1 --port=5000