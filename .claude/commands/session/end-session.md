# End Session and Prepare Handoff

Wrap up the current session and prepare for the next one. Supports two modes:

- **Default mode**: Create session log + update CURRENT_STATE.md + handoff info (no commit)
- **Commit mode**: Above + thorough conventional commit

**Arguments:** $ARGUMENTS
- `commit` or `--commit`: Include thorough conventional commit (using `/commit` format)
- (no args): Quick handoff without commit (use if you already committed)

---

## Mode Selection

Check if `$ARGUMENTS` contains "commit":
- If YES → Run **Sections A, B, and C**
- If NO → Run **Sections A and B only** (skip commit)

---

## Section A: Session Documentation (always runs)

### A1. Create Session Log

**Filename format:** `_session_logs/YYYY-MM-DD-N-description.md`

Before creating:
1. Check existing logs: `ls _session_logs/ | grep "^$(date +%Y-%m-%d)"`
2. Determine next sequence number (if `-1-` and `-2-` exist, use `-3-`)
3. If no logs for today, use `-1-`

Create the session log following `_session_logs/_TEMPLATE.md`. Include:
- Goals and work completed this session
- Decisions made and rationale
- Files created or changed
- Open questions and blockers
- Next steps with clear action items
- Context for next session (current state, key files, recommended starting point)

### A2. Update CURRENT_STATE.md

Update to reflect:
- Current development phase
- Features implemented vs pending
- Docker/service status
- Any configuration changes
- Update the "Last updated" date

---

## Section B: Handoff (always runs)

### B1. Stop Services (Optional)

Ask the user whether to stop services. If yes:
```bash
# Stop Docker containers
docker compose down

# Or if running uvicorn directly
# User should Ctrl+C the terminal
```

Note: Recommend keeping services running if user plans to continue soon.

### B2. Next Session Instructions

Tell the user:
```
To resume next session, run: /start-session

Or for full context after a break: /start-session deep
```

### B3. Final Summary

Provide a brief wrap-up:
- Key accomplishments this session
- Current project state
- Priority items for next session
- Any blockers needing resolution

---

## Section C: Thorough Commit (only if `commit` flag)

### C1. Review Current State

Check git status:
!`git status`

Review changes:
!`git diff HEAD`

### C2. Analyze Changes

Examine the diff and determine:

**Type of change:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation only
- `test`: Adding or updating tests
- `chore`: Maintenance (deps, config, etc.)
- `perf`: Performance improvement
- `style`: Code style/formatting

**Scope (if applicable):**
- Component or area affected (api, auth, chat, etc.)

**Description:**
- Brief summary of what changed (50 chars or less)
- Use imperative mood ("add" not "added")

**Body (if needed):**
- More detailed explanation
- Why the change was made
- Any important context

### C3. Stage and Commit

Stage all changes:
```bash
git add .
```

Create commit using conventional format:
```
type(scope): description

[optional body with details]

Co-authored-by: Claude <noreply@anthropic.com>
```

### C4. Confirm Success

Verify commit:
!`git log -1 --oneline`

Show commit details:
!`git show --stat`

---

## When to Use Each Mode

| Situation | Command |
|-----------|---------|
| Already committed during session | `/end-session` |
| Need to commit + wrap up | `/end-session commit` |
| Quick handoff, will commit later | `/end-session` |
| Full end-of-day wrap-up | `/end-session commit` |

---

## Output Report

### If Commit Mode
**Commit Created:**
- Hash: [hash]
- Message: [conventional commit message]
- Files: [count] changed

### Always (Both Modes)
**Session Log:** `_session_logs/[filename].md`
**CURRENT_STATE.md:** Updated
**Next Session:** Run `/start-session` or `/start-session deep`
