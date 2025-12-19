#!/usr/bin/env python3
"""
SC-D70 MIDI Bridge
Enables MIDI communication with Roland SC-D70 via USB on macOS
"""

import usb.core
import usb.util
import pygame.midi
import time
import sys

# SC-D70 USB IDs
VENDOR_ID = 0x0582
PRODUCT_ID = 0x000c
ENDPOINT_MIDI_OUT = 0x02

# SysEx initialization messages
GS_RESET = [0xF0, 0x41, 0x10, 0x42, 0x12, 0x40, 0x00, 0x7F, 0x00, 0x41, 0xF7]
MASTER_VOL = [0xF0, 0x7F, 0x7F, 0x04, 0x01, 0x00, 0x7F, 0xF7]

def send_sysex(dev, sysex):
    """Send SysEx message via USB MIDI"""
    packets = []
    for i in range(0, len(sysex), 3):
        chunk = sysex[i:i+3]
        cin = 0x07 if len(chunk) == 3 and chunk[2] == 0xF7 else 0x04
        p = [cin, 0, 0, 0]
        for j, b in enumerate(chunk):
            p[1+j] = b
        packets.extend(p)
    try:
        dev.write(ENDPOINT_MIDI_OUT, packets, timeout=100)
    except:
        pass

def main():
    print("=" * 60)
    print("SC-D70 MIDI Bridge")
    print("=" * 60)
    
    # Initialize pygame MIDI
    pygame.midi.init()
    
    # List MIDI inputs
    inputs = [i for i in range(pygame.midi.get_count()) 
              if pygame.midi.get_device_info(i)[2]]
    
    if not inputs:
        print("\nError: No MIDI input devices found!")
        return 1
    
    print("\nAvailable MIDI Inputs:")
    for i in inputs:
        info = pygame.midi.get_device_info(i)
        print(f"  {i}: {info[1].decode()}")
    
    # Select MIDI input
    while True:
        try:
            midi_id = int(input(f"\nSelect MIDI Input [{inputs[0]}]: ") or inputs[0])
            if midi_id in inputs:
                break
            print(f"Invalid selection. Please choose from: {inputs}")
        except ValueError:
            print("Please enter a number.")
    
    # Find SC-D70
    print("\nConnecting to SC-D70...")
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if not dev:
        print("Error: SC-D70 not found!")
        print("Please check:")
        print("  - SC-D70 is powered on")
        print("  - USB cable is connected")
        return 1
    
    # Configure USB device
    for intf in [0, 1, 2]:
        try:
            if dev.is_kernel_driver_active(intf):
                dev.detach_kernel_driver(intf)
        except:
            pass
    
    dev.set_configuration()
    dev.set_interface_altsetting(interface=2, alternate_setting=0)
    
    # Initialize SC-D70
    print("Initializing SC-D70...")
    send_sysex(dev, GS_RESET)
    time.sleep(0.2)
    send_sysex(dev, MASTER_VOL)
    
    # Open MIDI input
    midi_in = pygame.midi.Input(midi_id, buffer_size=4096)
    
    print("\n" + "=" * 60)
    print("MIDI Bridge Active!")
    print("=" * 60)
    print(f"Input:  {pygame.midi.get_device_info(midi_id)[1].decode()}")
    print(f"Output: SC-D70 (USB)")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Main MIDI loop
    try:
        while True:
            if midi_in.poll():
                packets = []
                while midi_in.poll():
                    events = midi_in.read(50)
                    for event in events:
                        data = event[0]
                        # Skip timing clock messages
                        if data[0] >= 0xF8:
                            continue
                        # Pack into USB MIDI packet
                        cin = (data[0] >> 4) & 0x0F
                        packets.extend([cin, data[0], data[1], data[2]])
                
                # Send to SC-D70
                if packets:
                    try:
                        dev.write(ENDPOINT_MIDI_OUT, packets, timeout=10)
                    except:
                        pass
            
            time.sleep(0.001)  # 1ms poll interval
            
    except KeyboardInterrupt:
        print("\n\nStopping MIDI bridge...")
    finally:
        midi_in.close()
        pygame.midi.quit()
        usb.util.dispose_resources(dev)
        print("Done.\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
