# 🔧 Felix Feature Inventory - Developer Reference

**Purpose:** Quick reference for developers to find where features are implemented and how to use/extend them.

---

## 🎯 CORE VOICE PIPELINE

### Speech-to-Text (STT)

**Location:** `server/stt/whisper.py`

**Key Functions:**
- `get_stt()` - Get or create STT instance (singleton)
- `STT.transcribe(audio_bytes: bytes) -> str` - Transcribe audio

**Implementation:**
```python
from server.stt.whisper import get_stt

stt = await get_stt()
transcript = await stt.transcribe(audio_bytes)
```

**Configuration:** `server/config.py`
- `whisper_model` - Model name (default: "large-v3-turbo")
- `whisper_device` - "cuda", "cpu", or "auto"
- `whisper_compute_type` - "float16", "int8", "int8_float16"
- `whisper_gpu_device` - GPU index (default: 0)

**Dependencies:**
- `faster-whisper` package
- `ctranslate2` for GPU acceleration

**Usage in Pipeline:** `server/main.py:768-771`

---

### Text-to-Speech (TTS)

**Location:** `server/tts/piper_tts.py`

**Key Functions:**
- `get_tts(voice: str = "amy")` - Get TTS instance
- `TTS.synthesize_streaming(text: str)` - Stream audio chunks
- `TTS.synthesize(text: str) -> bytes` - Generate full audio
- `TTS.cancel()` - Cancel ongoing synthesis

**Implementation:**
```python
from server.tts.piper_tts import get_tts

tts = get_tts("amy")
tts.speaking_rate = 1.5  # Speed control
async for chunk in tts.synthesize_streaming("Hello"):
    # Send chunk to client
    pass
```

**Available Voices:**
- `amy` (default)
- `lessac`
- `ryan`

**Configuration:** `server/config.py`
- `tts_engine` - "piper" or "clone"
- `tts_voice` - Voice name

**Voice Speed Control:** Set `tts.speaking_rate` (0.5 - 2.0)

**Usage in Pipeline:** `server/main.py:981-1001`

---

### Voice Activity Detection (VAD)

**Location:** `server/audio/vad.py`

**Key Functions:**
- `create_vad(vad_type, threshold, sample_rate, device)` - Create VAD instance
- `SileroVAD.process_chunk(audio_chunk: bytes) -> tuple` - Returns (is_speech, is_speaking, speech_ended)
- `SileroVAD.reset()` - Reset state

**Implementation:**
```python
from server.audio.vad import create_vad

vad = create_vad(
    vad_type="silero",
    threshold=0.5,
    sample_rate=16000,
    device="cpu"  # Must be CPU to avoid CUDA conflicts
)

is_speech, is_speaking, speech_ended = vad.process_chunk(audio_chunk)
```

**Global Instance:** `server/main.py:533-548` (singleton pattern)

**Barge-in Detection:** `server/main.py:664-697`

**Configuration:** `server/config.py`
- `barge_in_threshold` - Speech detection threshold (0.0-1.0)
- `barge_in_min_speech_ms` - Minimum speech duration

---

### Audio Pipeline

**Location:** `server/main.py:637-1018`

**Key Function:**
- `process_audio_pipeline(client_id, audio_data, session, voice, model, tts_playing, voice_speed)`

**Flow:**
1. VAD processing (`server/main.py:712-714`)
2. Speech end detection (`server/main.py:719`)
3. STT transcription (`server/main.py:768-771`)
4. LLM processing (`server/main.py:824-936`)
5. TTS synthesis (`server/main.py:981-1001`)

**State Machine:** `server/session.py:SessionState`
- `IDLE` → `LISTENING` → `PROCESSING` → `SPEAKING` → `INTERRUPTED`

---

## 🤖 LANGUAGE MODEL (LLM)

**Location:** `server/llm/ollama.py`

**Key Class:** `OllamaClient`

**Key Methods:**
- `chat(messages: list) -> AsyncIterator[dict]` - Streaming chat
- `register_tool(name, description, parameters, handler)` - Register tool
- `clear_tools()` - Clear all tools
- `update_config(backend, base_url, model, api_key)` - Change backend
- `list_models() -> list` - Get available models

**Implementation:**
```python
from server.llm.ollama import get_llm_client

ollama = await get_llm_client()
ollama.model = "llama3.2"
ollama.register_tool("my_tool", "Description", {...}, handler_func)

async for chunk in ollama.chat(messages):
    if chunk["type"] == "text":
        print(chunk["content"])
    elif chunk["type"] == "tool_call":
        print(chunk["name"], chunk["arguments"])
```

