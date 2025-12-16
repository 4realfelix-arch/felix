# Voice Agent Architecture

This document describes the technical architecture of the Voice Agent system.

## System Overview

Voice Agent is a real-time conversational AI assistant with barge-in (interrupt) support. The system is designed for local execution on CPU, with optional GPU acceleration on NVIDIA (CUDA) or AMD (ROCm/HIP) depending on the selected backend.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WEB BROWSER                                    │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────────────┐  │
│  │ Microphone   │  │ Audio Playback │  │ Conversation UI             │  │
│  │ (16kHz PCM)  │  │ (22050Hz WAV)  │  │ + Avatar + Settings         │  │
│  └──────┬───────┘  └───────▲────────┘  └─────────────────────────────┘  │
│         │                  │                                             │
│         └────────┬─────────┘                                             │
│                  │                                                       │
│         WebSocket (binary audio + JSON messages)                         │
└──────────────────┼───────────────────────────────────────────────────────┘
                   │
┌──────────────────┼───────────────────────────────────────────────────────┐
│                  ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI WebSocket Server                      │    │
│  │  • Session management with state machine                         │    │
│  │  • Audio routing and buffering                                   │    │
│  │  • Message dispatching                                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                  │                                                       │
│    ┌─────────────┼─────────────┬──────────────┬───────────────┐         │
│    ▼             ▼             ▼              ▼               │         │
│  ┌─────┐   ┌──────────┐  ┌──────────┐   ┌─────────┐          │         │
│  │ VAD │   │   STT    │  │   LLM    │   │   TTS   │          │         │
│  │     │   │          │  │          │   │         │          │         │
│  │Silero│   │faster-whisper│  │ Ollama   │   │ Piper   │          │         │
│  │ CPU  │   │ GPU/CPU  │  │ GPU/CPU  │   │  CPU    │          │         │
│  └──┬──┘   └────┬─────┘  └────┬─────┘   └────┬────┘          │         │
│     │           │             │              │                │         │
│     └───────────┴─────────────┴──────────────┴────────────────┘         │
│                              │                                           │
│                     ┌────────┴────────┐                                  │
│                     │  Tool Executor  │                                  │
│                     │  (19+ tools)    │                                  │
│                     └─────────────────┘                                  │
│                                                                          │
│                                              Voice Agent Server          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Frontend (Browser)

The frontend is a Progressive Web App (PWA) built with vanilla JavaScript ES6 modules.

**Key Components:**

| Module | File | Purpose |
|--------|------|---------|
| App | `app.module.js` | Main orchestration, WebSocket, state management |
| Audio | `audio.module.js` | Mic capture, playback, volume control via GainNode |
| Settings | `settings.js` | LocalStorage persistence, defaults |
| Theme | `theme.js` | 9 color themes, CSS variable switching |
| Avatar | `avatar.js` | Animated avatar with expressions |
| Notifications | `notifications.js` | Toast messages |
| Utils | `utils.js` | Debounce, formatting helpers |

**Audio Pipeline (Client):**

```
Microphone → MediaStream → AudioWorklet → PCM16 → WebSocket
                                              ↓
                                        Binary frames
                                        [1 byte flag][audio]
                                              ↓
WebSocket → Base64 decode → AudioContext → GainNode → Speakers
```

### 2. Backend Server

FastAPI async server with WebSocket support.

**`server/main.py`** - Entry point:
- WebSocket endpoint at `/ws`
- Static file serving
- Message routing
- Audio pipeline orchestration via `process_audio_pipeline()`

**`server/session.py`** - Session management:
- `Session` class with state machine
- `SessionState` enum: `IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`, `INTERRUPTED`
- `_processing_lock` for thread safety
- Conversation history storage

**`server/config.py`** - Configuration:
- Pydantic `Settings` class
- Environment variable loading
- Model paths, GPU device selection

### 3. Audio Components

**`server/audio/vad.py`** - Voice Activity Detection:
- Silero VAD model (PyTorch)
- Processes 512-sample chunks at 16kHz
- Returns probability of speech
- Tracks speech state with hysteresis
- Runs on CPU (<10ms latency)

**`server/audio/buffer.py`** - Audio buffering:
- Circular buffer for audio data
- Pre-roll buffer for capturing speech before VAD triggers
- Chunk management for STT

