# 🤖 Felix Feature Context for LLM Assistants

**Purpose:** Structured context document for AI assistants to understand all implemented features, their locations, and how to work with them.

**Format:** JSON-like structure with file paths, function names, and implementation details.

---

## SYSTEM_OVERVIEW

```yaml
project_name: "Felix Voice Agent"
type: "Real-time voice assistant with barge-in support"
architecture: "FastAPI backend + Vanilla JS frontend"
deployment: "Local-first, supports cloud"
language: "Python 3.10+ (backend), JavaScript ES6 (frontend)"
```

---

## CORE_VOICE_PIPELINE

### STT_IMPLEMENTATION
```yaml
file: "server/stt/whisper.py"
class: "STT"
singleton: true
function: "get_stt() -> STT"
method: "transcribe(audio_bytes: bytes) -> str"
config_keys:
  - "whisper_model" (default: "large-v3-turbo")
  - "whisper_device" (default: "cuda")
  - "whisper_compute_type" (default: "float16")
  - "whisper_gpu_device" (default: 0)
dependencies: ["faster-whisper", "ctranslate2"]
usage_location: "server/main.py:768-771"
```

### TTS_IMPLEMENTATION
```yaml
file: "server/tts/piper_tts.py"
function: "get_tts(voice: str) -> TTS"
voices: ["amy", "lessac", "ryan"]
methods:
  - "synthesize_streaming(text: str) -> AsyncIterator[bytes]"
  - "synthesize(text: str) -> bytes"
  - "cancel() -> None"
properties:
  - "speaking_rate" (0.5-2.0, controls speed)
config_keys:
  - "tts_engine" (default: "piper")
  - "tts_voice" (default: "amy")
usage_location: "server/main.py:981-1001"
```

### VAD_IMPLEMENTATION
```yaml
file: "server/audio/vad.py"
function: "create_vad(vad_type, threshold, sample_rate, device) -> SileroVAD"
type: "silero"
device: "cpu" (must be CPU to avoid CUDA conflicts)
method: "process_chunk(audio_chunk: bytes) -> tuple[bool, bool, bool]"
returns: "(is_speech, is_speaking, speech_ended)"
global_instance: "server/main.py:533-548"
barge_in_detection: "server/main.py:664-697"
config_keys:
  - "barge_in_threshold" (default: 0.5)
  - "barge_in_min_speech_ms" (default: 150)
```

### AUDIO_PIPELINE
```yaml
file: "server/main.py"
function: "process_audio_pipeline(client_id, audio_data, session, voice, model, tts_playing, voice_speed)"
flow:
  1. "VAD processing (line 712-714)"
  2. "Speech end detection (line 719)"
  3. "STT transcription (line 768-771)"
  4. "LLM processing (line 824-936)"
  5. "TTS synthesis (line 981-1001)"
state_machine: "server/session.py:SessionState"
states: ["IDLE", "LISTENING", "PROCESSING", "SPEAKING", "INTERRUPTED"]
```

---

## LLM_SYSTEM

### LLM_CLIENT
```yaml
file: "server/llm/ollama.py"
class: "OllamaClient"
function: "get_llm_client() -> OllamaClient"
methods:
  - "chat(messages: list) -> AsyncIterator[dict]"
  - "register_tool(name, description, parameters, handler)"
  - "clear_tools()"
  - "update_config(backend, base_url, model, api_key)"
  - "list_models() -> list"
supported_backends: ["ollama", "lmstudio", "openai", "openrouter"]
config_keys:
  - "llm_backend" (default: "ollama")
  - "ollama_url" (default: "http://localhost:11434")
  - "ollama_model" (default: "llama3.2")
  - "ollama_temperature" (default: 0.7)
  - "ollama_max_tokens" (default: 500)
tool_registration: "server/main.py:797-804"
backend_switching: "server/main.py:1374-1380"
```

### TOOL_SYSTEM
```yaml
registry_file: "server/tools/registry.py"
class: "ToolRegistry"
decorator: "@tool_registry.register(description, category, parameters)"
executor_file: "server/tools/executor.py"
function: "tool_executor.execute(name, arguments) -> ToolResult"
builtin_tools_location: "server/tools/builtin/"
total_tools: 56+
```

