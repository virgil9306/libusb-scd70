import usb.core
import usb.util
import pygame.midi
import time
import numpy as np

# SC-D70
VENDOR_ID = 0x0582
PRODUCT_ID = 0x000c
INTERFACE_AUDIO = 1
ENDPOINT_AUDIO_IN = 0x81
ENDPOINT_MIDI_OUT = 0x02

GS_RESET = [0xF0, 0x41, 0x10, 0x42, 0x12, 0x40, 0x00, 0x7F, 0x00, 0x41, 0xF7]
MASTER_VOL = [0xF0, 0x7F, 0x7F, 0x04, 0x01, 0x00, 0x7F, 0xF7]
NOTE_ON = [0x90, 69, 100] # A440, High Velocity
NOTE_OFF = [0x80, 69, 0]

def send_midi(dev, packet):
    # USB MIDI Packet: [CIN, B0, B1, B2]
    # CIN 0x9 = Note On, 0x8 = Note Off
    cine = packet[0] >> 4
    payload = [cine, packet[0], packet[1], packet[2]]
    try: dev.write(ENDPOINT_MIDI_OUT, payload, timeout=100)
    except: pass

def send_sysex(dev, sysex):
    packets = []
    for i in range(0, len(sysex), 3):
        chunk = sysex[i:i+3]
        if len(chunk) == 3:
            cin = 0x07 if chunk[2] == 0xF7 else 0x04
            packets.extend([cin, chunk[0], chunk[1], chunk[2]])
        elif len(chunk) == 2:
             packets.extend([0x06, chunk[0], chunk[1], 0x00])
        elif len(chunk) == 1:
             packets.extend([0x05, chunk[0], 0x00, 0x00])
    try: dev.write(ENDPOINT_MIDI_OUT, packets, timeout=100)
    except: pass

def decode_stream(raw_bytes, bit_depth, endian, channels):
    # bit_depth: 16, 24, 32
    # endian: 'little', 'big'
    # channels: 1, 2, 4
    
    dt = None
    bytes_per_sample = bit_depth // 8
    
    if bit_depth == 16:
        dt = np.int16
        if endian == 'big': dt = np.dtype('>i2')
        else: dt = np.dtype('<i2')
        samples = np.frombuffer(raw_bytes, dtype=dt)
        
    elif bit_depth == 32:
        dt = np.int32
        if endian == 'big': dt = np.dtype('>i4')
        else: dt = np.dtype('<i4')
        samples = np.frombuffer(raw_bytes, dtype=dt)
        
    elif bit_depth == 24:
        # Custom 24-bit unpack
        raw = np.frombuffer(raw_bytes, dtype=np.uint8)
        # Pad to 4 bytes? No, packed 3 bytes usually.
        # Length check
        if len(raw) % 3 != 0: raw = raw[:len(raw)-(len(raw)%3)]
        
        raw = raw.reshape(-1, 3)
        if endian == 'little':
            # lo, mid, hi
            # extend to 4 bytes (lo, mid, hi, 0) ? or (0, lo, mid, hi)?
            # Easier: manual shift
            samples = (raw[:,0].astype(np.int32) | 
                       (raw[:,1].astype(np.int32) << 8) | 
                       (raw[:,2].astype(np.int32) << 16))
            # Sign extend
            samples[samples >= 0x800000] -= 0x1000000
        else:
            # hi, mid, lo
            samples = ((raw[:,0].astype(np.int32) << 16) | 
                       (raw[:,1].astype(np.int32) << 8) | 
                       raw[:,2].astype(np.int32))
            samples[samples >= 0x800000] -= 0x1000000
    
    # Normalize
    samples = samples.astype(np.float32)
    
    # De-interleave
    # We only care about Channel 1 for smoothness check
    # But if stride is wrong, Ch1 will be garbage.
    
    if len(samples) % channels != 0:
        samples = samples[:len(samples)-(len(samples)%channels)]
        
    frames = samples.reshape(-1, channels)
    ch1 = frames[:, 0]
    
    return ch1

