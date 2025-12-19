import usb.core
import usb.util
import pygame.midi
import sounddevice as sd
import numpy as np
import time
import threading
import queue

VENDOR_ID = 0x0582
PRODUCT_ID = 0x000c
ENDPOINT_AUDIO_IN = 0x81
ENDPOINT_MIDI_OUT = 0x02

GS_RESET = [0xF0, 0x41, 0x10, 0x42, 0x12, 0x40, 0x00, 0x7F, 0x00, 0x41, 0xF7]
MASTER_VOL = [0xF0, 0x7F, 0x7F, 0x04, 0x01, 0x00, 0x7F, 0xF7]
NOTE_ON = [0x90, 69, 100]  # A440
NOTE_OFF = [0x80, 69, 0]

audio_queue = queue.Queue(maxsize=300)
keep_running = True

def send_sysex(dev, sysex):
    packets = []
    for i in range(0, len(sysex), 3):
        chunk = sysex[i:i+3]
        cin = 0x07 if len(chunk) == 3 and chunk[2] == 0xF7 else 0x04
        p = [cin, 0, 0, 0]
        for j, b in enumerate(chunk): p[1+j] = b
        packets.extend(p)
    try: dev.write(ENDPOINT_MIDI_OUT, packets, timeout=100)
    except: pass

def send_midi(dev, msg):
    try: dev.write(ENDPOINT_MIDI_OUT, [(msg[0]>>4)&0xF, msg[0], msg[1], msg[2]], timeout=100)
    except: pass

def pcm24_to_float32(data_bytes):
    raw = np.frombuffer(data_bytes, dtype=np.uint8).reshape(-1, 3)
    int_vals = (raw[:, 0].astype(np.int32) |
                (raw[:, 1].astype(np.int32) << 8) |
                (raw[:, 2].astype(np.int32) << 16))
    int_vals[int_vals >= 0x800000] -= 0x1000000
    return int_vals.astype(np.float32) / 8388608.0

def audio_callback(outdata, frames, time_info, status):
    out_ptr = 0
    while out_ptr < frames:
        try:
            chunk = audio_queue.get_nowait()
            remaining = frames - out_ptr
            if len(chunk) > remaining:
                outdata[out_ptr:] = chunk[:remaining]
                out_ptr = frames
            else:
                outdata[out_ptr:out_ptr+len(chunk)] = chunk
                out_ptr += len(chunk)
        except queue.Empty:
            outdata[out_ptr:] = 0
            break

def processing_thread(dev, rate):
    global keep_running
    while keep_running:
        try:
            chunk = dev.read(ENDPOINT_AUDIO_IN, 3120, timeout=100)
            if not chunk: continue
            
            l = len(chunk)
            if l % 6 != 0: chunk = chunk[:l - (l % 6)]
            
            num_frames = len(chunk) // 6
            raw_frames = np.frombuffer(chunk, dtype=np.uint8).reshape(num_frames, 6)
            stereo_data = raw_frames[:, 0:6].flatten().tobytes()
            float_data = pcm24_to_float32(stereo_data)
            
            if float_data is not None:
                floats = float_data.reshape(-1, 2)
                try: audio_queue.put_nowait(floats)
                except: pass
        except: pass

print("--- SC-D70 Pitch Comparison Test ---\n")
pygame.midi.init()

# Setup
print(sd.query_devices())
print("\nSelect outputs:")
sc_output = int(input("SC-D70 Output (BlackHole): "))
ref_output = int(input("Reference Output (speakers/headphones): "))

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if not dev: exit()
try:
    if dev.is_kernel_driver_active(1): dev.detach_kernel_driver(1)
except: pass
dev.set_configuration()
dev.set_interface_altsetting(1, 1)

send_sysex(dev, GS_RESET)
time.sleep(0.2)
send_sysex(dev, MASTER_VOL)

rates_to_test = [32000, 35520, 44100, 48000, 96000]

for rate in rates_to_test:
    print(f"\n{'='*60}")
    print(f"Testing: {rate} Hz")
    print(f"{'='*60}")
    
    # Clear queue
    while not audio_queue.empty():
        try: audio_queue.get_nowait()
        except: break
    
    # Start processing thread
    keep_running = True
    t = threading.Thread(target=processing_thread, args=(dev, rate), daemon=True)
    t.start()
    
    # Wait for buffer
    time.sleep(0.2)
    
    # Start SC-D70 stream
    stream = sd.OutputStream(device=sc_output, samplerate=rate, channels=2, 
                            callback=audio_callback, blocksize=512)
    stream.start()
    
    # Play note through SC-D70
    print(f"1. Playing A440 through SC-D70 at {rate} Hz...")
    send_midi(dev, NOTE_ON)
    time.sleep(1.5)
    send_midi(dev, NOTE_OFF)
    time.sleep(0.5)
    
    stream.stop()
    stream.close()
    keep_running = False
    time.sleep(0.2)
    
    # Play reference tone
    print(f"2. Playing reference A440 through speakers...")
    duration = 1.5
    t = np.linspace(0, duration, int(rate * duration), False)
    tone = np.sin(440.0 * 2 * np.pi * t) * 0.3
    stereo_tone = np.column_stack((tone, tone))
    sd.play(stereo_tone, rate, device=ref_output, blocking=True)
    time.sleep(0.5)
    
    response = input("\nDid they sound the SAME pitch? (y/n/skip): ").lower()
    if response == 'y':
        print(f"\n*** MATCH FOUND: {rate} Hz ***")
        break

pygame.midi.quit()
usb.util.dispose_resources(dev)
print("\nTest complete!")