### TOOL_CATEGORIES
```yaml
datetime_tools:
  file: "server/tools/builtin/datetime_tools.py"
  tools: ["get_current_time", "get_current_date", "calculate_date", "get_day_of_week", "time_until"]
  
weather_tools:
  file: "server/tools/builtin/weather_tools.py"
  tools: ["get_weather", "get_forecast"]
  api: "Open-Meteo (free, no key)"
  
web_tools:
  file: "server/tools/builtin/web_tools.py"
  tools: ["web_search", "quick_answer", "open_url", "get_url_content", "search_images", "search_videos"]
  dependency: "duckduckgo-search"
  flyout_support: true (returns {"flyout": {"type": "browser", "content": "url"}})
  
system_tools:
  file: "server/tools/builtin/system_tools.py"
  tools: ["get_system_info", "get_resource_usage", "get_disk_space", "get_uptime", "calculate", "tell_joke"]
  dependency: "psutil"
  
music_tools:
  file: "server/tools/builtin/music_tools.py"
  tools: 18 tools (play, pause, stop, next, previous, volume, search, queue, etc.)
  integration: "MPD (Music Player Daemon)"
  connection: "localhost:6600"
  dependency: "python-mpd2"
  state_tracking: "global _music_state dict (line 31-43)"
  volume_ducking: "DUCK_VOLUME = 30 (line 47)"
  frontend: "frontend/static/music.js"
  
image_tools:
  file: "server/tools/builtin/image_tools.py"
  tools: ["generate_image", "generate_image_advanced", "upscale_image", "image_to_image"]
  integration: "ComfyUI"
  service_file: "server/comfy_service.py"
  functions: ["initialize_comfy_service", "get_comfy_service", "shutdown_comfy_service"]
  
memory_tools:
  file: "server/tools/builtin/memory_tools.py"
  tools: ["remember", "recall", "forget", "memory_status"]
  integration: "OpenMemory"
  storage: "SQLite at data/memory.db"
  embeddings: "Ollama nomic-embed-text"
  dependency: "openmemory"
  
knowledge_tools:
  file: "server/tools/builtin/knowledge_tools.py"
  tools: ["search_knowledge", "list_knowledge_datasets"]
  integration: "FAISS vector search"
  datasets_path: "/home/stacy/mcpower/datasets"
  dependencies: ["faiss-cpu", "sentence-transformers"]
  model: "sentence-transformers/all-MiniLM-L6-v2"
  caching: "Model and index cache (line 121-122)"
  
onboarding_tools:
  file: "server/tools/builtin/onboarding_tools.py"
  tools: ["start_onboarding", "onboarding_next", "complete_onboarding", "get_onboarding_status", "skip_onboarding_category"]
  questions_location: "line 16-41"
  categories: ["basic", "work", "preferences", "interests", "goals"]
  state: "global _onboarding_state dict"
  memory_integration: true
  
help_tools:
  file: "server/tools/builtin/help_tools.py"
  tools: ["list_available_tools", "get_tool_help", "get_system_info"]
```

---

## FRONTEND_ARCHITECTURE

### MAIN_APPLICATION
```yaml
file: "frontend/static/app.module.js"
class: "VoiceAgentApp"
initialization: "init() method (line 59-86)"
websocket: "wsUrl = ws://${window.location.host}/ws"
modules:
  - "audio.module.js - AudioHandler"
  - "settings.js - Settings management"
  - "theme.js - Theme system"
  - "avatar.js - Avatar animations"
  - "notifications.js - Toast notifications"
  - "radial-menu.js - Radial menu"
  - "music.js - Music player"
```

### AUDIO_HANDLER
```yaml
file: "frontend/static/audio.module.js"
class: "AudioHandler"
methods:
  - "startRecording()"
  - "stopRecording()"
  - "playAudio(base64Data)"
  - "setVolume(volume: 0-1)"
  - "mute() / unmute()"
api: "Web Audio API (AudioContext, MediaStream, GainNode)"
format: "16kHz PCM16"
```

### THEME_SYSTEM
```yaml
file: "frontend/static/theme.js"
functions: ["initTheme", "applyTheme", "nextTheme", "prevTheme", "updateThemeSwatches"]
themes: 9 themes (midnight, emerald, sunset, cyberpunk, ocean, forest, lavender, rose, slate)
storage: "localStorage.setItem('theme', name)"
css_file: "frontend/static/style.css"
implementation: "CSS variables"
```

### AVATAR_SYSTEM
```yaml
file: "frontend/static/avatar.js"
functions: ["initAvatar", "setAvatarState", "setInterrupted"]
states: ["idle", "listening", "thinking", "speaking", "happy", "confused", "interrupted"]
svg_location: "frontend/index.html:68-88"
animations: "CSS animations in style.css"
```

### FLYOUT_PANELS
```yaml
file: "frontend/static/app.module.js"
functions: ["toggleFlyout", "openFlyout", "closeFlyout", "setFlyoutContent", "showInFlyout"]
types:
  - "browser - Web browser iframe"
  - "knowledge - Knowledge base iframe"
  - "code - Code editor"
  - "terminal - Terminal interface"
  - "preview - URL preview"
  - "history - Chat history"
html_location: "frontend/index.html:224-303"
css_location: "frontend/static/style.css:878-1069"
tabs_location: "frontend/index.html:277-303"
```

