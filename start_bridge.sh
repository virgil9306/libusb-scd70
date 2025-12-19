#!/bin/bash
# SC-D70 MIDI Bridge Launcher

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run: python3 -m venv venv && ./venv/bin/pip install pyusb pygame numpy"
    exit 1
fi

# Activate virtual environment and run bridge
./venv/bin/python3 midi_bridge.py