def calculate_score(signal):
    # Heuristic: Smooth Sine Wave has low Total Variation relative to Amplitude.
    # Noise has high TV.
    # Clipped signal has high TV at edges.
    
    if len(signal) < 100: return 0.0
    
    amp = np.max(np.abs(signal))
    if amp == 0: return 0.0
    
    # Normalize
    norm = signal / amp
    
    # Total Variation
    tv = np.mean(np.abs(np.diff(norm)))
    
    # Derivative Variance (Smoothness)
    # Sine wave diff is Cosine (Smooth).
    # White noise diff is Noise (Rough).
    # We want MINIMIZED smoothness metric?
    # Actually, let's look at Zero Crossings vs Length.
    # A440 at 48k has 440 crossings per sec.
    # Noise has thousands.
    
    # Let's use simple autocorrelation or visual score?
    # Let's use TV for now. Lower is smoother.
    # Pure sine at low freq has very low TV (pixel to pixel change is small).
    # White noise has average change of ~0.5.
    
    score = 1.0 / (tv + 1e-9) # Higher is Better (Smoother)
    return score

def render_ascii(signal, width=60):
    # Downsample to width
    if len(signal) == 0: return ""
    step = len(signal) // width
    if step == 0: step = 1
    subs = signal[::step]
    
    # Normalize to -1..1
    m = np.max(np.abs(subs))
    if m == 0: return "_" * width
    norm = subs / m
    
    line = ""
    for v in norm:
        if v > 0.5: line += "▀"
        elif v < -0.5: line += "▄"
        else: line += "-"
    return line

def main():
    print("--- SC-D70 Signal Forensics ---")
    pygame.midi.init()
    
    # Find MIDI
    mid_id = -1
    for i in range(pygame.midi.get_count()):
        inf = pygame.midi.get_device_info(i)
        if inf[2] and b'SC-D70' in inf[1]:
            mid_id = i
            break
    if mid_id == -1:
        # Fallback
        inputs = [i for i in range(pygame.midi.get_count()) if pygame.midi.get_device_info(i)[2]]
        if inputs: mid_id = inputs[0]
        else:
            print("No MIDI Input found for reset.")
            return

    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if not dev: 
        print("USB Device Not Found.")
        return
        
    try:
        if dev.is_kernel_driver_active(1): dev.detach_kernel_driver(1)
    except: pass
    dev.set_configuration()
    dev.set_interface_altsetting(1, 1)
    
    print("1. Sending Test Tone (A440)...")
    send_sysex(dev, GS_RESET)
    time.sleep(0.2)
    send_sysex(dev, MASTER_VOL)
    send_midi(dev, NOTE_ON)
    
    print("2. Capturing USB Audio (1.0s)...")
    raw_buffer = bytearray()
    start_t = time.time()
    packet_count = 0
    
    try:
        while (time.time() - start_t) < 1.0:
            try:
                data = dev.read(ENDPOINT_AUDIO_IN, 3120, timeout=100)
                if data:
                    raw_buffer.extend(data)
                    packet_count += 1
            except usb.core.USBError: pass
    except KeyboardInterrupt: pass
    
    send_midi(dev, NOTE_OFF)
    
    total_bytes = len(raw_buffer)
    print(f"\nCaptured {total_bytes} bytes in {packet_count} reads.")
    print(f"Average Read Size: {total_bytes / packet_count if packet_count else 0:.1f}")
    
    # --- ANALYSIS ---
    print("\n3. Brute-Force Decoding...")
    
    candidates = []
    
    depths = [16, 24, 32]
    endians = ['little', 'big']
    channels = [2, 4] # Mono usually unpacked to stereo anyway
    
    for d in depths:
        for e in endians:
            for c in channels:
                try:
                    sig = decode_stream(raw_buffer, d, e, c)
                    score = calculate_score(sig)
                    candidates.append({
                        'fmt': f"{d}-bit {e} {c}ch",
                        'score': score,
                        'sig': sig[:1000] # Preview
                    })
                except Exception as err:
                    pass
                    
    # Sort by Score Descending
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nTop 3 Probable Formats:")
    for i in range(min(3, len(candidates))):
        c = candidates[i]
        print(f"Rank {i+1}: {c['fmt']} (Score: {c['score']:.1f})")
        print(f"Wave: [{render_ascii(c['sig'])}]")
        print("-" * 60)

    pygame.midi.quit()
    usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
