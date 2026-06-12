# LOCALIZE_IT — Production Deployment
## 2026-06-12

---

## Status: ✅ PRODUCTION READY

All three tiers operational and monitored by Corraler.

---

## Deployment Summary

### Tier 1: Shadow (Automated)
- **What**: Processes Pi session JSONL files
- **When**: Daily 03:00
- **Script**: `src/pipeline-shadow.py --yesterday`
- **Output**: `data/shadow/*`, `data/training/corpus-*.json`
- **Cron**: `~/.pi/skills/localize/cron/daily-aggregator.sh`

### Tier 2: Intraday (Interactive)
- **What**: `localize` CLI for active capture
- **How**: Run `localize "thing to capture"`
- **Questions**: Interactive categorization
- **Storage**: `data/localize/entries.jsonl`
- **Aggregated**: Daily at 03:00

### Tier 3: Explicit (Direct)
- **What**: Direct capture commands
- **How**: `localize --type framework "description"`
- **Types**: preference, pattern, framework, context, discovery, research, note
- **Storage**: `data/explicit/*/*.jsonl`

---

## Cron Schedule (Corraler Managed)

| Task | Schedule | Next Run | Purpose |
|:---|:---|:---|:---|
| Daily Aggregation | 03:00 daily | Tomorrow 03:00 | Process shadow + build corpus |
| Weekly Review | 09:00 Sunday | 2026-06-15 | Generate Pupper digest |
| Pupper Check | 09:00 Sunday | 2026-06-15 | Review weekly captures |

**Crontab**: `~/.pi/corraler/crontab.master` → installed via `crontab`

---

## Monitoring

### Logs
- Daily: `~/.pi/corraler/logs/localize-daily.log`
- Weekly: `~/.pi/corraler/logs/localize-weekly.log`

### Pupper Digests
- Daily: `~/.pi/corraler/pupper/localize/summary-YYYY-MM-DD.md`
- Weekly: `~/.pi/corraler/pupper/localize/weekly-YYYY-MM-DD.md`

### Corraler Status
```bash
# Check all hounds
cat ~/.pi/corraler/crontab.master | grep "HOUND:"

# Check localize specifically
grep -A5 "HOUND: localize" ~/.pi/corraler/crontab.master
```

---

## Weekly Ritual (Sundays 09:00)

**Pupper Check Protocol:**
1. Review `~/.pi/corraler/pupper/localize/weekly-*.md`
2. Check what was captured this week
3. Update `~/.pi/personas/pupper/kinch-profile.md` if needed
4. Mark WORK_TRACKER task complete

**Location in Tracker**: `~/Desktop/Shepherd/Shepherd/WORK_TRACKER.md`

---

## Usage Examples

```bash
# During any session, say "let's localize this discovery"
localize "I realized I work better with structured output"

# Or quick capture
localize "my preferred apps for task management" --type preference

# Check status
localize --status

# List recent captures
localize --list
```

---

## Data Flow

```
Your Input → localize CLI → categorized → stored
                                              ↓
                              ┌───────────────┼───────────────┐
                              ↓               ↓               ↓
                        data/localize/  data/intraday/  data/explicit/
                        entries.jsonl   *.jsonl         */*.jsonl
                              ↓               ↓               ↓
                              └───────────────┴───────────────┘
                                              ↓
                                    Daily 03:00 Aggregation
                                              ↓
                              data/training/corpus-*.json
                                              ↓
                                    (Future: LoRA Training)
```

---

## Files

| Path | Purpose |
|:---|:---|
| `~/Projects/localize_it/localize` | Main CLI |
| `~/.pi/skills/localize/cron/` | Cron scripts |
| `~/.pi/corraler/registry/localize.json` | Hound registration |
| `~/.pi/corraler/deadlines/2026-06-15/pupper-weekly-check.json` | Weekly reminder |
| `~/Desktop/Shepherd/Shepherd/WORK_TRACKER.md` | Task tracking |

---

## Next Steps

1. **Wait for corpus to grow** (need ~1000 entries for effective LoRA)
2. **Review weekly digests** (starts 2026-06-15)
3. **Implement LoRA training** when ready
4. **Test trained model** offline

---

*Deployed: 2026-06-12*  
*Maintained by: Corraler (daily), Shepherd (weekly)*
