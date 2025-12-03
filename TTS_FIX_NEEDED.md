# TTS Fix Required

## Issue
Piper TTS has a symbol lookup error:
```
./piper/piper/piper: symbol lookup error: libpiper_phonemize.so.1: undefined symbol: espeak_TextToPhonemesWithTerminator
```

This is because Piper needs **espeak-ng 1.52+** but the system has an older version.

## Quick Fix (Requires Sudo)
Run the provided fix script:
```bash
cd /home/stacy/felix/felix
./fix_piper_espeak.sh
```

This will:
1. Download and build espeak-ng 1.52.0
2. Install it to `/usr/local`
3. Test Piper to confirm it works

Takes about 5 minutes.

## Workaround (Until Fix)
If you want to test Felix without voice:
1. Use text-only mode (type in the chat box instead of speaking)
2. Disable TTS responses (or Felix will error when trying to speak)

## What Still Works Without TTS
Everything else works perfectly:
- ✅ Text chat (type to Felix)
- ✅ All 55 tools (weather, web, memory, music, **image generation**)
- ✅ LLM responses
- ✅ Message actions (copy, edit, regenerate, save)
- ✅ ComfyUI integration
- ✅ Image generation

You just won't hear Felix speak back.

## Testing After Fix
```bash
# Test Piper directly
echo "Hello, this is a test." | ./piper/piper/piper --model ./piper/piper/voices/en_US-amy-medium.onnx --output_file /tmp/test.wav

# Should create /tmp/test.wav with no errors

# Then start Felix
./run.sh
```

## Status
- **Everything else:** ✅ Working and pushed to GitHub
- **TTS:** ❌ Needs sudo to rebuild espeak-ng (5 min fix when you're home)
