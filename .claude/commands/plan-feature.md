---
description: Research a feature thoroughly, then generate an implementation plan
argument-hint: [feature description] [optional: specific resources or questions to investigate]
---

# Plan Feature: Research + Implementation Planning

**Feature Request:** $ARGUMENTS

---

## Phase 1: Context Loading

Read these project context documents to understand existing decisions and architecture:

1. `CLAUDE.md` - Project conventions and guidelines
2. `.agents/reference/PRD.md` - Product requirements and architecture decisions
3. `.agents/reference/mvp-tool-designs.md` - Tool specifications (if feature involves tools)
4. `CURRENT_STATE.md` - Current implementation status

Summarize key constraints and decisions that will affect this feature.

---

## Phase 2: Feature Understanding

Based on the feature request and project context:

1. **Restate the request** - Write a clear summary of what the user wants to build
2. **Classify the feature type** - Is this: New feature / Enhancement / Refactor / Bug fix?
3. **Identify affected systems** - Which parts of the codebase will this touch?
4. **Surface ambiguities** - List any unclear requirements or decisions that need user input

### Checkpoint 1

**Present to user:**
- Summary of the feature request (your understanding)
- Feature type classification
- Key constraints from project context
- Any ambiguities or questions

**Ask:** "Is this understanding correct? Any clarifications before I analyze the codebase?"

Do not proceed until user confirms.

---

## Phase 3: Codebase Analysis

Use the Task tool with `subagent_type=Explore` to analyze the codebase:

1. **Find similar features** - Search for existing features with similar patterns (e.g., if building a new tool, look at existing tools)
2. **Identify folder structure** - Where do features live? What's the naming convention?
3. **Extract patterns** - How are routes, schemas, services, and tests organized?
4. **Find reusable code** - What existing utilities, helpers, or base classes can be leveraged?

Document specific file paths and line numbers for patterns the new feature should follow.

---

## Phase 4: Research Question Generation

Based on codebase analysis, generate specific research questions. Use these categories:

| Category | Questions to Answer |
|----------|---------------------|
| **Libraries/APIs** | What external libraries or APIs does this feature need? What are their docs? |
| **Patterns** | What are established patterns for this type of feature? |
| **Gotchas** | What commonly goes wrong? What pitfalls should we avoid? |
| **Best practices** | What do experts recommend for this type of implementation? |
| **Assumptions** | What assumptions must be clarified to avoid ambiguity during implementation? |

Generate 3-7 specific, answerable research questions tailored to this feature.

### Checkpoint 2

**Present to user:**
- Summary of codebase analysis (key patterns found, similar features identified)
- List of generated research questions
- Any resources the user mentioned to investigate

**Ask:** "Are these the right research questions? Anything to add, remove, or modify?"

Do not proceed until user confirms.

---

## Phase 5: External Research

For each research question from Checkpoint 2, gather information:

**Methods to use:**
- `gh api` commands for GitHub repositories (code examples, library source)
- WebSearch for documentation, best practices, tutorials
- WebFetch for specific documentation pages

**For each question:**
1. Search for relevant sources
2. Extract key findings that answer the question
3. Note specific code examples or patterns
4. Evaluate fit - does this apply to our project's constraints?

Document findings with source links. Discard information that doesn't fit the project context.

---

## Phase 6: Synthesis & Evaluation

Connect research findings to codebase patterns:

1. **Map research to implementation** - For each finding, identify where/how it applies in this codebase
2. **Resolve conflicts** - If research suggests patterns different from codebase conventions, decide which to follow (prefer codebase consistency unless there's strong reason)
3. **Identify gaps** - What questions remain unanswered? Are they blockers or can we proceed?
4. **Draft approach** - Write a brief (3-5 sentences) summary of the recommended implementation approach

**Produce:**
- Recommended approach summary
- Key patterns to follow (with file references)
- Any remaining risks or uncertainties

### Checkpoint 3

**Present to user:**
- Recommended implementation approach (3-5 sentence summary)
- Key patterns to follow (with file:line references)
- Any remaining risks or uncertainties
- Research sources consulted

**Ask:** "Does this approach look right? Ready to generate the implementation plan?"

If user has concerns, address them and re-present. Do not proceed until user confirms.

---

## Phase 7: Create Implementation Plan

Generate the implementation plan document:

**Filename:** `.agents/plans/implement-[feature-name].md` (use kebab-case feature name)

**Required sections:**
1. **Overview** - Feature description, user story, problem/solution
2. **Context References** - Relevant codebase files (with line numbers), new files to create, documentation consulted
3. **Patterns to Follow** - Specific patterns from codebase analysis with file:line references
4. **Implementation Phases** - Logical grouping of work (e.g., Foundation → Core → Integration → Testing)
5. **Step-by-Step Tasks** - Atomic tasks with exact file paths, what to implement, and validation commands
6. **Testing Strategy** - Unit tests, integration tests, edge cases to cover
7. **Validation Commands** - Exact commands to run (lint, typecheck, test)

Each task must be specific enough that an executing agent can implement without guessing.

---

## Output

After saving the plan, present to user:

- Confirm plan saved: `.agents/plans/implement-[feature-name].md`
- Brief summary of what the plan covers
- Suggested next step: "Run `/execute .agents/plans/implement-[feature-name].md` to implement this feature"

**Success criteria for this command:**
- Plan is specific enough for execution without additional context
- All research is incorporated and cited
- Codebase patterns are referenced with file:line numbers
- Tasks are atomic and ordered by dependency
