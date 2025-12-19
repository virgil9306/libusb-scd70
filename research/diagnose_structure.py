import usb.core
import usb.util
import time
import numpy as np
import threading
import random

# SC-D70
VENDOR_ID = 0x0582
PRODUCT_ID = 0x000c
ENDPOINT_MIDI_OUT = 0x02
INTERFACE_AUDIO = 1
ENDPOINT_AUDIO_IN = 0x81

keep_playing = True

def send_midi_note(dev, note, velocity, on=True):
    try:
        cin = 0x09 if on else 0x08
        cmd = 0x90 if on else 0x80
        packet = [cin, cmd, note, velocity]
        dev.write(ENDPOINT_MIDI_OUT, packet, timeout=10)
    except: pass

def midi_slammer_thread(dev):
    print("   >>> MIDI SLAMMER: Playing notes... <<<")
    notes = [60, 64, 67, 72, 48, 52, 55] 
    while keep_playing:
        n = random.choice(notes)
        send_midi_note(dev, n, 100, on=True)
        time.sleep(0.1)
        send_midi_note(dev, n, 0, on=False)
        time.sleep(0.05)

def main():
    global keep_playing
    print("--- SC-D70 GAP VISUALIZER v1.2 (Adaptive) ---")
    
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if not dev: return

    for i in [0, 1, 2]:
        try:
            if dev.is_kernel_driver_active(i): dev.detach_kernel_driver(i)
        except: pass
    
    dev.set_configuration()
    dev.set_interface_altsetting(interface=1, alternate_setting=1)
    
    t = threading.Thread(target=midi_slammer_thread, args=(dev,), daemon=True)
    t.start()
    
    time.sleep(1.0) 
    
    print(">>> CAPTURING...")
    packets = []
    packet_size_found = 0
    
    try:
        # Read raw chunks
        for _ in range(50): 
            # Request 3120, but we might get 2880
            data = dev.read(ENDPOINT_AUDIO_IN, 3120, timeout=1000)
            arr = np.array(data, dtype=np.uint8)
            
            # Smart reshape
            if len(arr) % 288 == 0:
                packet_size_found = 288
                packets.extend(arr.reshape(-1, 288))
            elif len(arr) % 312 == 0:
                packet_size_found = 312
                packets.extend(arr.reshape(-1, 312))
            else:
                 print(f"Warning: Weird check size {len(arr)}")

    except Exception as e:
        print(f"Capture Error: {e}")
    
    keep_playing = False
    print(f"\n>>> Mode Detected: {packet_size_found} bytes/packet")
    
    print(f"Analyzing {len(packets)} packets...")
    print("Pkt# | [Visualization]")
    print("-" * 60)

    for i, pkt in enumerate(packets):
        # Visualize
        scale = len(pkt) / 60
        vis = ""
        for x in range(60):
            start = int(x * scale)
            end = int((x+1) * scale)
            chunk = pkt[start:end]
            if all(c == 0 for c in chunk): vis += " "
            elif any(c == 0 for c in chunk): vis += "."
            else: vis += "#"
            
        print(f"{i:03d} | [{vis}]")
        if i > 400: break 

    usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
