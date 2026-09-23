#!/usr/bin/env bash
# Render build script

set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations if needed
# python -m alembic upgrade head
