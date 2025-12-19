# SC-D70 USB Audio Research

This folder contains research and diagnostic tools used to analyze the SC-D70's USB audio format.

## Key Findings

### Audio Format (Confirmed)
- **Sample Rate**: 48000 Hz (hardware switch dependent)
- **Bit Depth**: 24-bit
- **Channels**: 2 (Stereo)
- **Endianness**: Little Endian
- **Bytes per Frame**: 6 (3 bytes × 2 channels)

### Packet Structure
- **Active Audio**: 288-byte packets (pure payload)
- **Idle/Decay**: 312-byte packets (288 bytes payload + 24 bytes zero-padding)
- The device dynamically switches between these modes

### Throughput Requirements
- **48kHz Stereo 24-bit**: 288 kB/s (48000 × 6 bytes)
- **Python USB Limitation**: ~213 kB/s achieved (25% shortfall)
- **Conclusion**: Python's `pyusb` cannot maintain required throughput

## Research Tools

### `analyze_signal.py`
Forensic tool that captures USB audio and brute-force tests all possible format combinations (bit depth, endianness, channels) to identify the correct format. Uses waveform smoothness scoring to rank candidates.

**Key Result**: Confirmed 24-bit Little Endian Stereo (Score: 45.5)

### `pitch_compare.py`
A/B comparison tool that plays the same note through the SC-D70 bridge and a reference tone generator at different sample rates to identify correct pitch.

**Key Result**: Confirmed 48000 Hz sample rate

### `diagnose_structure.py`
Packet structure analyzer that visualizes USB packet sizes and identifies the 288/312 byte switching pattern.

**Key Result**: Discovered dynamic packet framing behavior

### `usb_reader.c` + `setup.py`
Attempted C extension to bypass Python's USB throughput limitations. Compiled successfully but had compatibility issues with pyusb's internal handle representation.

**Status**: Incomplete - would need deeper integration with libusb

## Why USB Audio Failed

Python's `pyusb` library cannot achieve the required 288 kB/s throughput for 48kHz stereo 24-bit audio. Multiple optimization attempts were made:

1. **Large buffers** (1000-item queues) - Helped but insufficient
2. **Aggressive threading** - Minimal improvement
3. **C extension** - Compilation successful, integration failed
4. **Larger USB reads** (62400 bytes) - Still couldn't keep up

The fundamental issue is Python's overhead in USB I/O operations.

## Future Directions

To achieve working USB audio from the SC-D70, one would likely need:

1. **macOS DriverKit Extension**: A proper kernel driver written in C/C++
2. **Code Signing**: Apple Developer certificate for driver installation
3. **USB Audio Class Compliance**: Implement UAC2 protocol properly
4. **CoreAudio Integration**: Bridge to macOS audio system

This is a substantial project (weeks of development) requiring:
- Kernel driver development expertise
- macOS driver architecture knowledge
- USB Audio Class specification understanding
- Apple code signing and notarization

## Practical Solution

**Use analog audio output** from the SC-D70 and the MIDI bridge for control. This provides:
- Perfect audio quality (no USB limitations)
- Low latency
- Reliable operation
- Simple setup

The MIDI bridge (`../midi_bridge.py`) works perfectly for MIDI communication.
