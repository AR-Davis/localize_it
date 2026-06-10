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
        log "Processing shadow data for $(date -d yesterday +%Y-%m-%d)..."
        
        # Step 1: Collect yesterday's interactions
        YESTERDAY_DIR="$DATA_DIR/$(date -d yesterday +%Y-%m)"
        if [ ! -d "$YESTERDAY_DIR" ]; then
            log "No data for yesterday"
            exit 0
        fi
        
        # Step 2: Extract patterns
        log "Extracting patterns..."
        "$PROJECT_DIR/src/distill/extract-patterns.py" \
            --input="$YESTERDAY_DIR" \
            --output="$SHADOW_DIR/patterns/$(date -d yesterday +%Y%m%d).json"
        
        # Step 3: Analyze style
        log "Analyzing style..."
        "$PROJECT_DIR/src/distill/analyze-style.py" \
            --input="$YESTERDAY_DIR" \
            --output="$SHADOW_DIR/style/$(date -d yesterday +%Y%m%d).json"
        
        # Step 4: Build knowledge graph
        log "Building knowledge graph..."
        "$PROJECT_DIR/src/distill/build-knowledge.py" \
            --input="$YESTERDAY_DIR" \
            --output="$SHADOW_DIR/knowledge/$(date -d yesterday +%Y%m%d).json"
        
        # Step 5: Generate report
        REPORT="$PROJECT_DIR/logs/shadow-synthesis-$(date -d yesterday +%Y%m%d).md"
        cat > "$REPORT" << EOF
# Shadow Synthesis Report
## Date: $(date -d yesterday +%Y-%m-%d)

### Overview
- Interactions captured: $(ls "$YESTERDAY_DIR"/*.jsonl 2>/dev/null | wc -l)
- Patterns extracted: $(jq length "$SHADOW_DIR/patterns/$(date -d yesterday +%Y%m%d).json" 2>/dev/null || echo 0)
- Knowledge nodes: $(jq '.nodes | length' "$SHADOW_DIR/knowledge/$(date -d yesterday +%Y%m%d).json" 2>/dev/null || echo 0)

### Style Drift
$(cat "$SHADOW_DIR/style/$(date -d yesterday +%Y%m%d).json" 2>/dev/null | jq -r '.summary' || echo "No style analysis available")

### Recommendations
- Training corpus size: $(du -sh "$YESTERDAY_DIR" | cut -f1)
- Ready for LoRA training: Yes

Run: localize_it train-nightly --date=$(date -d yesterday +%Y-%m-%d)
EOF
        
        log "Shadow synthesis complete. Report: $REPORT"
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
