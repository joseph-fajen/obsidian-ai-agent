# Project Commands

Commands for the Jasque project, organized by workflow stage. Many are customized versions of templates from the [agentic-coding-course](https://github.com/dynamous-community/agentic-coding-course).

---

## Command Structure

```
.claude/commands/
├── session/                   # Session lifecycle
│   ├── start-session.md       # Begin work session
│   └── end-session.md         # End session, create log
│
├── piv_loop/                  # Plan → Implement → Validate
│   ├── prime.md               # Load project context
│   ├── prime-tools.md         # Deep-dive on tool implementation
│   ├── plan-feature.md        # Research + create implementation plan
│   └── execute.md             # Implement from plan
│
├── validation/                # Quality & review
│   ├── validate.md            # Run all validation checks
│   ├── code-review.md         # Technical code review
│   ├── execution-report.md    # Document what was implemented
│   └── system-review.md       # Analyze process for improvements
│
├── commit.md                  # Create git commit
├── init-project.md            # One-time project setup
└── check-ignore-comments.md   # Find noqa/type:ignore comments
```

---

## Workflow Quick Reference

### Starting Work
```
/session/start-session
```

### Building Features (PIV Loop)
```
/piv_loop/prime              # Load context
/piv_loop/plan-feature       # Research + plan
/piv_loop/execute [plan]     # Implement
/validation/validate         # Check quality
/commit                      # Commit changes
```

### Quality Review
```
/validation/code-review      # Review code changes
/validation/execution-report # Document what was built
/validation/system-review    # Improve the process
```

### Ending Work
```
/session/end-session
```

---

## Command Origins & Customizations

| Command | Source | Notes |
|---------|--------|-------|
| `session/start-session.md` | Custom | Project-specific session initialization |
| `session/end-session.md` | Custom | Project-specific session wrap-up |
| `piv_loop/prime.md` | Course | Minor syntax adjustment |
| `piv_loop/prime-tools.md` | Course | Customized for Jasque tool specs |
| `piv_loop/plan-feature.md` | Course | Added 3 user checkpoints |
| `piv_loop/execute.md` | Course | Unchanged from upstream |
| `validation/validate.md` | Course | Project-specific validation commands |
| `validation/code-review.md` | Course | Supports uncommitted/last-commit/unpushed modes |
| `validation/execution-report.md` | Course | Unchanged from upstream |
| `validation/system-review.md` | Course | Expanded philosophy section for clarity |
| `commit.md` | Course | Expanded with structured process |
| `init-project.md` | Course | One-time project setup |
| `check-ignore-comments.md` | Custom | Find and evaluate suppression comments |

---

## Comparing with Upstream

Pristine course commands are stored in `.agents/reference/upstream-commands/`.

```bash
# Compare a specific command
diff .agents/reference/upstream-commands/core_piv_loop/plan-feature.md \
     .claude/commands/piv_loop/plan-feature.md

# Compare all overlapping commands
./scripts/diff-commands.sh
```

---

## Upstream Commands Not Yet Adopted

These commands exist in the course but haven't been copied to this project:

- `create-prd.md` - Generate product requirements documents
- `github_bug_fix/rca.md` - Root cause analysis for bugs
- `github_bug_fix/implement-fix.md` - Implement fix from RCA
- `validation/code-review-fix.md` - Address review findings

To adopt a command:
1. Copy from `.agents/reference/upstream-commands/`
2. Customize as needed for this project
3. Update this README
