#!/bin/bash
# Fix Piper espeak-ng dependency by building espeak-ng 1.52+
set -e

echo "Building espeak-ng 1.52+ for Piper compatibility..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download espeak-ng 1.52.0
echo "Downloading espeak-ng 1.52.0..."
wget -q https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz
tar xf 1.52.0.tar.gz
cd espeak-ng-1.52.0

# Install build dependencies if needed
echo "Installing build dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential autoconf automake libtool pkg-config libsonic-dev

# Build and install
echo "Building espeak-ng..."
./autogen.sh
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig

echo "Done! espeak-ng 1.52.0 installed to /usr/local"
echo "Cleaning up..."
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "Testing Piper..."
cd /home/stacy/felix/felix
./piper/piper/piper --model ./piper/piper/voices/en_US-amy-medium.onnx --output_file /tmp/test.wav <<< "Hello, this is a test."
if [ -f /tmp/test.wav ]; then
    echo "SUCCESS! Piper TTS is now working."
    ls -lh /tmp/test.wav
else
    echo "ERROR: Piper still not working"
    exit 1
fi