### RADIAL_MENU
```yaml
file: "frontend/static/radial-menu.js"
config_location: "line 7-55"
actions: ["music", "weather", "search", "memory", "time", "joke"]
functions: ["initRadialMenu", "openMenu", "closeMenu"]
html_location: "frontend/index.html:98-162"
features: ["smooth animations", "magnetic pointer tracking"]
```

### MUSIC_PLAYER_UI
```yaml
file: "frontend/static/music.js"
functions: ["initMusicPlayer", "updateMusicState", "handleMusicToolResult", "duckVolume", "restoreVolume"]
polling: "startStatusPolling() - polls every 2s"
websocket_message_type: "music_command"
html_location: "frontend/index.html (music player panel)"
```

### SETTINGS_MANAGEMENT
```yaml
file: "frontend/static/settings.js"
functions: ["loadSettings", "saveSettings", "getSetting", "getAllSettings"]
storage: "localStorage + server-side per-client files"
keys: ["voice", "model", "voiceSpeed", "theme", "autoListen", "showTimestamps", "llmBackend", "llmUrl", "llmApiKey"]
server_persistence: "server/storage/local_persistence.py"
```

### NOTIFICATIONS
```yaml
file: "frontend/static/notifications.js"
functions: ["initNotifications", "showError", "showSuccess", "showInfo"]
options: ["duration (ms)", "persistent (bool)"]
```

---

## AUTHENTICATION

```yaml
file: "server/auth.py"
class: "AuthManager"
methods:
  - "register_user(username, password, is_admin)"
  - "login(username, password) -> tuple[token, message]"
  - "logout(token)"
  - "validate_token(token) -> username"
  - "is_admin(username) -> bool"
storage:
  - "data/users.json"
  - "data/sessions.json"
password_hashing: "SHA-256 with salt (line 54-58)"
token_expiry: "24 hours (line 24)"
admin_protection: "server/main.py:87-122 (require_admin dependency)"
```

---

## PERSISTENCE

### SESSION_PERSISTENCE
```yaml
file: "server/main.py"
functions:
  - "load_sessions_from_disk() - line 555"
  - "save_sessions_to_disk() - line 623"
  - "_save_sessions_to_disk_sync() - line 596"
storage: "data/sessions.json"
format: "JSON with client_id -> session data"
background_saves: "line 186-196 (configurable interval)"
atomic_writes: "line 613-618 (tmp file + replace + fsync)"
per_client_history: "server/storage/local_persistence.py"
```

### SETTINGS_PERSISTENCE
```yaml
file: "server/storage/local_persistence.py"
functions:
  - "load_user_settings(client_id)"
  - "save_user_settings(client_id, settings)"
  - "load_history(client_id)"
  - "save_history(client_id, messages)"
storage:
  - "data/users/{client_id}/settings.json"
  - "data/users/{client_id}/history.json"
```

---

## TOOL_TUTOR_SYSTEM

```yaml
location: "server/tools/tutor/"
main_file: "server/tools/tutor/tutor.py"
function: "create_tool_tutor(settings, enabled, data_dir, ...)"
methods:
  - "prepare_prompt(query, system_prompt, context)"
  - "process_tool_call(query, response, context)"
  - "record_result(query, tool_call, success, error)"
components:
  - "confidence.py - Confidence scoring"
  - "examples.py - Example management"
  - "learning.py - Learning algorithms"
  - "voting.py - Tool selection voting"
  - "voters.py - Voter implementations"
  - "injector.py - Prompt injection"
config_keys:
  - "enable_tool_tutor (default: True)"
  - "tool_confidence_threshold (default: 0.7)"
integration: "server/main.py:812-915"
```

---

## ADMIN_DASHBOARD

```yaml
frontend: "frontend/admin.html"
javascript: "frontend/static/admin.js"
endpoints:
  - "GET /admin.html"
  - "GET /api/admin/health"
  - "GET /api/admin/sessions"
  - "GET /api/admin/events"
  - "GET /api/admin/logs"
telemetry: "server/main.py:60-84"
buffers:
  - "admin_events (200 events max)"
  - "admin_logs (200 logs max)"
functions:
  - "record_event(type, **payload)"
  - "record_log(level, message, **payload)"
polling: "admin.js:194-197 (every 2s)"
```

---

## API_ENDPOINTS

