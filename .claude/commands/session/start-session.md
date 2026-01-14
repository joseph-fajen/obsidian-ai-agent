# Start New Session

Initialize context for a new working session. Supports two modes:

- **Default mode**: Quick resume from session logs (light, ~3-5k tokens)
- **Deep mode**: Full codebase analysis + session context (~10-18k tokens)

**Arguments:** $ARGUMENTS
- `deep` or `--deep`: Include full codebase analysis (use after context reset or long break)
- (no args): Quick continuity mode

---

## Mode Selection

Check if `$ARGUMENTS` contains "deep":
- If YES → Run **Deep Mode** (Section A, then Section B)
- If NO → Run **Default Mode** (Section B only)

---

## Section A: Deep Analysis (only if `deep` flag)

### A1. Analyze Project Structure

Show directory structure:
!`tree -L 3 -I 'node_modules|__pycache__|.git|dist|build|.venv|*.pyc'`

List tracked files:
!`git ls-files | head -50`

### A2. Read Core Documentation

Read in this order (each file once):
1. `CLAUDE.md` - Project guidelines and conventions
2. `README.md` - Project overview

### A3. Identify Key Files

Based on project type, read:
- Main entry point: `app/main.py`
- Core config: `pyproject.toml`, `app/core/config.py`
- Key schemas or models (scan `app/core/` and `app/features/`)

### A4. Recent Git Activity

!`git log -10 --oneline`

**After completing Section A, proceed to Section B.**

---

## Section B: Session Continuity (always runs)

### B1. Read Recent Session Logs

List available logs:
!`ls -la _session_logs/ | tail -5`

Read the 1-2 most recent logs to understand:
- What was accomplished
- Decisions made
- Open questions or blockers
- Recommended next steps

### B2. Check Current State

Read `CURRENT_STATE.md` to understand:
- Development phase and progress
- Which features are implemented/pending
- Any blockers

### B3. Git Status (brief)

!`git status --short`

### B4. Verify Services

Check if services are running:
```bash
# Check Docker container status
docker compose ps 2>/dev/null || echo "Docker not running"

# Health check (if server is running)
curl -s http://localhost:8123/health 2>/dev/null || echo "Server not responding"
```

### B5. Start Services If Needed

If services are not running and needed for testing:
```bash
# Option 1: Docker Compose
docker compose up -d

# Option 2: Direct uvicorn (development)
uv run uvicorn app.main:app --reload --port 8123
```

---

## Output Summary

Provide a concise summary:

### If Deep Mode
- **Project Overview**: Purpose, tech stack, architecture
- **Key Patterns**: Important conventions observed

### Always (Both Modes)
- **Last Session**: What was accomplished
- **Current State**: Development phase, what's working
- **Next Steps**: Priority actions from session log
- **Blockers**: Any issues needing resolution
- **Services**: Running status

---

## When to Use Each Mode

| Situation | Command |
|-----------|---------|
| Daily work, same day | `/start-session` |
| New Claude Code session (context reset) | `/start-session deep` |
| Coming back after days/weeks | `/start-session deep` |
| Quick check on status | `/start-session` |
| First session on fresh clone | `/start-session deep` |