**Backend Support:**
- Ollama (default): `server/llm/ollama.py`
- LM Studio: Same client, different URL
- OpenAI-compatible: Same client, different URL
- OpenRouter: Same client, different URL

**Backend Switching:** `server/main.py:1374-1380`

**Configuration:** `server/config.py`
- `llm_backend` - "ollama", "lmstudio", "openai"
- `ollama_url` - Backend URL
- `ollama_model` - Model name
- `ollama_temperature` - Temperature (0.0-2.0)
- `ollama_max_tokens` - Max tokens

**Tool Registration:** `server/main.py:797-804`

---

## 🛠️ TOOL SYSTEM

### Tool Registry

**Location:** `server/tools/registry.py`

**Key Class:** `ToolRegistry`

**Key Methods:**
- `register(name, description, parameters, category)` - Decorator
- `get_tool(name) -> Tool` - Get tool by name
- `list_tools() -> list[Tool]` - List all tools
- `get_tools_for_llm() -> list[dict]` - OpenAI-compatible format

**Creating a Tool:**
```python
from server.tools.registry import tool_registry

@tool_registry.register(
    description="My tool description",
    category="general"
)
async def my_tool(param1: str, param2: int = 10) -> str:
    """Tool docstring."""
    return f"Result: {param1} x {param2}"
```

**Tool Execution:** `server/tools/executor.py`
- `tool_executor.execute(name, arguments) -> ToolResult`

**All Built-in Tools:** `server/tools/builtin/__init__.py`

---

### Date & Time Tools

**Location:** `server/tools/builtin/datetime_tools.py`

**Tools:**
- `get_current_time()` - Current time
- `get_current_date()` - Today's date
- `calculate_date(days, weeks, months, years)` - Date math
- `get_day_of_week(date)` - Day of week
- `time_until(target_date)` - Time until date

**Dependencies:** Python `datetime` module

---

### Weather Tools

**Location:** `server/tools/builtin/weather_tools.py`

**Tools:**
- `get_weather(location)` - Current weather
- `get_forecast(location, days)` - Weather forecast

**API:** Open-Meteo (free, no API key)

**Implementation:** `httpx` async client

---

### Web Tools

**Location:** `server/tools/builtin/web_tools.py`

**Tools:**
- `web_search(query)` - DuckDuckGo search
- `quick_answer(query)` - Quick answers
- `open_url(url)` - Open in browser flyout
- `get_url_content(url)` - Fetch URL content
- `search_images(query)` - Image search
- `search_videos(query)` - Video search

**Browser Flyout:** Returns `{"text": "...", "flyout": {"type": "browser", "content": "url"}}`

**Dependencies:** `duckduckgo-search` package

---

### System Tools

**Location:** `server/tools/builtin/system_tools.py`

**Tools:**
- `get_system_info()` - System info
- `get_resource_usage()` - CPU/memory
- `get_disk_space()` - Disk usage
- `get_uptime()` - System uptime
- `calculate(expression)` - Math
- `tell_joke()` - Random jokes

**Dependencies:** `psutil` package

---

### Music Tools (18 tools!)

**Location:** `server/tools/builtin/music_tools.py`

**MPD Integration:** Uses `python-mpd2` package

**Connection:** `localhost:6600` (configurable via `MPD_HOST`, `MPD_PORT`)

**Tools:**
- `music_play()` - Start playback
- `music_pause()` - Pause
- `music_stop()` - Stop
- `music_next()` - Next track
- `music_previous()` - Previous track
- `music_set_volume(volume)` - Set volume (0-100)
- `music_get_volume()` - Get volume
- `music_search(query)` - Search library
- `music_play_track(track)` - Play specific track
- `music_play_album(album)` - Play album
- `music_play_artist(artist)` - Play artist
- `music_add_to_queue(track)` - Add to queue
- `music_get_queue()` - Get queue
- `music_clear_queue()` - Clear queue
- `music_get_now_playing()` - Current track info
- `music_set_repeat(enabled)` - Repeat mode
- `music_set_random(enabled)` - Shuffle mode
- `music_duck_volume()` - Duck for voice
- `music_restore_volume()` - Restore volume

**Music State:** Global `_music_state` dict in `music_tools.py:31-43`

**Volume Ducking:** `music_tools.py:46-47` (DUCK_VOLUME = 30)

**Frontend Integration:** `frontend/static/music.js`

---

### Image Generation Tools

**Location:** `server/tools/builtin/image_tools.py`

**ComfyUI Integration:** `server/comfy_service.py`

