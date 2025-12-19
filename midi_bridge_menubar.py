#!/usr/bin/env python3
"""
SC-D70 MIDI Bridge - Menu Bar App
Runs in the background with a menu bar icon
"""

import rumps
import usb.core
import usb.util
import pygame.midi
import threading
import time
import json
import os

# SC-D70 USB IDs
VENDOR_ID = 0x0582
PRODUCT_ID = 0x000c
ENDPOINT_MIDI_OUT = 0x02

# SysEx initialization messages
GS_RESET = [0xF0, 0x41, 0x10, 0x42, 0x12, 0x40, 0x00, 0x7F, 0x00, 0x41, 0xF7]
MASTER_VOL = [0xF0, 0x7F, 0x7F, 0x04, 0x01, 0x00, 0x7F, 0xF7]

# Preferences and Log files
CONFIG_DIR = os.path.expanduser("~/.config/sc-d70-bridge")
PREFS_FILE = os.path.join(CONFIG_DIR, "config.json")
LOG_FILE = os.path.join(CONFIG_DIR, "bridge.log")

def log(msg):
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

log("--- App Starting ---")

class SC_D70_Bridge(rumps.App):
    def __init__(self):
        super(SC_D70_Bridge, self).__init__("SC-D70", "🎹")
        
        # Initialize pygame MIDI early to get initial list
        try:
            pygame.midi.init()
            log("Pygame MIDI initialized")
        except Exception as e:
            log(f"Pygame MIDI Init Error: {e}")

        # Initialize UI elements
        self.status_item = rumps.MenuItem("Status: Initializing...")
        
        # Create initial MIDI Input menu correctly as a submenu
        self.midi_menu = rumps.MenuItem("MIDI Input")
        # Adding a dummy item ensures rumps treats it as a submenu
        self.midi_menu.add(rumps.MenuItem("Refreshing..."))
        
        self.menu = [
            self.status_item,
            None,
            self.midi_menu,
            None,
            rumps.MenuItem("Reconnect", callback=self.reconnect),
        ]
        
        self.bridge_thread = None
        self.running = False
        self.dev = None
        self.midi_in = None
        self.midi_id = None
        self.prefs = self.load_prefs()
        
        # Start the engine
        self.start_bridge()
        
        # Periodically refresh the MIDI menu to catch new devices
        self.refresh_timer = rumps.Timer(self.periodic_update, 10) # 10s is plenty
        self.refresh_timer.start()

    def periodic_update(self, _):
        """Update menus without restarting the bridge"""
        self.update_midi_menu()

    def load_prefs(self):
        """Load saved preferences"""
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {"midi_id": None}
    
    def save_prefs(self):
        """Save preferences"""
        try:
            if not os.path.exists(CONFIG_DIR):
                os.makedirs(CONFIG_DIR)
            with open(PREFS_FILE, 'w') as f:
                json.dump(self.prefs, f)
        except:
            pass
    
    def send_sysex(self, sysex):
        """Send SysEx message via USB MIDI"""
        if not self.dev:
            return
        packets = []
        for i in range(0, len(sysex), 3):
            chunk = sysex[i:i+3]
            cin = 0x07 if len(chunk) == 3 and chunk[2] == 0xF7 else 0x04
            p = [cin, 0, 0, 0]
            for j, b in enumerate(chunk):
                p[1+j] = b
            packets.extend(p)
        try:
            self.dev.write(ENDPOINT_MIDI_OUT, packets, timeout=100)
        except:
            pass
    
    def get_midi_inputs(self):
        """Get list of available MIDI inputs"""
        # Removed quit/init cycle as it breaks active streams
        inputs = []
        try:
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info and info[2]:  # Is input
                    name = info[1].decode()
                    inputs.append((i, name))
        except Exception as e:
            log(f"Error getting MIDI inputs: {e}")
        return inputs
    
    def update_midi_menu(self):
        """Rebuild the MIDI input submenu"""
        try:
            self.midi_menu.clear()
        except Exception as e:
            log(f"Menu Clear Error: {e}")
            
        inputs = self.get_midi_inputs()
        log(f"Updating MIDI menu with {len(inputs)} devices")
        
        for midi_id, name in inputs:
            item = rumps.MenuItem(name, callback=self.select_midi_callback)
            item.midi_id = midi_id
            if midi_id == self.midi_id:
                item.state = 1
            self.midi_menu.add(item)
    
    def select_midi_callback(self, sender):
        """Callback for selecting a MIDI device from the menu"""
        log(f"Menu selection: {sender.title} (ID: {sender.midi_id})")
        self.select_midi(sender.midi_id)

    def select_midi(self, midi_id):
        """Select MIDI input and restart bridge"""
        self.midi_id = midi_id
        self.prefs["midi_id"] = midi_id
        self.save_prefs()
        self.reconnect(None)
    
    def start_bridge(self):
        """Start the MIDI bridge"""
        log("Attempting to start bridge...")
        if self.running:
            log("Bridge already running, stopping first")
            self.stop_bridge()
        
        # Find SC-D70
        self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if not self.dev:
            log("SC-D70 not found")
            self.status_item.title = "Status: SC-D70 Not Found"
            self.title = "🎹❌"
            self.update_midi_menu()
            return
        
        log("SC-D70 found and connected")
        
        # Configure USB
        for intf in [0, 1, 2]:
            try:
                if self.dev.is_kernel_driver_active(intf):
                    self.dev.detach_kernel_driver(intf)
            except:
                pass
        
        try:
            self.dev.set_configuration()
            self.dev.set_interface_altsetting(interface=2, alternate_setting=0)
            log("USB configuration complete")
        except Exception as e:
            log(f"USB Init Error: {e}")
            self.status_item.title = f"Status: USB Init Error"
            self.update_midi_menu()
            return
        
        # Initialize SC-D70
        self.send_sysex(GS_RESET)
        time.sleep(0.2)
        self.send_sysex(MASTER_VOL)
        log("SC-D70 initialized with GS Reset")
        
        # Get MIDI inputs
        inputs = self.get_midi_inputs()
        if not inputs:
            log("No MIDI inputs available")
            self.status_item.title = "Status: No MIDI Inputs"
            self.title = "🎹⚠️"
            self.update_midi_menu()
            return
        
        # Use saved preference or first input
        self.midi_id = self.prefs.get("midi_id")
        
        # Verify saved ID still exists, otherwise pick first
        available_ids = [inp[0] for inp in inputs]
        if self.midi_id not in available_ids:
            self.midi_id = inputs[0][0]
            log(f"Saved MIDI ID not found, using first available: {self.midi_id}")
        
        # Open MIDI input
        try:
            self.midi_in = pygame.midi.Input(self.midi_id, buffer_size=4096)
            log(f"MIDI input opened: ID {self.midi_id}")
        except Exception as e:
            log(f"MIDI Open Error: {e}")
            self.status_item.title = "Status: MIDI Open Error"
            self.title = "🎹⚠️"
            self.update_midi_menu()
            return
        
        # Update UI
        info = pygame.midi.get_device_info(self.midi_id)
        midi_name = info[1].decode() if info else "Unknown"
        self.status_item.title = f"Status: Running ({midi_name})"
        self.title = "🎹✓"
        self.update_midi_menu()
        
        # Start bridge thread
        self.running = True
        self.bridge_thread = threading.Thread(target=self.bridge_loop, daemon=True)
        self.bridge_thread.start()
        log("Bridge thread started")
    
    def bridge_loop(self):
        """Main MIDI bridge loop"""
        log("Bridge loop entered")
        packet_count = 0
        last_log = time.time()
        
        while self.running:
            try:
                if self.midi_in and self.midi_in.poll():
                    packets = []
                    while self.midi_in.poll():
                        events = self.midi_in.read(50)
                        for event in events:
                            data = event[0]
                            if data[0] >= 0xF8:  # Skip timing clock
                                continue
                            cin = (data[0] >> 4) & 0x0F
                            packets.extend([cin, data[0], data[1], data[2]])
                    
                    if packets and self.dev:
                        try:
                            self.dev.write(ENDPOINT_MIDI_OUT, packets, timeout=10)
                            packet_count += (len(packets) // 4)
                        except Exception as e:
                            log(f"USB Write Error: {e}")
                
                # Heartbeat logging
                if time.time() - last_log > 60:
                    log(f"Bridge heartbeat: processed {packet_count} MIDI packets in last min")
                    packet_count = 0
                    last_log = time.time()
                    
                time.sleep(0.001)
            except Exception as e:
                log(f"Bridge Loop Error: {e}")
                break
        log("Bridge loop exited")
    
    def stop_bridge(self):
        """Stop the MIDI bridge"""
        log("Stopping bridge...")
        self.running = False
        if self.bridge_thread:
            self.bridge_thread.join(timeout=1)
            self.bridge_thread = None
        if self.midi_in:
            try:
                self.midi_in.close()
            except:
                pass
            self.midi_in = None
        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except:
                pass
            self.dev = None
        
        self.status_item.title = "Status: Disconnected"
        self.title = "🎹"
        log("Bridge stopped")
    
    @rumps.clicked("Reconnect")
    def reconnect(self, _):
        """Reconnect to SC-D70"""
        self.stop_bridge()
        time.sleep(0.5)
        self.start_bridge()
    
    def quit_application(self, _):
        """Clean shutdown"""
        self.stop_bridge()
        pygame.midi.quit()
        rumps.quit_application()

if __name__ == "__main__":
    app = SC_D70_Bridge()
    app.run()
