#!/bin/sh
cd "$(dirname "${BASH_SOURCE[0]:-$0}")"
screen uv run main.py 
