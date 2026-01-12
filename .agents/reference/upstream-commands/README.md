# Upstream Commands Reference

Pristine copies of commands from the agentic-coding-course repository.
These are **READ-ONLY** reference copies - do not edit directly.

## Source

- **Repository:** dynamous-community/agentic-coding-course
- **Branch:** main
- **Last synced:** 2026-01-12
- **Commit:** cda1799 (Main Course Excalidraw Diagram)

## Contents

```
upstream-commands/
├── core_piv_loop/
│   ├── execute.md
│   ├── plan-feature.md
│   ├── prime.md
│   └── prime-tools.md
├── validation/
│   ├── code-review.md
│   ├── code-review-fix.md
│   ├── execution-report.md
│   ├── system-review.md
│   └── validate.md
├── github_bug_fix/
│   ├── implement-fix.md
│   └── rca.md
├── commit.md
├── create-prd.md
└── init-project.md
```

## Sync Instructions

To update these files from the course repo (assumes repos are siblings):

```bash
# From obsidian-ai-agent root
cd ../agentic-coding-course && git pull origin main && cd -

# Sync commands (preserves structure)
rsync -av --delete \
  ../agentic-coding-course/.agents/commands/ \
  .agents/reference/upstream-commands/ \
  --exclude README.md

# Update the commit info in this README manually after syncing
```

## Comparing with Active Commands

```bash
# Compare a specific command
diff .agents/reference/upstream-commands/core_piv_loop/plan-feature.md \
     .claude/commands/plan-feature.md

# Compare all overlapping commands (use helper script)
./scripts/diff-commands.sh
```

## When to Sync

- After completing a new course module
- When the instructor announces updates to commands
- Periodically to check for improvements you might want to adopt
