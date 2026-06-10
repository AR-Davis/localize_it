#!/bin/bash
# EXPLICIT COMMAND — Tier 3: Intentional framework capture
# Part of LOCALIZE_IT: Personal AI Sovereignty
# Usage: localize_it capture-[style|framework|context|voice] [options]

set -e

PROJECT_DIR="$HOME/Projects/localize_it"
EXPLICIT_DIR="$PROJECT_DIR/data/explicit"
LOG_FILE="$PROJECT_DIR/logs/explicit-capture.log"

# Ensure directories exist
mkdir -p "$EXPLICIT_DIR"/{styles,frameworks,contexts,voices}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

show_help() {
    cat << 'EOF'
LOCALIZE_IT — Explicit Capture Commands

Capture complete working styles, frameworks, and contexts.

USAGE:
  localize_it capture-style [options]
  localize_it capture-framework [options]
  localize_it capture-context [options]
  localize_it capture-voice [options]

STYLE CAPTURE:
  --name="technical-writing"
  --description="Concise, code-first, assumes reader knows basics"
  --examples="/path/to/example/files/"
  --rules="Never use 'utilize', always use 'use'"

FRAMEWORK CAPTURE:
  --name="architecture-review"
  --description="How to evaluate system design"
  --steps="Constraints,Options,Tradeoffs,Recommendation,Implementation"
  --criteria="Scalability,Security,Cost,Maintainability"

CONTEXT CAPTURE:
  --project="DOMM"
  --stack="Rust,TUI,Offline-first"
  --patterns="Modular,Event-driven"
  --constraints="No network dependencies"

VOICE CAPTURE:
  --name="pupper-refined"
  --traits="technical,enthusiastic,brief"
  --markers="occasional-dog-metaphors,wags-tail"
  --sample="/path/to/sample/conversations/"

EXAMPLES:

  # Capture writing style
  localize_it capture-style \\
    --name="kinch-tech-docs" \\
    --description="Direct, code-heavy, minimal fluff"

  # Capture decision framework
  localize_it capture-framework \\
    --name="debugging-method" \\
    --steps="Reproduce,Isolate,Hypothesize,Test,Verify,Document"

  # Capture project context
  localize_it capture-context \\
    --project="localize_it" \\
    --stack="Python,Bash,LoRA,JSONL"

  # Capture voice/persona
  localize_it capture-voice \\
    --name="pupper-v2" \\
    --traits="technical-baseline,dog-enthusiasm"

All captures are stored in ~/Projects/localize_it/data/explicit/
and versioned with timestamps.

EOF
}

capture_style() {
    local name=""
    local description=""
    local examples=""
    local rules=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name=*) name="${1#*=}" ;;
            --description=*) description="${1#*=}" ;;
            --examples=*) examples="${1#*=}" ;;
            --rules=*) rules="${1#*=}" ;;
            *) echo "Unknown option: $1" ;;
        esac
        shift
    done
    
    if [ -z "$name" ] || [ -z "$description" ]; then
        echo "Error: --name and --description required"
        return 1
    fi
    
    local filename="$EXPLICIT_DIR/styles/$(echo $name | tr ' ' '-').md"
    local timestamp=$(date -Iseconds)
    
    cat > "$filename" << EOF
---
name: "$name"
type: style
captured: $timestamp
version: "1.0"
---

# Style: $name

## Description
$description

## Rules
$rules

## Examples
EOF
    
    if [ -n "$examples" ] && [ -d "$examples" ]; then
        echo "" >> "$filename"
        echo "Example files:" >> "$filename"
        ls -la "$examples" >> "$filename"
    fi
    
    log "Style captured: $name -> $filename"
    echo "✓ Style saved: $filename"
}

capture_framework() {
    local name=""
    local description=""
    local steps=""
    local criteria=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name=*) name="${1#*=}" ;;
            --description=*) description="${1#*=}" ;;
            --steps=*) steps="${1#*=}" ;;
            --criteria=*) criteria="${1#*=}" ;;
        esac
        shift
    done
    
    if [ -z "$name" ] || [ -z "$steps" ]; then
        echo "Error: --name and --steps required"
        return 1
    fi
    
    local filename="$EXPLICIT_DIR/frameworks/$(echo $name | tr ' ' '-').md"
    local timestamp=$(date -Iseconds)
    
    cat > "$filename" << EOF
---
name: "$name"
type: framework
captured: $timestamp
version: "1.0"
---

# Framework: $name

## Description
${description:-"A decision/analysis framework"}