**Tools:**
- `generate_image(prompt, negative_prompt, width, height, steps, cfg_scale)` - Text-to-image
- `generate_image_advanced(...)` - Advanced options
- `upscale_image(image_path, scale)` - Upscale
- `image_to_image(image_path, prompt, ...)` - Image-to-image

**ComfyUI Service:** `server/comfy_service.py`
- `initialize_comfy_service(auto_start)` - Start service
- `get_comfy_service()` - Get service instance
- `shutdown_comfy_service()` - Stop service

**Workflow:** Default workflow in `image_tools.py:18-76`

**Dependencies:** ComfyUI server running (separate process)

---

### Memory Tools

**Location:** `server/tools/builtin/memory_tools.py`

**OpenMemory Integration:** Uses `openmemory` package

**Storage:** SQLite database at `data/memory.db`

**Tools:**
- `remember(content, tags, importance)` - Store memory
- `recall(query, limit, min_relevance)` - Search memories
- `forget(memory_id)` - Delete memory
- `memory_status(sector, limit)` - Get status

**Embeddings:** Uses Ollama `nomic-embed-text` model

**Configuration:** `memory_tools.py:18-41`

**Sectors:** Automatic categorization (work, personal, etc.)

---

### Knowledge Tools

**Location:** `server/tools/builtin/knowledge_tools.py`

**FAISS Integration:** Vector search

**Tools:**
- `search_knowledge(query, dataset, limit)` - Semantic search
- `list_knowledge_datasets()` - List datasets

**Datasets Path:** `/home/stacy/mcpower/datasets` (configurable)

**Dependencies:**
- `faiss-cpu` package
- `sentence-transformers` package

**Model:** `sentence-transformers/all-MiniLM-L6-v2` (default)

**Caching:** Model and index cache in `knowledge_tools.py:121-122`

---

### Onboarding Tools

**Location:** `server/tools/builtin/onboarding_tools.py`

**Tools:**
- `start_onboarding(quick_mode)` - Begin onboarding
- `onboarding_next(user_response)` - Process response
- `complete_onboarding()` - Finish
- `get_onboarding_status()` - Check progress
- `skip_onboarding_category(category)` - Skip category

**Questions:** `onboarding_tools.py:16-41` (organized by category)

**State:** Global `_onboarding_state` dict

**Categories:** basic, work, preferences, interests, goals

**Memory Integration:** Stores responses in memory system

---

### Help Tools

**Location:** `server/tools/builtin/help_tools.py`

**Tools:**
- `list_available_tools(category)` - List tools
- `get_tool_help(tool_name)` - Get tool docs
- `get_system_info()` - System info

---

## 🎨 FRONTEND FEATURES

### Main Application

**Location:** `frontend/static/app.module.js`

**Key Class:** `VoiceAgentApp`

**Initialization:** `app.module.js:59-86`

**WebSocket:** `app.module.js:26-30`, connection at `app.module.js:85`

**Modules Imported:**
- `audio.module.js` - Audio handling
- `settings.js` - Settings management
- `theme.js` - Theme system
- `avatar.js` - Avatar animations
- `notifications.js` - Toast notifications
- `radial-menu.js` - Radial menu
- `music.js` - Music player

---

### Audio Handler

**Location:** `frontend/static/audio.module.js`

**Key Class:** `AudioHandler`

**Methods:**
- `startRecording()` - Start mic capture
- `stopRecording()` - Stop capture
- `playAudio(base64Data)` - Play audio
- `setVolume(volume)` - Volume control (0-1)
- `mute()` / `unmute()` - Mute toggle

**Web Audio API:** Uses `AudioContext`, `MediaStream`, `GainNode`

**Audio Format:** 16kHz PCM16

**Volume Control:** `GainNode` at `audio.module.js`

---

### Theme System

**Location:** `frontend/static/theme.js`

**Functions:**
- `initTheme()` - Initialize
- `applyTheme(name)` - Apply theme
- `nextTheme()` - Next theme
- `prevTheme()` - Previous theme
- `updateThemeSwatches()` - Update UI

**Themes:** 9 themes defined in `frontend/static/style.css`

**Storage:** `localStorage.setItem('theme', name)`

**CSS Variables:** All colors via CSS variables

---

### Avatar System

**Location:** `frontend/static/avatar.js`

**Functions:**
- `initAvatar(element)` - Initialize
- `setAvatarState(state)` - Set state
- `setInterrupted()` - Interrupt animation

**States:** `AVATAR_STATES` enum
- `idle`, `listening`, `thinking`, `speaking`, `happy`, `confused`, `interrupted`

**SVG:** Avatar defined in `frontend/index.html:68-88`

**Animations:** CSS animations in `style.css`

---

