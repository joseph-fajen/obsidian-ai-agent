# Prime for Tool Development

Load tool specifications to prepare for building Jasque agent tools.

## Context

You are about to work on building or modifying the 3 Obsidian tools (`obsidian_manage_notes`, `obsidian_query_vault`, `obsidian_manage_structure`) that will be used by the Pydantic AI agent. Load the tool specifications and patterns.

## Read

Read the tool docstring guide: @.agents/reference/adding_tools_guide.md
Read the tool specifications: @.agents/reference/mvp-tool-designs.md
Read the project guidelines: @CLAUDE.md

## Process

Understand and internalize:

1. **Core Philosophy** - How agent tool docstrings differ from standard docstrings
2. **7 Required Elements** - One-line summary, "Use this when", "Do NOT use", Args with guidance, Returns, Performance Notes, Examples
3. **Agent Perspective** - Writing for LLM comprehension and tool selection
4. **Token Efficiency** - Documenting token costs and optimization strategies
5. **Anti-patterns** - Common mistakes that confuse agents
6. **Template Structure** - The exact format to follow

Pay special attention to:

- "Use this when" (affirmative guidance for tool selection)
- "Do NOT use" (negative guidance to prevent tool confusion)
- Performance Notes (token costs, execution time, limits)
- Realistic examples (not "foo", "bar", "test.md")

## Report Back

Provide a concise summary with:

### Key Principles (5 bullets max)

- [What are the core principles you understood?]

### Critical Distinctions

- [What makes agent tool docstrings different from standard docstrings?]
- [Why does "Do NOT use" matter?]

### Template Internalized

- [Confirm you understand the structure you'll follow]

### Ready to Apply

- [One sentence confirming you're ready to write agent-optimized tool docstrings]

Keep it scannable - I want to verify understanding in 30 seconds.