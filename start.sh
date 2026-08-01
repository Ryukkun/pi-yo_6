#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]:-$0}")"
git pull
mkdir -p logs
uv sync --upgrade

screen -L -Logfile "./logs/screen-$(date +%Y%m%d_%H%M%S).log" -dmS pi-yo6 uv run main.py 