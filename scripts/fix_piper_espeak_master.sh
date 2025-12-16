#!/bin/bash
# Fix Piper espeak-ng dependency by building latest espeak-ng from master
set -e

echo "Building latest espeak-ng from master for Piper compatibility..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download espeak-ng master
echo "Downloading espeak-ng master branch..."
wget -q https://github.com/espeak-ng/espeak-ng/archive/refs/heads/master.tar.gz
tar xf master.tar.gz
cd espeak-ng-master

# Install build dependencies if needed
echo "Installing build dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential autoconf automake libtool pkg-config libsonic-dev

# Build and install
echo "Building espeak-ng from master..."
./autogen.sh
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig

echo "Done! espeak-ng (master) installed to /usr/local"
echo "Cleaning up..."
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "Testing Piper..."
cd /home/stacy/felix/felix
echo "Hello, this is a test." | ./piper/piper/piper --model ./piper/piper/voices/en_US-amy-medium.onnx --output_file /tmp/test.wav
if [ -f /tmp/test.wav ]; then
    echo "SUCCESS! Piper TTS is now working."
    ls -lh /tmp/test.wav
else
    echo "ERROR: Piper still not working"
    exit 1
fi
