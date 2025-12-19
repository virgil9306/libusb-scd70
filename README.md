# SC-D70 MIDI Bridge

A USB MIDI bridge for the Roland SC-D70 sound module on macOS.

## Quick Start

**Option 1: Menu Bar** (Best for background use)
1. Run `./build_menubar_app.sh`.
2. Launch **SC-D70 Bridge.app**.
3. Select your MIDI input from the 🎹 menu icon.

**Option 2: Terminal Interative** (Best for first-time setup or monitoring)
1. Run `./build_terminal_app.sh`.
2. Launch **SC-D70 MIDI Terminal.app**.

**Option 3: Classic Shell** (Best for experts)
1. Run `./start_bridge.sh`.

## Requirements

- **macOS**: Optimized for CoreMIDI/USB interaction on Mac.
- **Python 3.9+**.
- **SC-D70**: Connected via USB.

## Setup

Initialize your environment:
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## How it works

- **Config**: Settings are stored in `~/.config/sc-d70-bridge/config.json`.
- **Backgrounding**: The "Bridge.app" runs silently in your status bar.
- **Persistence**: Your chosen MIDI input is remembered between sessions.

If you prefer to run it in a terminal, `midi_bridge.py` provides an interactive CLI. Both utilize the same underlying USB bridge logic.

## Repository Structure

- `midi_bridge_menubar.py`: The status bar application source.
- `midi_bridge.py`: The interactive terminal bridge source.
- `build_menubar_app.sh`: Script to package the menu bar version into a macOS `.app`.
- `start_bridge.sh`: Script to launch the terminal version.
- `research/`: Technical analysis, bit-depth discovery, and why USB audio isn't in the main bridge.

## Usage

1. Launch the bridge: `./start_bridge.sh`
2. Select your MIDI input device
3. Play! MIDI will be routed to the SC-D70

Press `Ctrl+C` to stop the bridge.

## Audio

For audio output, use the **SC-D70's analog audio output** (recommended).

USB audio was explored but Python's USB library cannot achieve the required 288 kB/s throughput for 48kHz stereo 24-bit audio. See `research/` folder for detailed findings.

> ⚠️ Important Hardware Note: Analog Ground Loops
> The SC-D70 is a hybrid MIDI/Audio interface. When connecting the RCA Outputs to another USB-powered device (like a guitar processor or audio interface) while the SC-D70 is also connected to your Mac via USB, you will likely experience a significant ground loop buzz (digital noise).
>
> The "Intended" Usage Scenario
> This driver is primarily designed for users who want to use the SC-D70 as a standalone sound module.
> (_i.e._ plug your headphones into the front of the device)
> 
> Best Experience: Connect the SC-D70 to your Mac via USB to send MIDI data using this driver, and monitor the audio directly from the front-panel headphone jack. This avoids the common ground loop issues associated with the rear RCA outputs.
> 
> For External Recording: If you must route the RCA outputs into another USB-powered interface, it is highly recommended to use a 5-pin MIDI cable (via a separate MIDI interface) instead of the USB connection (reason: MIDI uses opto-isolation and doesn't have the same electrical noise that USB causes), or insert a ground loop isolator in the analog signal path.


## Repository Structure

```
.
├── midi_bridge.py      # Main MIDI bridge application
├── start_bridge.sh     # Launcher script
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── research/           # USB audio research and diagnostic tools
│   ├── README.md       # Research findings and documentation
│   ├── analyze_signal.py
│   ├── pitch_compare.py
│   ├── diagnose_structure.py
│   └── usb_reader.c
└── venv/              # Python virtual environment
```

## Troubleshooting

**"SC-D70 not found"**
- Check USB cable connection
- Ensure SC-D70 is powered on
- Try a different USB port

**"No MIDI input devices found"**
- Connect a MIDI controller or enable IAC Driver in Audio MIDI Setup
- Check that your DAW is sending MIDI

**Permission errors**
- You may need to allow USB device access in macOS System Settings

## Research

This project includes extensive research into the SC-D70's USB audio format. Key findings:

- **Audio Format**: 48kHz, Stereo, 24-bit, Little Endian
- **Packet Structure**: Dynamic 288/312 byte framing
- **Python Limitation**: Cannot achieve required 288 kB/s throughput

See `research/README.md` for complete details and diagnostic tools.


## License

MIT
