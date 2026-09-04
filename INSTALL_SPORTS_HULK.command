#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo
echo "SPORTS HULK STARTER INSTALLED"
echo "Add your private SPORTSGAMEODDS_API_KEY to .env"
echo
read -p "Press Enter to close..."
