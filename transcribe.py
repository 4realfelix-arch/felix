
import asyncio
import sys
from server.stt.whisper import WhisperSTT

async def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]

    stt = WhisperSTT()
    await stt.initialize()

    try:
        with open(audio_file, "rb") as f:
            audio_data = f.read()
    except FileNotFoundError:
        print(f"Error: Audio file not found at {audio_file}")
        sys.exit(1)

    print(f"Transcribing {audio_file}...")
    transcription = await stt.transcribe(audio_data)
    print("\nTranscription:")
    print(transcription)

if __name__ == "__main__":
    asyncio.run(main())