```yaml
file: "server/main.py"
rest_endpoints:
  - "GET / - Main page"
  - "GET /admin.html - Admin dashboard"
  - "GET /health - Health check"
  - "GET /api/admin/* - Admin endpoints (protected)"
  - "POST /api/auth/login - Login"
  - "POST /api/auth/logout - Logout"
  - "GET /api/voices - Available voices"
  - "GET /api/models - Available models"
websocket:
  endpoint: "/ws"
  location: "server/main.py:1237-1537"
  message_types:
    binary: "Audio data"
    json: "Control messages (start_listening, stop_listening, interrupt, settings, text_message, clear_conversation, playback_done, test_audio, music_command)"
```

---

## CONFIGURATION

```yaml
file: "server/config.py"
class: "Settings (Pydantic BaseSettings)"
env_file: ".env"
key_settings:
  stt: ["whisper_model", "whisper_device", "whisper_gpu_device"]
  llm: ["llm_backend", "ollama_url", "ollama_model"]
  tts: ["tts_engine", "tts_voice"]
  server: ["server_host", "server_port"]
  audio: ["audio_sample_rate", "audio_channels"]
  barge_in: ["barge_in_threshold", "barge_in_min_speech_ms"]
  admin: ["admin_token", "enable_auth"]
  persistence: ["data_dir", "session_save_interval"]
  tool_tutor: ["enable_tool_tutor", "tool_confidence_threshold"]
access: "from server.config import settings"
```

---

## PWA_FEATURES

```yaml
manifest: "frontend/manifest.json"
service_worker: "frontend/sw.js"
icons: "frontend/static/icons/ (192x192, 512x512)"
installation: "Browser 'Add to Home Screen'"
```

---

## QUICK_REFERENCE_PATTERNS

### ADDING_NEW_TOOL
```yaml
steps:
  1. "Create file: server/tools/builtin/my_tool.py"
  2. "Register tool with @tool_registry.register decorator"
  3. "Import in server/tools/builtin/__init__.py"
pattern: |
  from server.tools.registry import tool_registry
  
  @tool_registry.register(description="...", category="...")
  async def my_tool(param: str) -> str:
      return "result"
```

### ADDING_NEW_THEME
```yaml
steps:
  1. "Add CSS variables in frontend/static/style.css"
  2. "Add to theme list in frontend/static/theme.js"
pattern: |
  [data-theme="mytheme"] {
      --bg-primary: #color;
  }
```

### ADDING_NEW_FLYOUT
```yaml
steps:
  1. "Add tab button in frontend/index.html:277-303"
  2. "Add content handler in frontend/static/app.module.js:1493-1565"
  3. "Add CSS in frontend/static/style.css"
```

### ADDING_NEW_LLM_BACKEND
```yaml
steps:
  1. "Extend server/llm/ollama.py or create new client"
  2. "Add backend option in server/config.py"
  3. "Add UI option in frontend/static/app.module.js"
```

---

## DEPENDENCIES

```yaml
python: "requirements.txt"
packages:
  - "fastapi, uvicorn, websockets"
  - "faster-whisper, ctranslate2"
  - "torch, onnxruntime (for VAD)"
  - "edge-tts, aiofiles"
  - "httpx, aiohttp"
  - "pydantic, structlog"
  - "psutil, python-mpd2"
  - "openmemory, faiss-cpu, sentence-transformers"
frontend: "No build step, vanilla JS ES6 modules"
external_services:
  - "Ollama (local LLM)"
  - "MPD (music player daemon)"
  - "ComfyUI (image generation)"
```

---

## FEATURE_COUNTS

```yaml
total_tools: 56+
music_tools: 18
themes: 9
flyout_types: 6
llm_backends: 4
tts_voices: 3
avatar_states: 7
radial_menu_actions: 6
```

---

## IMPORTANT_NOTES

```yaml
code_organization:
  - "Backend: server/ directory"
  - "Frontend: frontend/ directory"
  - "Tools: server/tools/builtin/"
  - "Config: server/config.py"
  - "Main entry: server/main.py"

async_patterns:
  - "All I/O operations are async"
  - "Use asyncio.to_thread() for blocking operations"
  - "Fire-and-forget saves use asyncio.create_task()"

state_management:
  - "Session state: server/session.py"
  - "Music state: server/tools/builtin/music_tools.py:31-43"
  - "Onboarding state: server/tools/builtin/onboarding_tools.py:44-50"

error_handling:
  - "Structured logging with structlog"
  - "Try-except blocks around all tool executions"
  - "User-friendly error messages sent to client"

performance:
  - "VAD runs on CPU (avoids CUDA conflicts)"
  - "STT on GPU #1"
  - "LLM on GPU #2"
  - "TTS on CPU"
  - "Background saves don't block main thread"
```

---

*This document should be updated whenever new features are added.*

