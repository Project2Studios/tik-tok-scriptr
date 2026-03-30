#!/bin/bash
# Double-click this file in Finder to launch scriptr
cd "$(dirname "$0")"
echo "Starting scriptr..."
python3 app.py
# Keep terminal open if there's an error
read -p "Press Enter to close..."