### Flyout Panels

**Location:** `frontend/static/app.module.js:1446-1565`

**Types:**
- `browser` - Web browser iframe
- `knowledge` - Knowledge base iframe
- `code` - Code editor
- `terminal` - Terminal interface
- `preview` - URL preview
- `history` - Chat history

**Functions:**
- `toggleFlyout(type)` - Toggle panel
- `openFlyout(type)` - Open panel
- `closeFlyout()` - Close panel
- `setFlyoutContent(type)` - Set content
- `showInFlyout(type, content)` - Show content

**HTML:** `frontend/index.html:224-303`

**CSS:** `frontend/static/style.css:878-1069`

**Tabs:** `frontend/index.html:277-303`

---

### Radial Menu

**Location:** `frontend/static/radial-menu.js`

**Configuration:** `radial-menu.js:7-55`

**Actions:**
- Music, Weather, Search, Memory, Time, Joke

**Functions:**
- `initRadialMenu(sendMessage)` - Initialize
- `openMenu()` - Open menu
- `closeMenu()` - Close menu

**Animations:** Smooth elastic animations with magnetic pointer

**HTML:** `frontend/index.html:98-162`

---

### Music Player UI

**Location:** `frontend/static/music.js`

**Functions:**
- `initMusicPlayer(wsSend)` - Initialize
- `updateMusicState(data)` - Update state
- `handleMusicToolResult(result)` - Handle tool result
- `duckVolume()` - Duck for voice
- `restoreVolume()` - Restore

**State Polling:** `startStatusPolling()` - Polls server every 2s

**HTML:** Music player panel in `frontend/index.html`

**WebSocket Messages:** `music_command` type

---

### Settings Management

**Location:** `frontend/static/settings.js`

**Functions:**
- `loadSettings()` - Load from localStorage
- `saveSettings(settings)` - Save to localStorage
- `getSetting(key)` - Get single setting
- `getAllSettings()` - Get all settings

**Settings Keys:**
- `voice`, `model`, `voiceSpeed`, `theme`, `autoListen`, `showTimestamps`
- `llmBackend`, `llmUrl`, `llmApiKey`

**Persistence:** `localStorage` + server-side per-client files

---

### Notifications

**Location:** `frontend/static/notifications.js`

**Functions:**
- `initNotifications()` - Initialize
- `showError(message, options)` - Error toast
- `showSuccess(message, options)` - Success toast
- `showInfo(message, options)` - Info toast

**Options:**
- `duration` - Auto-dismiss time (ms)
- `persistent` - Don't auto-dismiss

---

## 🔐 AUTHENTICATION

**Location:** `server/auth.py`

**Key Class:** `AuthManager`

**Methods:**
- `register_user(username, password, is_admin)` - Register
- `login(username, password) -> tuple[token, message]` - Login
- `logout(token)` - Logout
- `validate_token(token) -> username` - Validate
- `is_admin(username) -> bool` - Check admin

**Storage:** `data/users.json`, `data/sessions.json`

**Password Hashing:** SHA-256 with salt (`auth.py:54-58`)

**Token Expiry:** 24 hours (`auth.py:24`)

**Admin Protection:** `server/main.py:87-122` (`require_admin` dependency)

---

## 💾 PERSISTENCE

### Session Persistence

**Location:** `server/main.py:551-626`

**Functions:**
- `load_sessions_from_disk()` - Load on startup
- `save_sessions_to_disk()` - Save sessions
- `_save_sessions_to_disk_sync()` - Sync implementation

**Storage:** `data/sessions.json`

**Format:** JSON with client_id → session data

**Background Saves:** `server/main.py:186-196` (configurable interval)

**Atomic Writes:** `server/main.py:613-618` (tmp file + replace + fsync)

**Per-Client History:** `server/storage/local_persistence.py`

---

### Settings Persistence

**Location:** `server/storage/local_persistence.py`

**Functions:**
- `load_user_settings(client_id)` - Load settings
- `save_user_settings(client_id, settings)` - Save settings
- `load_history(client_id)` - Load history
- `save_history(client_id, messages)` - Save history

**Storage:** `data/users/{client_id}/settings.json`, `history.json`

---

## 🧠 TOOL TUTOR SYSTEM

**Location:** `server/tools/tutor/`

**Main Module:** `server/tools/tutor/tutor.py`

**Key Functions:**
- `create_tool_tutor(settings, enabled, data_dir, ...)` - Create tutor
- `prepare_prompt(query, system_prompt, context)` - Enhance prompt
- `process_tool_call(query, response, context)` - Override tool call
- `record_result(query, tool_call, success, error)` - Learn from result

