#!/bin/bash
# Voice Agent - Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║         🎙️  Voice Agent               ║"
echo "║    Real-time Voice Assistant          ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

usage() {
    cat <<'USAGE'
Usage:
    ./run.sh [--foreground] [--reload]
  ./run.sh start|stop|restart|status

Default behavior: starts Felix in the background (does NOT hold your terminal).

Options:
  --foreground   Run in the foreground (blocks terminal).
    --reload       Enable uvicorn --reload (useful for active dev; may be less stable).

Commands:
  start          Start in background (same as default).
  stop           Stop the background server started by this script.
  restart        Stop then start.
  status         Print status (pid, listening port) and log location.

Examples:
    ./run.sh
    ./run.sh status
    ./run.sh stop
    ./run.sh restart
    ./run.sh --foreground --reload
USAGE
}

RUN_MODE="start"
FOREGROUND=0
RELOAD=0

case "${1:-}" in
    start|stop|restart|status)
        RUN_MODE="$1"
        shift
        ;;
    "" )
        ;;
    -h|--help)
        usage
        exit 0
        ;;
esac

while [ $# -gt 0 ]; do
    case "$1" in
        --foreground)
            FOREGROUND=1
            ;;
        --reload)
            RELOAD=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${NC}"
            usage
            exit 1
            ;;
    esac
    shift
done

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}Created .env file. Edit it to customize settings.${NC}"
    else
        echo -e "${RED}Warning: No .env.example file found${NC}"
    fi
fi

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
deactivate 2>/dev/null || true
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check if Ollama is running
echo -e "${BLUE}Checking Ollama...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
else
    echo -e "${RED}✗ Ollama is not running${NC}"
    echo -e "${YELLOW}Starting Ollama...${NC}"
    # Try to start Ollama in background
    if command -v ollama &> /dev/null; then
        ollama serve &
        sleep 3
    else
        echo -e "${RED}Ollama not found. Please install from https://ollama.ai${NC}"
        exit 1
    fi
fi

# Check for OpenMemory backend
OPENMEMORY_DIR="/home/stacy/openmemory"
echo -e "${BLUE}Checking OpenMemory...${NC}"
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OpenMemory is running${NC}"
else
    echo -e "${YELLOW}Starting OpenMemory backend...${NC}"
    if [ -d "$OPENMEMORY_DIR/backend" ]; then
        cd "$OPENMEMORY_DIR/backend"
        nohup npx tsx src/server/index.ts > "$OPENMEMORY_DIR/openmemory.log" 2>&1 &
        cd "$SCRIPT_DIR"
        sleep 3
        if curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ OpenMemory started${NC}"
        else
            echo -e "${YELLOW}⚠ OpenMemory failed to start (memory tools will be unavailable)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ OpenMemory not found at $OPENMEMORY_DIR (memory tools will be unavailable)${NC}"
    fi
fi

# Check for MPD (Music Player Daemon)
echo -e "${BLUE}Checking MPD...${NC}"
if systemctl --user is-active mpd > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MPD is running${NC}"
elif mpc status > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MPD is running${NC}"
else
    echo -e "${YELLOW}Starting MPD...${NC}"
    if command -v mpd &> /dev/null; then
        # Try user service first
        if systemctl --user start mpd 2>/dev/null; then
            echo -e "${GREEN}✓ MPD started (user service)${NC}"
        else
            # Try starting directly
            mpd 2>/dev/null || true
            sleep 1
            if mpc status > /dev/null 2>&1; then
                echo -e "${GREEN}✓ MPD started${NC}"
            else
                echo -e "${YELLOW}⚠ MPD failed to start (music tools will be unavailable)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ MPD not installed (music tools will be unavailable)${NC}"
        echo -e "${YELLOW}  Install with: sudo apt install mpd mpc${NC}"
    fi
fi

# Check for required model
MODEL=${OLLAMA_MODEL:-llama3.2}
echo -e "${BLUE}Checking for model: $MODEL${NC}"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo -e "${YELLOW}Model $MODEL not found. Pulling...${NC}"
    ollama pull "$MODEL"
fi
echo -e "${GREEN}✓ Model $MODEL available${NC}"

# Get host and port from environment or defaults
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

PIDFILE="$SCRIPT_DIR/.felix.pid"
LOGFILE="${LOGFILE:-/tmp/felix-uvicorn.log}"
READY_URL="${READY_URL:-http://127.0.0.1:${PORT}/api/auth/user}"
READY_TIMEOUT_SECS="${READY_TIMEOUT_SECS:-15}"

