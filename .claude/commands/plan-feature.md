---
description: "Create comprehensive feature plan with deep codebase analysis and research"
argument-hint: [feature description] [optional: specific resources or questions to investigate]
---

# Plan Feature: Research + Implementation Planning

**Feature Request:** $ARGUMENTS

**Core Principle**: We do NOT write code in this phase. Our goal is to create a context-rich implementation plan that enables one-pass implementation success for AI agents.

**Key Philosophy**: Context is King. The plan must contain ALL information needed for implementation - patterns, mandatory reading, documentation, validation commands - so the execution agent succeeds on the first attempt.

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
3. **Assess complexity** - Low / Medium / High
4. **Identify affected systems** - Which parts of the codebase will this touch?
5. **Surface ambiguities** - List any unclear requirements or decisions that need user input

**Create User Story:**

```
As a <type of user>
I want to <action/goal>
So that <benefit/value>
```

### Checkpoint 1

**Present to user:**
- Summary of the feature request (your understanding)
- User story
- Feature type and complexity classification
- Key constraints from project context
- Any ambiguities or questions

**Ask:** "Is this understanding correct? Any clarifications before I analyze the codebase?"

Do not proceed until user confirms.

---

## Phase 3: Codebase Intelligence Gathering

Use the Task tool with `subagent_type=Explore` and parallel analysis:

### 1. Project Structure Analysis

- Detect primary language(s), frameworks, and runtime versions
- Map directory structure and architectural patterns
- Identify service/component boundaries and integration points
- Locate configuration files (pyproject.toml, package.json, etc.)
- Find environment setup and build processes

### 2. Pattern Recognition

- Search for similar implementations in codebase
- Identify coding conventions:
  - Naming patterns (CamelCase, snake_case, kebab-case)
  - File organization and module structure
  - Error handling approaches
  - Logging patterns and standards
- Extract common patterns for the feature's domain
- Document anti-patterns to avoid
- Check CLAUDE.md for project-specific rules and conventions

### 3. Dependency Analysis

- Catalog external libraries relevant to feature
- Understand how libraries are integrated (check imports, configs)
- Find relevant documentation in docs/, ai_docs/, .agents/reference or ai-wiki if available
- Note library versions and compatibility requirements

### 4. Testing Patterns

- Identify test framework and structure (pytest, jest, etc.)
- Find similar test examples for reference
- Understand test organization (unit vs integration)
- Note coverage requirements and testing standards

### 5. Integration Points

- Identify existing files that need updates
- Determine new files that need creation and their locations
- Map router/API registration patterns
- Understand database/model patterns if applicable
- Identify authentication/authorization patterns if relevant

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

**Compile Research References:**

```markdown
## Relevant Documentation

- [Library Official Docs](https://example.com/docs#section)
  - Specific feature implementation guide
  - Why: Needed for X functionality
- [Framework Guide](https://example.com/guide#integration)
  - Integration patterns section
  - Why: Shows how to connect components
```

Document findings with source links. Discard information that doesn't fit the project context.

---

## Phase 6: Synthesis & Evaluation

Connect research findings to codebase patterns:

