# Start New Session

Initialize context for a new working session with Jasque. Follow these steps:

## 1. Read Recent Context

Read the most recent session log(s) from `_session_logs/`:
```bash
ls -la _session_logs/
```
Read the 1-2 most recent logs to understand what was accomplished and what's next.

## 2. Check Current State

Read `CURRENT_STATE.md` to understand:
- Development phase and progress
- Which features are implemented/pending
- Docker container status
- Any blockers or open questions

## 3. Read Core Documents

Familiarize with project scope:
```bash
# Quick reference for tool specifications
cat mvp-tool-designs.md

# Full requirements if needed
cat PRD.md
```

## 4. Verify Services (if running)

Check if Jasque is running:
```bash
# Check Docker container status
docker compose ps

# Health check (if server is running)
curl -s http://localhost:8000/health
```

## 5. Start Services If Needed

If services are not running and you need to test:
```bash
# Start Jasque with vault mounted
docker compose up -d

# Or run directly with Docker
docker run -v ${OBSIDIAN_VAULT_PATH}:/vault:rw -e OBSIDIAN_VAULT_PATH=/vault jasque-agent

# View logs
docker compose logs -f
```

## 6. Review Next Steps

Check the "Next Steps" section in the most recent session log and present options to the user.

## 7. Summarize for User

Provide a brief summary:
- What was accomplished last session
- Current development state
- Recommended next actions
- Any blockers that need resolution

---

**Arguments:** $ARGUMENTS (optional: specific session log to read)