### 4. Speech-to-Text

**`server/stt/whisper.py`** - Whisper integration:
- Uses `faster-whisper` (CTranslate2) for low-latency transcription
- STT backend and runtime are controlled by env/settings (see `server/config.py`): `STT_BACKEND`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`, `WHISPER_MODEL`

```python
# Typical call path
stt = await get_stt()
text = await stt.transcribe(audio_pcm16_bytes)
```

### 5. Language Model

**`server/llm/ollama.py`** - Ollama client:
- Async httpx client
- Streaming responses via Server-Sent Events
- Tool calling support
- System prompt with tool definitions

**`server/llm/conversation.py`** - Context management:
- Conversation history with role/content pairs
- Token truncation for context window
- Tool call/response tracking

### 6. Text-to-Speech

**`server/tts/piper_tts.py`** - Piper integration:
- Subprocess wrapper for Piper binary
- Voices: `amy`, `lessac`, `ryan`
- Outputs 22050Hz WAV audio
- `length_scale` parameter for speed control (0.5x-2.0x)

```python
# Piper CLI invocation
piper/piper/piper \
    --model piper/piper/voices/en_US-amy-medium.onnx \
    --output_file /tmp/output.wav \
    --length_scale 1.0
```

### 7. Tools

**`server/tools/registry.py`** - Tool registration:
- `@tool_registry.register()` decorator
- Auto-infers parameters from type hints
- Generates OpenAI-compatible tool definitions

**`server/tools/executor.py`** - Execution:
- Async tool execution
- Error handling and timeout
- Result formatting for LLM

**Built-in Tools** (`server/tools/builtin/`):
- `datetime_tools.py` - Time, date, calculations
- `weather_tools.py` - Open-Meteo API integration
- `web_tools.py` - DuckDuckGo search, URL opening
- `system_tools.py` - System info, resource usage

## Data Flow

### Conversation Flow

```
1. User speaks into microphone
   │
2. Browser captures 16kHz PCM16 audio
   │
3. WebSocket sends binary frames to server
   │                [1 byte TTS flag][PCM16 data]
   │
4. VAD analyzes audio chunks
   │                If speech detected → state = LISTENING
   │                If silence >800ms → state = PROCESSING
   │
5. STT transcribes buffered audio
   │                STT backend (depends on `STT_BACKEND`)
   │
6. LLM generates response
   │                Ollama with streaming
   │                May call tools
   │
7. TTS synthesizes audio
   │                Piper at 22050Hz
   │
8. Server streams audio back
   │                Base64 in JSON messages
   │
9. Browser plays audio
   │                Via AudioContext + GainNode
   │
10. Barge-in detection
    │               VAD still running during playback
    │               If speech → interrupt → back to step 1
```

### State Machine

```
                         ┌─────────────────┐
                         │      IDLE       │
                         └────────┬────────┘
                                  │ start_listening
                                  ▼
         ┌───────────────┌─────────────────┐───────────────┐
         │               │    LISTENING    │               │
         │               └────────┬────────┘               │
         │                        │ speech_ended           │
         │                        ▼                        │
         │               ┌─────────────────┐               │
         │               │   PROCESSING    │               │
         │               └────────┬────────┘               │
         │                        │ response_ready         │
         │                        ▼                        │
         │               ┌─────────────────┐               │
         │      ┌────────│    SPEAKING     │────────┐      │
         │      │        └─────────────────┘        │      │
         │      │                                   │      │
         │ barge_in                           playback_done│
         │      │                                   │      │
         │      ▼                                   │      │
         │ ┌─────────────────┐                      │      │
         │ │   INTERRUPTED   │──────────────────────┴──────┘
         │ └────────┬────────┘
         │          │ resume_listening
         └──────────┘
