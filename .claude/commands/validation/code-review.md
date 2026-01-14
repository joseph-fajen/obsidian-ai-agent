---
description: Technical code review for quality and bugs - supports uncommitted, last commit, or unpushed changes
---

Perform technical code review on changed files.

## Review Mode

Parse the argument to determine review scope:

- **No argument or `--uncommitted`**: Review uncommitted changes (default)
- **`--last-commit`**: Review the most recent commit
- **`--unpushed`**: Review all commits not yet pushed to origin

Argument provided: $ARGUMENTS

## Core Principles

Review Philosophy:

- Simplicity is the ultimate sophistication - every line should justify its existence
- Code is read far more often than it's written - optimize for readability
- The best code is often the code you don't write
- Elegance emerges from clarity of intent and economy of expression

## What to Review

### Step 1: Gather Codebase Context

Start by examining project standards:

- CLAUDE.md
- README.md
- Key files in the app/core/ module
- Documented standards in the docs/ directory

### Step 2: Identify Changed Files

Based on the review mode, run the appropriate commands:

**If no argument or `--uncommitted`:**
```bash
git status
git diff HEAD
git diff --stat HEAD
git ls-files --others --exclude-standard
```

**If `--last-commit`:**
```bash
git show HEAD --stat
git show HEAD
git log -1 --format="%H %s"
```

**If `--unpushed`:**
```bash
git log --oneline origin/main..HEAD
git diff origin/main..HEAD --stat
git diff origin/main..HEAD
```

### Step 3: Read Full Files

Read each changed file in its entirety (not just the diff) to understand full context.

For new files, read the entire file.

### Step 4: Analyze for Issues

For each changed file or new file, analyze for:

1. **Logic Errors**
   - Off-by-one errors
   - Incorrect conditionals
   - Missing error handling
   - Race conditions
   - Edge cases not handled

2. **Security Issues**
   - SQL injection vulnerabilities
   - XSS vulnerabilities
   - Insecure data handling
   - Exposed secrets or API keys
   - Path traversal vulnerabilities

3. **Performance Problems**
   - N+1 queries
   - Inefficient algorithms
   - Memory leaks
   - Unnecessary computations
   - Objects recreated unnecessarily

4. **Code Quality**
   - Violations of DRY principle
   - Overly complex functions
   - Poor naming
   - Missing type hints/annotations

5. **Adherence to Codebase Standards**
   - Standards documented in the docs/ directory
   - Strict typing (MyPy + Pyright must pass)
   - Logging standards (structlog JSON format)
   - Testing standards (pytest patterns)
   - Vertical Slice Architecture patterns

## Verify Issues Are Real

Before reporting an issue:

- Run specific tests if needed
- Confirm type errors are legitimate
- Validate security concerns with context
- Check if the pattern is used elsewhere in the codebase

## Output Format

Save a new file to `.agents/code-reviews/YYYY-MM-DD-[brief-description].md`

### Header

```markdown
# Code Review: [Brief Description]

**Date:** YYYY-MM-DD
**Mode:** uncommitted | last-commit | unpushed
**Reviewer:** Claude

## Summary

[1-2 sentence summary of findings]
```

### Stats

```markdown
## Stats

- Files Reviewed: X
- Issues Found: X (critical: X, high: X, medium: X, low: X)
- Lines Changed: +X / -X
```

### Issues

For each issue found:

```markdown
## Issues

### [SEVERITY] Issue Title

- **File:** path/to/file.py
- **Line:** 42
- **Issue:** [one-line description]

**Detail:** [explanation of why this is a problem]

**Suggestion:** [specific fix, ideally with code example]
```

### Verdict

```markdown
## Verdict

[ ] **PASS** - No blocking issues found
[ ] **PASS WITH NOTES** - Minor issues, safe to proceed
[ ] **NEEDS FIXES** - Issues should be addressed before proceeding
```

If no issues found: "Code review passed. No technical issues detected."

## Important

- Be specific (line numbers, not vague complaints)
- Focus on real bugs, not style preferences
- Suggest fixes, don't just complain
- Flag security issues as CRITICAL
- Consider the context - is this pattern used elsewhere?
