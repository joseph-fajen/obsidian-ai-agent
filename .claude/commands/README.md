# Project Commands

Active commands for the obsidian-ai-agent project. Many are customized versions of templates from the [agentic-coding-course](https://github.com/dynamous-community/agentic-coding-course).

## Command Origins & Customizations

| Command | Source | Customizations |
|---------|--------|----------------|
| `plan-feature.md` | Course | Added 3 user checkpoints for review gates between phases |
| `prime.md` | Course | Minor: changed tree command syntax to use `!` prefix |
| `prime-tools.md` | Course | Customized for Jasque/obsidian-ai-agent: references project-specific tool specs and CLAUDE.md |
| `validate.md` | Course | (Review and document differences) |
| `commit.md` | Course | Significantly expanded: added frontmatter, argument hints, allowed-tools, structured process |
| `execute.md` | Course | None (identical to upstream) |
| `start-session.md` | Custom | Project-specific session initialization |
| `end-session.md` | Custom | Project-specific session wrap-up |
| `plan-template.md` | Custom | Template structure for feature plans |
| `check-ignore-comments.md` | Custom | Find and address TODO/FIXME comments |
| `init-project.md` | Course | (Review and document differences) |

## Comparing with Upstream

Pristine course commands are stored in `.agents/reference/upstream-commands/`.

```bash
# Compare a specific command
diff .agents/reference/upstream-commands/core_piv_loop/plan-feature.md \
     .claude/commands/plan-feature.md

# Compare all overlapping commands
./scripts/diff-commands.sh
```

See `.agents/reference/upstream-commands/README.md` for sync instructions.

## Upstream Commands Not Yet Adopted

These commands exist in the course but haven't been copied to this project yet:

- `create-prd.md` - Generate product requirements documents
- `github_bug_fix/rca.md` - Root cause analysis for bugs
- `github_bug_fix/implement-fix.md` - Implement fix from RCA
- `validation/code-review.md` - Technical code review (Module 7)
- `validation/code-review-fix.md` - Address review findings (Module 7)
- `validation/system-review.md` - Process improvement analysis (Module 7)
- `validation/execution-report.md` - Document implementation vs plan (Module 7)

To adopt a command:
1. Copy from `.agents/reference/upstream-commands/`
2. Customize as needed for this project
3. Update this table

## Adding New Commands

1. Check if course has a template in `upstream-commands/`
2. Copy and customize, or create from scratch
3. Document in the table above with source and customizations
