#!/bin/bash
# DAILY AGGREGATOR — Tier 2: Daily Preference Consolidation
# Part of LOCALIZE_IT: Personal AI Sovereignty
# 
# Runs at 03:00 daily (set via cron)
# Aggregates intraday captures into daily summaries
#
# Usage: daily-aggregator.sh [YYYY-MM-DD]
# If no date provided, uses yesterday

set -e

PROJECT_DIR="$HOME/Projects/localize_it"
DATA_DIR="$PROJECT_DIR/data/intraday"
LOGS_DIR="$PROJECT_DIR/logs"
DAILY_DIR="$DATA_DIR/daily"

# Get date (yesterday if not specified)
DATE="${1:-$(date -d yesterday +%Y-%m-%d)}"
DATE_STAMP=$(echo "$DATE" | tr '-' '')

echo "LOCALIZE_IT Daily Aggregator"
echo "============================"
echo "Date: $DATE"
echo ""

# Ensure directories exist
mkdir -p "$DAILY_DIR" "$LOGS_DIR"

# Check for intraday data
if [ ! -d "$DATA_DIR" ]; then
    echo "No intraday data directory found"
    exit 0
fi

# Count preferences captured today
echo "Scanning for preferences..."

PREF_COUNT=0
PATTERN_COUNT=0
FRAMEWORK_COUNT=0

if [ -f "$DATA_DIR/preferences.jsonl" ]; then
    PREF_COUNT=$(grep "\"date\": \"$DATE\"" "$DATA_DIR/preferences.jsonl" 2>/dev/null | wc -l || echo 0)
fi

if [ -f "$DATA_DIR/patterns.jsonl" ]; then
    PATTERN_COUNT=$(grep "$DATE" "$DATA_DIR/patterns.jsonl" 2>/dev/null | wc -l || echo 0)
fi

if [ -f "$DATA_DIR/frameworks.jsonl" ]; then
    FRAMEWORK_COUNT=$(grep "$DATE" "$DATA_DIR/frameworks.jsonl" 2>/dev/null | wc -l || echo 0)
fi

TOTAL=$((PREF_COUNT + PATTERN_COUNT + FRAMEWORK_COUNT))

echo "Found:"
echo "  Preferences: $PREF_COUNT"
echo "  Patterns: $PATTERN_COUNT"
echo "  Frameworks: $FRAMEWORK_COUNT"
echo "  Total: $TOTAL"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "No intraday captures for $DATE"
    exit 0
fi

# Generate daily summary
SUMMARY_FILE="$DAILY_DIR/summary-$DATE.md"

cat > "$SUMMARY_FILE" << EOF
# Intraday Summary — $DATE

## Capture Statistics
- **Preferences:** $PREF_COUNT
- **Patterns:** $PATTERN_COUNT
- **Frameworks:** $FRAMEWORK_COUNT
- **Total:** $TOTAL

## Captured Items

### Preferences
$(if [ -f "$DATA_DIR/preferences.jsonl" ]; then
    grep "\"date\": \"$DATE\"" "$DATA_DIR/preferences.jsonl" 2>/dev/null | \\
    while read -r line; do
        pref=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('preference',''))" 2>/dev/null || echo "")
        [ -n "$pref" ] && echo "- $pref"
    done
else
    echo "_No preferences captured_"
fi)

### Patterns
$(if [ -f "$DATA_DIR/patterns.jsonl" ]; then
    grep "$DATE" "$DATA_DIR/patterns.jsonl" 2>/dev/null | \\
    while read -r line; do
        pattern=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('description',''))" 2>/dev/null || echo "")
        [ -n "$pattern" ] && echo "- $pattern"
    done
else
    echo "_No patterns captured_"
fi)

### Frameworks
$(if [ -f "$DATA_DIR/frameworks.jsonl" ]; then
    grep "$DATE" "$DATA_DIR/frameworks.jsonl" 2>/dev/null | \\
    while read -r line; do
        fw=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
        [ -n "$fw" ] && echo "- $fw"
    done
else
    echo "_No frameworks captured_"
fi)

---
*Generated: $(date '+%Y-%m-%d %H:%M:%S')*
*Next aggregation: tomorrow 03:00*
EOF

echo "Summary saved: $SUMMARY_FILE"

# Archive old raw data (keep 7 days of intraday captures)
find "$DATA_DIR" -name "*.jsonl" -mtime +7 -exec gzip {} \; 2>/dev/null || true

# Log to aggregator
LOG_ENTRY="{\"timestamp\": \"$(date -Iseconds)\", \"date\": \"$DATE\", \"total_captures\": $TOTAL, \"summary\": \"$SUMMARY_FILE\"}"
echo "$LOG_ENTRY" >> "$LOGS_DIR/daily-aggregator.jsonl"

echo ""
echo "✓ Daily aggregation complete"

# Optional: Trigger Tier 1 Shadow if not already run
# This ensures both tiers run at 03:00
if command -v "$PROJECT_DIR/src/pipeline-shadow.py" >/dev/null 2>&1; then
    echo ""
    echo "Running shadow pipeline..."
    python3 "$PROJECT_DIR/src/pipeline-shadow.py" --date "$DATE" >> "$LOGS_DIR/shadow-$DATE.log" 2>&1 || true
fi

echo ""
echo "Next run: tomorrow at 03:00"