1. **Map research to implementation** - For each finding, identify where/how it applies in this codebase
2. **Resolve conflicts** - If research suggests patterns different from codebase conventions, decide which to follow (prefer codebase consistency unless there's strong reason)
3. **Identify gaps** - What questions remain unanswered? Are they blockers or can we proceed?
4. **Draft approach** - Write a brief (3-5 sentences) summary of the recommended implementation approach

**Think Harder About:**
- How does this feature fit into the existing architecture?
- What are the critical dependencies and order of operations?
- What could go wrong? (Edge cases, race conditions, errors)
- How will this be tested comprehensively?
- Are there security considerations?

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

Generate the implementation plan document.

**Filename:** `.agents/plans/{kebab-case-descriptive-name}.md`
- Examples: `add-user-authentication.md`, `implement-search-api.md`, `refactor-database-layer.md`

**Create `.agents/plans/` directory if it doesn't exist.**

### Plan Template

Use this structure for the plan file:

```markdown
# Feature: <feature-name>

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

<Detailed description of the feature, its purpose, and value to users>

## User Story

As a <type of user>
I want to <action/goal>
So that <benefit/value>

## Problem Statement

<Clearly define the specific problem or opportunity this feature addresses>

## Solution Statement

<Describe the proposed solution approach and how it solves the problem>

## Feature Metadata

**Feature Type**: [New Capability/Enhancement/Refactor/Bug Fix]
**Estimated Complexity**: [Low/Medium/High]
**Primary Systems Affected**: [List of main components/services]
**Dependencies**: [External libraries or services required]

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: READ THESE FILES BEFORE IMPLEMENTING!

<List files with line numbers and relevance>

- `path/to/file.py` (lines 15-45) - Why: Contains pattern for X that we'll mirror
- `path/to/model.py` (lines 100-120) - Why: Database model structure to follow
- `path/to/test.py` - Why: Test pattern example

### New Files to Create

- `path/to/new_service.py` - Service implementation for X functionality
- `path/to/new_model.py` - Data model for Y resource
- `tests/path/to/test_new_service.py` - Unit tests for new service

### Relevant Documentation READ THESE BEFORE IMPLEMENTING!

- [Documentation Link 1](https://example.com/doc1#section)
  - Specific section: Authentication setup
  - Why: Required for implementing secure endpoints
- [Documentation Link 2](https://example.com/doc2#integration)
  - Specific section: Database integration
  - Why: Shows proper async database patterns

### Patterns to Follow

<Specific patterns extracted from codebase - include actual code examples from the project>

**Naming Conventions:** (extracted from codebase)

**Error Handling:** (extracted from codebase)

**Logging Pattern:** (extracted from codebase)

**Other Relevant Patterns:** (extracted from codebase)

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

<Describe foundational work needed before main implementation>

**Tasks:**
- Set up base structures (schemas, types, interfaces)
- Configure necessary dependencies
- Create foundational utilities or helpers

### Phase 2: Core Implementation

<Describe the main implementation work>

**Tasks:**
- Implement core business logic
- Create service layer components
- Add API endpoints or interfaces
- Implement data models

### Phase 3: Integration

<Describe how feature integrates with existing functionality>

**Tasks:**
- Connect to existing routers/handlers
- Register new components
- Update configuration files
- Add middleware or interceptors if needed

### Phase 4: Testing & Validation

<Describe testing approach>

**Tasks:**
- Implement unit tests for each component
- Create integration tests for feature workflow
- Add edge case tests
- Validate against acceptance criteria

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

Use information-dense keywords for clarity:

- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **REFACTOR**: Restructure without changing behavior
- **MIRROR**: Copy pattern from elsewhere in codebase

### {ACTION} {target_file}

- **IMPLEMENT**: {Specific implementation detail}
- **PATTERN**: {Reference to existing pattern - file:line}
- **IMPORTS**: {Required imports and dependencies}
- **GOTCHA**: {Known issues or constraints to avoid}
- **VALIDATE**: `{executable validation command}`

<Continue with all tasks in dependency order...>

---

## TESTING STRATEGY

<Define testing approach based on project's test framework and patterns>

### Unit Tests

<Scope and requirements based on project standards>

Design unit tests with fixtures and assertions following existing testing approaches.

### Integration Tests

<Scope and requirements based on project standards>

### Edge Cases

<List specific edge cases that must be tested for this feature>

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

<Project-specific linting and formatting commands>

### Level 2: Type Checking

<Project-specific type checking commands>

### Level 3: Unit Tests

<Project-specific unit test commands>

### Level 4: Integration Tests

<Project-specific integration test commands>

### Level 5: Manual Validation

<Feature-specific manual testing steps - API calls, UI testing, etc.>

---

## ACCEPTANCE CRITERIA

<List specific, measurable criteria that must be met for completion>

- [ ] Feature implements all specified functionality
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage meets requirements
- [ ] Integration tests verify end-to-end workflows
- [ ] Code follows project conventions and patterns
- [ ] No regressions in existing functionality

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

<Additional context, design decisions, trade-offs, risks>
```

---

## Quality Criteria

### Context Completeness ✓

- [ ] All necessary patterns identified and documented
- [ ] External library usage documented with links
- [ ] Integration points clearly mapped
- [ ] Gotchas and anti-patterns captured
- [ ] Every task has executable validation command

### Implementation Ready ✓

- [ ] Another developer could execute without additional context
- [ ] Tasks ordered by dependency (can execute top-to-bottom)
- [ ] Each task is atomic and independently testable
- [ ] Pattern references include specific file:line numbers

### Pattern Consistency ✓

- [ ] Tasks follow existing codebase conventions
- [ ] New patterns justified with clear rationale
- [ ] No reinvention of existing patterns or utils
- [ ] Testing approach matches project standards

### Information Density ✓

- [ ] No generic references (all specific and actionable)
- [ ] URLs include section anchors when applicable
- [ ] Task descriptions use codebase keywords
- [ ] Validation commands are non-interactive and executable

---

## Success Metrics

**One-Pass Implementation**: Execution agent can complete feature without additional research or clarification

**Validation Complete**: Every task has at least one working validation command

**Context Rich**: Plan passes "No Prior Knowledge Test" - someone unfamiliar with codebase can implement using only plan content

**Confidence Score**: Rate #/10 that execution will succeed on first attempt

---

## Output

After saving the plan, present to user:

- Confirm plan saved: `.agents/plans/{feature-name}.md`
- Brief summary of what the plan covers
- Complexity assessment
- Key implementation risks or considerations
- Confidence score for one-pass success
- Suggested next step: "Run `/execute .agents/plans/{feature-name}.md` to implement this feature"
