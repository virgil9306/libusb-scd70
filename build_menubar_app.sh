#!/bin/bash
# Build SC-D70 MIDI Bridge Menu Bar App

echo "Building SC-D70 Menu Bar App..."

# Create app bundle structure
APP_NAME="SC-D70 Bridge"
APP_DIR="$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy Python script
cp midi_bridge_menubar.py "$RESOURCES_DIR/"

# Create launcher script that runs in background
cat > "$MACOS_DIR/SC-D70 Bridge" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../Resources"

# Check if virtual environment exists
VENV_PATH="../../../venv"
if [ ! -d "$VENV_PATH" ]; then
    osascript -e 'display dialog "Virtual environment not found!\n\nPlease run setup first:\n\ncd to the repository folder and run:\npython3 -m venv venv\n./venv/bin/pip install pyusb pygame numpy rumps" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

# Run menu bar app
exec "$VENV_PATH/bin/python3" midi_bridge_menubar.py
EOF

chmod +x "$MACOS_DIR/SC-D70 Bridge"

# Create Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>SC-D70 Bridge</string>
    <key>CFBundleIdentifier</key>
    <string>com.dante.sc-d70-bridge</string>
    <key>CFBundleName</key>
    <string>SC-D70 Bridge</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

echo "✓ Created $APP_DIR"
echo ""
echo "Features:"
echo "  • Runs in menu bar (no dock icon)"
echo "  • Select MIDI input from menu"
echo "  • Preferences saved automatically"
echo "  • Auto-reconnect on launch"
echo ""
echo "To use:"
echo "  1. Double-click '$APP_DIR' to launch"
echo "  2. Look for 🎹 icon in menu bar"
echo "  3. Click icon to select MIDI input"
echo ""