```

### WebSocket Protocol

**Binary Messages** (audio):
```
[1 byte: TTS flag][N bytes: PCM16 audio]
```
- Flag = 0: Not playing TTS (normal audio)
- Flag = 1: TTS is playing (enables barge-in detection)

**JSON Messages** (control):

Client → Server:
```json
{"type": "start_listening"}
{"type": "stop_listening"}
{"type": "interrupt"}
{"type": "playback_done"}
{"type": "settings", "theme": "midnight", "voice_speed": 100}
{"type": "clear_conversation"}
{"type": "test_audio"}
```

Server → Client:
```json
{"type": "state", "state": "listening"}
{"type": "transcript", "text": "Hello", "is_final": true}
{"type": "response", "text": "Hi there!"}
{"type": "response_chunk", "text": "Hi", "is_first": true}
{"type": "audio", "data": "<base64>"}
{"type": "tool_call", "name": "get_weather", "args": {...}}
{"type": "tool_result", "name": "get_weather", "result": {...}}
{"type": "flyout", "flyout_type": "browser", "content": "https://..."}
{"type": "error", "message": "Something went wrong"}
```

## Hardware Utilization

| Component | Hardware | Notes |
|-----------|----------|-------|
| VAD (Silero) | CPU | Lightweight, <10ms per chunk |
| STT | GPU/CPU | Controlled by `STT_BACKEND` and (for faster-whisper) `WHISPER_DEVICE` |
| LLM (Ollama) | GPU/CPU | Runs as a separate local service (default `http://localhost:11434`) |
| TTS (Piper) | CPU | Fast ONNX runtime, ~50ms |
| WebSocket Server | CPU | Async I/O, minimal overhead |

## Security Considerations

1. **Local-only**: No data leaves the machine
2. **CORS**: Origin validation for WebSocket
3. **No auth**: Designed for single-user local use
4. **Secure context**: Mic requires localhost or HTTPS

## Performance Characteristics

| Operation | Typical Latency |
|-----------|-----------------|
| VAD chunk processing | <10ms |
| STT (5s utterance) | 1-2s |
| LLM first token | 300-500ms |
| LLM streaming | ~50 tokens/sec |
| TTS synthesis (short) | ~50ms |
| End-to-end response | 2-4s |

## Extensibility

### Extensions: Tools + Flyouts

The “extension” model is split into two cooperating parts:

- **Tools (backend modules):** Python functions registered in the tool registry (`server/tools/registry.py`). A tool can be enabled/disabled like a plugin and can return plain text or structured UI output.
- **Flyouts (frontend extension surfaces):** stable UI panels (browser/code/terminal) that act like extension points. Tools can optionally render into a flyout by returning a `flyout` payload; the frontend hosts and renders it.

Think of it like a VS Code extension API: the core app provides a small, stable surface area (tool calling + flyout hosts), and modules plug into it.

**Current implementation (today):**
- Tools are registered by importing modules under `server/tools/builtin/` (see `server/tools/builtin/__init__.py`).
- A tool result may include a flyout instruction that the server forwards to the client, e.g.:

```json
{
   "text": "Opening the page",
   "flyout": {"type": "browser", "content": "https://example.com"}
}
```

**Target setup (user-shareable modules):**
- A **Tool Pack** is a folder you can drop in (or zip/share) that contains:
   - a small **manifest** (metadata + what it provides)
   - one or more Python modules that register tools
   - optional frontend assets/config (if needed)
- The app loads only **enabled** packs (toggle on/off), so the UI feels like “turning extensions on/off”.

Example manifest (shape, not yet enforced by code):

```json
{
   "id": "felix.browser_tools",
   "name": "Browser Tools",
   "version": "0.1.0",
   "description": "Open URLs and show results in a flyout",
   "backend": {"python_module": "server.tools.packs.browser_tools"},
   "tools": ["open_url"],
   "flyouts": ["browser"],
   "optional_deps": []
}
```

Enable/disable can be modeled as a config list of pack IDs: only those IDs are imported/registered and exposed to the LLM.

### Adding New Tools

Tools are registered via decorator in `server/tools/builtin/`:

```python
@tool_registry.register(description="Tool description")
async def my_tool(param: str) -> str:
    return "result"
```

### Adding New Themes

Themes are CSS variable sets in `style.css`:

```css
[data-theme="mytheme"] {
    --bg-primary: #color;
    /* ... */
}
```

### Alternative TTS/STT

The architecture supports swapping components:
- STT: Implement `transcribe(audio_bytes) -> str`
- TTS: Implement `synthesize(text) -> bytes`
- LLM: Implement streaming `chat(messages) -> AsyncIterator[str]`

---

*Last updated: November 27, 2025*
we 