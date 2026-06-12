#!/bin/bash
# SHADOW LOGGER — Tier 1: Passive capture of cloud AI interactions
# Part of LOCALIZE_IT: Personal AI Sovereignty
# Usage: shadow-logger [start|stop|status|process]

set -e

PROJECT_DIR="$HOME/Projects/localize_it"
DATA_DIR="$PROJECT_DIR/data/raw"
SHADOW_DIR="$PROJECT_DIR/data/shadow"
LOG_FILE="$PROJECT_DIR/logs/shadow-capture.log"
PID_FILE="/tmp/localize_it-shadow.pid"

# Ensure directories exist
mkdir -p "$DATA_DIR/$(date +%Y-%m)" "$SHADOW_DIR"/{style,patterns,knowledge}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

case "${1:-}" in
    start)
        if [ -f "$PID_FILE" ]; then
            log "Shadow logger already running (PID: $(cat $PID_FILE))"
            exit 0
        fi
        
        log "Starting shadow logger..."
        
        # Background process that monitors for cloud AI interactions
        # In production, this would hook into browser API calls or pi sessions
        (
            while true; do
                # Placeholder: Capture mechanism would go here
                # Could be: browser extension, pi session logger, API proxy
                
                # For now, check if there are manual logs to process
                if ls "$DATA_DIR"/*.jsonl 2>/dev/null | grep -q .; then
                    log "Found $(ls "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l) log files"
                fi
                
                sleep 60
            done
        ) &
        
        echo $! > "$PID_FILE"
        log "Shadow logger started (PID: $!)"
        ;;
        
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                rm "$PID_FILE"
                log "Shadow logger stopped"
            else
                log "Shadow logger not running (stale PID file)"
                rm "$PID_FILE"
            fi
        else
            log "Shadow logger not running"
        fi
        ;;
        
    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
            echo "Shadow logger: 🟢 Running (PID: $(cat $PID_FILE))"
            echo "Data captured today: $(ls "$DATA_DIR/$(date +%Y-%m)"/*.jsonl 2>/dev/null | wc -l) files"
            echo "Total data: $(du -sh "$DATA_DIR" | cut -f1)"
        else
            echo "Shadow logger: 🔴 Stopped"
            echo "Last capture: $(ls -t "$DATA_DIR"/*/.jsonl 2>/dev/null | head -1 | xargs stat -c %y 2>/dev/null || echo 'None')"
        fi
        ;;
        
    process)
        log "Starting shadow pipeline for $(date -d yesterday +%Y-%m-%d)..."
        
        # Run the new Python pipeline
        "$PROJECT_DIR/src/pipeline-shadow.py" --yesterday
        
        log "Shadow pipeline complete"
        ;;
        
    *)
        echo "LOCALIZE_IT Shadow Logger"
        echo ""
        echo "Usage:"
        echo "  shadow-logger start    - Begin background capture"
        echo "  shadow-logger stop     - End background capture"
        echo "  shadow-logger status   - Check capture status"
        echo "  shadow-logger process  - Process yesterday's data"
        echo ""
        echo "Purpose: Passive, continuous learning from cloud AI usage"
        ;;
esac
