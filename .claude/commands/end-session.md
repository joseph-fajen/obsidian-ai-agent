# End Session and Prepare Handoff

Wrap up the current Jasque session and prepare for the next one. Follow these steps precisely:

## 1. Create Session Log

**Filename format:** `_session_logs/YYYY-MM-DD-N-description.md` where N is the session number for that day.

Before creating a new session log:
1. Check for existing logs with today's date: `ls _session_logs/ | grep "^$(date +%Y-%m-%d)"`
2. If logs exist, determine the next sequence number (e.g., if `-1-` and `-2-` exist, use `-3-`)
3. If no logs exist for today, use `-1-` as the sequence number

Create the session log following the template in `_session_logs/_TEMPLATE.md`. Include:
- Goals and work completed this session
- Decisions made and rationale
- Files created or changed
- Open questions and blockers
- Next steps with clear action items
- Context for next session (current state, key files, recommended starting point)

## 2. Update CURRENT_STATE.md

Update `CURRENT_STATE.md` to reflect:
- Current development phase
- Features implemented vs pending
- Docker/service status
- Any configuration changes
- Update the "Last updated" date

## 3. Git Commit

Stage and commit all changes with a descriptive message:
```bash
git add -A && git commit -m "Session YYYY-MM-DD: [brief description of main accomplishments]"
```

## 4. Stop Services (Optional)

Ask the user whether to stop services, then if yes:
```bash
# Stop Jasque container
docker compose down

# Or if running directly
docker stop jasque-agent
```

Note: Recommend keeping services running if user plans to continue soon.

## 5. Provide Next Session Instructions

Tell the user:
```
To resume next session, run: /start-session

Or manually read:
- _session_logs/[latest-log].md
- CURRENT_STATE.md
- CLAUDE.md (for project guidelines)
```

## 6. Final Summary

Provide a brief wrap-up:
- Key accomplishments this session
- Current project state (% complete, blockers)
- Priority items for next session

---

**Arguments:** $ARGUMENTS (optional: date override for session log, defaults to today)
