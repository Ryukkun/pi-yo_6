#!/bin/sh
cd "$(dirname "${BASH_SOURCE[0]:-$0}")"
uv sync --upgrade
screen -mdS "pi-yo6" uv run main.py 