is_running() {
    local pid
    pid="${1:-}"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

print_status() {
    local pid=""
    if [ -f "$PIDFILE" ]; then
        pid=$(cat "$PIDFILE" 2>/dev/null || true)
    fi
    if is_running "$pid"; then
        echo -e "${GREEN}✓ Felix server running${NC} (pid=$pid, url=http://localhost:$PORT)"
        echo -e "${BLUE}Log:${NC} $LOGFILE"
        echo -e "${BLUE}Tips:${NC} ./run.sh status | ./run.sh stop | ./run.sh restart"
    else
        echo -e "${YELLOW}Felix server not running${NC}"
        echo -e "${BLUE}Log:${NC} $LOGFILE"
        echo -e "${BLUE}Tips:${NC} ./run.sh start | ./run.sh --foreground"
    fi
}

stop_server() {
    local pid=""
    if [ -f "$PIDFILE" ]; then
        pid=$(cat "$PIDFILE" 2>/dev/null || true)
    fi
    if ! is_running "$pid"; then
        rm -f "$PIDFILE" 2>/dev/null || true
        return 0
    fi
    echo -e "${YELLOW}Stopping Felix server (pid=$pid)...${NC}"
    kill "$pid" 2>/dev/null || true
    sleep 1
    if is_running "$pid"; then
        echo -e "${YELLOW}Force stopping Felix server (pid=$pid)...${NC}"
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE" 2>/dev/null || true
}

case "$RUN_MODE" in
    status)
        print_status
        exit 0
        ;;
    stop)
        stop_server
        print_status
        exit 0
        ;;
    restart)
        stop_server
        RUN_MODE="start"
        ;;
esac

# Check if port is in use and stop only processes we own.
# (Avoid trying to kill unrelated/privileged processes, and avoid killing client sockets like Chrome.)
PIDS=$(lsof -nP -t -iTCP:$PORT -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo -e "${YELLOW}Port $PORT has listening process(es): $PIDS${NC}"
    OWNED_PIDS=""
    for pid in $PIDS; do
        if [ "$(ps -o user= -p "$pid" 2>/dev/null | awk '{print $1}')" = "$(whoami)" ]; then
            OWNED_PIDS="$OWNED_PIDS $pid"
        fi
    done
    if [ -n "$OWNED_PIDS" ]; then
        echo -e "${YELLOW}Stopping existing server process(es) on $PORT:$OWNED_PIDS${NC}"
        # Try graceful first.
        kill $OWNED_PIDS 2>/dev/null || true
        sleep 1
        # Force kill if still listening.
        STILL_LISTENING=$(lsof -nP -t -iTCP:$PORT -sTCP:LISTEN 2>/dev/null || true)
        if [ -n "$STILL_LISTENING" ]; then
            echo -e "${YELLOW}Force killing remaining process(es) on $PORT: $STILL_LISTENING${NC}"
            kill -9 $STILL_LISTENING 2>/dev/null || true
            sleep 1
        fi
    else
        echo -e "${RED}Port $PORT is in use, but no listening process is owned by $(whoami).${NC}"
        echo -e "${YELLOW}Set PORT to a free port (e.g., PORT=8001) or stop the other process manually.${NC}"
        echo ""
        usage
        exit 1
    fi
fi

# Force torchaudio to use CPU to avoid cuDNN version mismatches
# Silero VAD doesn't need GPU acceleration
export TORCHAUDIO_USE_BACKEND_DISPATCHER=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

echo ""
echo -e "${GREEN}Starting Voice Agent server...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Open: ${GREEN}http://localhost:$PORT${NC}"
echo -e "  Log:  ${GREEN}$LOGFILE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run the server
# Exclude heavy directories to prevent "Too many open files" errors
UVICORN_ARGS=(server.main:app --host "$HOST" --port "$PORT")
if [ "$RELOAD" = "1" ]; then
    UVICORN_ARGS+=(--reload \
        --reload-exclude "node_modules" \
        --reload-exclude ".git" \
        --reload-exclude "venv" \
        --reload-exclude "test-results" \
        --reload-exclude "playwright-report" \
        --reload-exclude "__pycache__")
fi

if [ "$FOREGROUND" = "1" ]; then
    exec python -m uvicorn "${UVICORN_ARGS[@]}"
else
    # Background mode (default): do not hold the terminal.
    if [ -f "$PIDFILE" ]; then
        oldpid=$(cat "$PIDFILE" 2>/dev/null || true)
        if is_running "$oldpid"; then
            echo -e "${YELLOW}Server already running (pid=$oldpid).${NC}"
            print_status
            exit 0
        fi
        rm -f "$PIDFILE" 2>/dev/null || true
    fi

    # Start detached. If the script exits, the server keeps running.
    nohup python -m uvicorn "${UVICORN_ARGS[@]}" > "$LOGFILE" 2>&1 &
    newpid=$!
    echo "$newpid" > "$PIDFILE"
    echo -e "${GREEN}✓ Started in background${NC} (pid=$newpid)"

    # Wait for server to become responsive to avoid transient connection errors.
    echo -e "${BLUE}Waiting for server to become ready...${NC}"
    start_ts=$(date +%s)
    while true; do
        if curl -s -o /dev/null "$READY_URL"; then
            break
        fi
        now_ts=$(date +%s)
        if [ $((now_ts - start_ts)) -ge "$READY_TIMEOUT_SECS" ]; then
            echo -e "${YELLOW}⚠ Server didn't respond within ${READY_TIMEOUT_SECS}s. It may still be starting.${NC}"
            echo -e "${YELLOW}  Check logs: tail -f $LOGFILE${NC}"
            break
        fi
        sleep 1
    done

    print_status
    echo ""
    echo -e "${BLUE}Next commands:${NC}"
    echo -e "  ./run.sh status"
    echo -e "  ./run.sh stop"
    echo -e "  ./run.sh restart"
    echo -e "${BLUE}Logs:${NC} tail -f $LOGFILE"
    exit 0
fi