**Components:**
- `confidence.py` - Confidence scoring
- `examples.py` - Example management
- `learning.py` - Learning algorithms
- `voting.py` - Tool selection voting
- `voters.py` - Voter implementations
- `injector.py` - Prompt injection

**Configuration:** `server/config.py`
- `enable_tool_tutor` - Enable/disable
- `tool_confidence_threshold` - Confidence threshold

**Integration:** `server/main.py:812-915` (prompt enhancement, tool call override)

---

## 📊 ADMIN DASHBOARD

**Location:** `frontend/admin.html`, `frontend/static/admin.js`

**Endpoints:**
- `GET /admin.html` - Dashboard page
- `GET /api/admin/health` - Health check
- `GET /api/admin/sessions` - Active sessions
- `GET /api/admin/events` - Event log
- `GET /api/admin/logs` - System logs

**Telemetry:** `server/main.py:60-84`
- `admin_events` - Event buffer (200 events)
- `admin_logs` - Log buffer (200 logs)
- `record_event(type, **payload)` - Record event
- `record_log(level, message, **payload)` - Record log

**Real-time Updates:** `admin.js:194-197` (polling every 2s)

---

## 🌐 API ENDPOINTS

**Location:** `server/main.py`

**REST Endpoints:**
- `GET /` - Main page
- `GET /admin.html` - Admin dashboard
- `GET /health` - Health check
- `GET /api/admin/*` - Admin endpoints (protected)
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/voices` - Available voices
- `GET /api/models` - Available models

**WebSocket:** `server/main.py:1237-1537`
- Endpoint: `/ws`
- Binary messages: Audio data
- JSON messages: Control messages

**Message Types:**
- `start_listening`, `stop_listening`, `interrupt`
- `settings`, `text_message`, `clear_conversation`
- `playback_done`, `test_audio`, `music_command`

---

## 🔧 CONFIGURATION

**Location:** `server/config.py`

**Settings Class:** `Settings` (Pydantic BaseSettings)

**Environment File:** `.env`

**Key Settings:**
- STT: `whisper_model`, `whisper_device`, `whisper_gpu_device`
- LLM: `llm_backend`, `ollama_url`, `ollama_model`
- TTS: `tts_engine`, `tts_voice`
- Server: `server_host`, `server_port`
- Audio: `audio_sample_rate`, `audio_channels`
- Barge-in: `barge_in_threshold`, `barge_in_min_speech_ms`
- Admin: `admin_token`, `enable_auth`
- Persistence: `data_dir`, `session_save_interval`
- Tool Tutor: `enable_tool_tutor`, `tool_confidence_threshold`

**Access:** `from server.config import settings`

---

## 📱 PWA FEATURES

**Manifest:** `frontend/manifest.json`

**Service Worker:** `frontend/sw.js`

**Icons:** `frontend/static/icons/` (192x192, 512x512)

**Installation:** Browser "Add to Home Screen"

---

## 🎯 QUICK REFERENCE

### Adding a New Tool

1. Create file: `server/tools/builtin/my_tool.py`
2. Register tool:
```python
from server.tools.registry import tool_registry

@tool_registry.register(description="...", category="...")
async def my_tool(param: str) -> str:
    return "result"
```
3. Import in `server/tools/builtin/__init__.py`:
```python
from . import my_tool
```

### Adding a New Theme

1. Add CSS variables in `frontend/static/style.css`:
```css
[data-theme="mytheme"] {
    --bg-primary: #color;
    /* ... */
}
```
2. Add to theme list in `frontend/static/theme.js`

### Adding a New Flyout

1. Add tab button in `frontend/index.html:277-303`
2. Add content handler in `frontend/static/app.module.js:1493-1565`
3. Add CSS in `frontend/static/style.css`

### Adding a New LLM Backend

1. Extend `server/llm/ollama.py` or create new client
2. Add backend option in `server/config.py`
3. Add UI option in `frontend/static/app.module.js`

---

## 📚 DEPENDENCIES

**Python:** `requirements.txt`
- `fastapi`, `uvicorn`, `websockets`
- `faster-whisper`, `ctranslate2`
- `torch`, `onnxruntime` (for VAD)
- `edge-tts`, `aiofiles`
- `httpx`, `aiohttp`
- `pydantic`, `structlog`
- `psutil`, `python-mpd2`
- `openmemory`, `faiss-cpu`, `sentence-transformers`

**Frontend:** No build step, vanilla JS ES6 modules

**External Services:**
- Ollama (local LLM)
- MPD (music player daemon)
- ComfyUI (image generation)

---

*Last updated: December 2024*

