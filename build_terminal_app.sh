#!/bin/bash
# Build SC-D70 MIDI Bridge Terminal App

echo "Building SC-D70 MIDI Terminal.app..."

# Create app bundle structure
APP_NAME="SC-D70 MIDI Terminal"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy Python script
cp midi_bridge.py "$RESOURCES_DIR/"

# Create launcher script that opens in Terminal
cat > "$MACOS_DIR/SC-D70 MIDI Terminal" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../Resources"

# Check if virtual environment exists
VENV_PATH="../../../venv"
if [ ! -d "$VENV_PATH" ]; then
    osascript -e 'display dialog "Virtual environment not found!\n\nPlease run setup first:\n\ncd to the repository folder and run:\npython3 -m venv venv\n./venv/bin/pip install pyusb pygame numpy" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

# Run MIDI bridge in a new Terminal window
osascript <<APPLESCRIPT
tell application "Terminal"
    activate
    do script "cd '$(pwd)'; ../../../venv/bin/python3 midi_bridge.py; exit"
end tell
APPLESCRIPT
EOF

chmod +x "$MACOS_DIR/SC-D70 MIDI Terminal"

# Create Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>SC-D70 MIDI Terminal</string>
    <key>CFBundleIdentifier</key>
    <string>com.dante.sc-d70-midi-terminal</string>
    <key>CFBundleName</key>
    <string>SC-D70 MIDI Terminal</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
EOF

echo "✓ Created $APP_DIR"
echo ""
echo "To use:"
echo "  1. Double-click '$APP_DIR' to launch in a new terminal"
echo "  2. Or drag it into an existing terminal"
echo ""