## Steps
EOF
    
    IFS=',' read -ra STEP_ARRAY <<< "$steps"
    local i=1
    for step in "${STEP_ARRAY[@]}"; do
        echo "$i. ${step// /}" >> "$filename"
        ((i++))
    done
    
    if [ -n "$criteria" ]; then
        echo "" >> "$filename"
        echo "## Evaluation Criteria" >> "$filename"
        IFS=',' read -ra CRIT_ARRAY <<< "$criteria"
        for crit in "${CRIT_ARRAY[@]}"; do
            echo "- ${crit// /}" >> "$filename"
        done
    fi
    
    log "Framework captured: $name -> $filename"
    echo "✓ Framework saved: $filename"
}

capture_context() {
    local project=""
    local stack=""
    local patterns=""
    local constraints=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project=*) project="${1#*=}" ;;
            --stack=*) stack="${1#*=}" ;;
            --patterns=*) patterns="${1#*=}" ;;
            --constraints=*) constraints="${1#*=}" ;;
        esac
        shift
    done
    
    if [ -z "$project" ]; then
        echo "Error: --project required"
        return 1
    fi
    
    local filename="$EXPLICIT_DIR/contexts/$(echo $project | tr ' ' '-').md"
    local timestamp=$(date -Iseconds)
    
    cat > "$filename" << EOF
---
project: "$project"
type: context
captured: $timestamp
---

# Context: $project

## Technology Stack
EOF
    
    if [ -n "$stack" ]; then
        IFS=',' read -ra STACK_ARRAY <<< "$stack"
        for tech in "${STACK_ARRAY[@]}"; do
            echo "- ${tech// /}" >> "$filename"
        done
    fi
    
    if [ -n "$patterns" ]; then
        echo "" >> "$filename"
        echo "## Architectural Patterns" >> "$filename"
        IFS=',' read -ra PAT_ARRAY <<< "$patterns"
        for pat in "${PAT_ARRAY[@]}"; do
            echo "- ${pat// /}" >> "$filename"
        done
    fi
    
    if [ -n "$constraints" ]; then
        echo "" >> "$filename"
        echo "## Constraints" >> "$filename"
        echo "$constraints" >> "$filename"
    fi
    
    log "Context captured: $project -> $filename"
    echo "✓ Context saved: $filename"
}

capture_voice() {
    local name=""
    local traits=""
    local markers=""
    local sample=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name=*) name="${1#*=}" ;;
            --traits=*) traits="${1#*=}" ;;
            --markers=*) markers="${1#*=}" ;;
            --sample=*) sample="${1#*=}" ;;
        esac
        shift
    done
    
    if [ -z "$name" ] || [ -z "$traits" ]; then
        echo "Error: --name and --traits required"
        return 1
    fi
    
    local filename="$EXPLICIT_DIR/voices/$(echo $name | tr ' ' '-').md"
    local timestamp=$(date -Iseconds)
    
    cat > "$filename" << EOF
---
name: "$name"
type: voice
captured: $timestamp
base_model: "llama3.2:1b"
---

# Voice/Persona: $name

## Core Traits
EOF
    
    IFS=',' read -ra TRAIT_ARRAY <<< "$traits"
    for trait in "${TRAIT_ARRAY[@]}"; do
        echo "- ${trait// /}" >> "$filename"
    done
    
    if [ -n "$markers" ]; then
        echo "" >> "$filename"
        echo "## Speech Markers" >> "$filename"
        IFS=',' read -ra MARK_ARRAY <<< "$markers"
        for mark in "${MARK_ARRAY[@]}"; do
            echo "- ${mark// /}" >> "$filename"
        done
    fi
    
    if [ -n "$sample" ]; then
        echo "" >> "$filename"
        echo "## Training Samples" >> "$filename"
        echo "Location: $sample" >> "$filename"
    fi
    
    log "Voice captured: $name -> $filename"
    echo "✓ Voice saved: $filename"
}

# Main dispatcher
case "${1:-}" in
    capture-style)
        shift
        capture_style "$@"
        ;;
    capture-framework)
        shift
        capture_framework "$@"
        ;;
    capture-context)
        shift
        capture_context "$@"
        ;;
    capture-voice)
        shift
        capture_voice "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "LOCALIZE_IT — Explicit Capture Interface"
        echo ""
        echo "Commands:"
        echo "  capture-style      - Capture writing/analysis style"
        echo "  capture-framework - Capture decision frameworks"
        echo "  capture-context   - Capture project contexts"
        echo "  capture-voice     - Capture persona/voice"
        echo ""
        echo "Run 'localize_it help' for detailed usage"
        ;;
esac
