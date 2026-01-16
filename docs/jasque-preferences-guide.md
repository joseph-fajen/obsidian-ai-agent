# Jasque Preferences Guide

This guide explains how to customize Jasque's behavior using the `_jasque/preferences.md` file in your vault.

---

## What This File Does

Every time you chat with Jasque, **before your message reaches the AI**, Jasque reads `_jasque/preferences.md` and prepends it to your conversation as context.

Think of it as a "read me first" document—a cheat sheet about you that Jasque consults before every interaction.

**Location:** `_jasque/preferences.md` (in your vault root)

---

## The Two Sections

The preferences file has two distinct parts:

### 1. Structured Settings (YAML Frontmatter)

```yaml
---
date_format: "YYYY-MM-DD"
time_format: "HH:mm"
# ... more settings
---
```

- **Fixed schema** — only specific fields are recognized
- **Validated** — typos in field names are ignored (defaults apply)
- **Safe** — missing fields get sensible defaults

### 2. Free-Form Context (Markdown Body)

Everything after the closing `---` is free-form markdown:

```markdown
---
# ... yaml above
---

## Additional Context

Write anything here. Jasque reads it as natural language context.
```

- **Unlimited flexibility** — write anything
- **Natural language** — describe how you work, what you want
- **This is where the real power lives**

---

## Structured Settings Reference

### Date and Time

| Field | Default | Description |
|-------|---------|-------------|
| `date_format` | `"YYYY-MM-DD"` | How dates should appear in responses |
| `time_format` | `"HH:mm"` | How times should appear in responses |

Common formats:
- `"YYYY-MM-DD"` → 2026-01-16
- `"MM/DD/YYYY"` → 01/16/2026
- `"DD MMM YYYY"` → 16 Jan 2026
- `"HH:mm"` → 14:30
- `"h:mm A"` → 2:30 PM

### Default Folders

```yaml
default_folders:
  meeting_notes: "Meetings/"
  daily_notes: "Daily/"
  projects: "Projects/"
```

| Field | Default | Description |
|-------|---------|-------------|
| `meeting_notes` | *(none)* | Where to create meeting notes |
| `daily_notes` | *(none)* | Where to create daily notes |
| `projects` | *(none)* | Where to create project notes |

**Tip:** Match these to your actual vault structure. Include trailing slash for folders.

### Response Style

```yaml
response_style:
  verbosity: "concise"
  use_bullet_points: true
  include_timestamps: false
```

| Field | Default | Options | Description |
|-------|---------|---------|-------------|
| `verbosity` | `"concise"` | `"concise"`, `"detailed"` | How much Jasque explains |
| `use_bullet_points` | `true` | `true`, `false` | Prefer bullets over paragraphs |
| `include_timestamps` | `false` | `true`, `false` | Add timestamps to responses |

---

## Free-Form Section: What to Put There

The free-form section is where you can dramatically improve Jasque's usefulness. Here are ideas organized by sophistication level:

### Basic: Behavioral Preferences

```markdown
- Keep responses short
- Always use bullet points
- End responses with "🌀"
- Don't use emojis in notes you create
```

### Intermediate: Your Organizational System

```markdown
## My Vault Organization

I use PARA:
- **Projects/** - Active projects with deadlines
- **Areas/** - Ongoing responsibilities
- **Resources/** - Reference material by topic
- **Archive/** - Completed items
```

### Intermediate: Note Formats

```markdown
## Note Formats

Meeting notes should include:
- Date and attendees at top
- Agenda items (numbered)
- Discussion notes under each item
- Action items at bottom with owners and due dates

Tasks should be formatted as:
`- [ ] Task description @due(YYYY-MM-DD) #priority/p1`
```

### Advanced: Naming Conventions

```markdown
## Naming Conventions

- Meeting notes: `YYYY-MM-DD - Meeting with [Person/Team]`
- Daily notes: `YYYY-MM-DD` in `Journal/YYYY/MM/`
- Project notes: `[ProjectCode] - [Topic]`
```

### Advanced: Tags You Use

```markdown
## My Tag System

Status: #status/active, #status/blocked, #status/done
Type: #type/meeting, #type/decision, #type/research
Priority: #priority/p0, #priority/p1, #priority/p2
```

### Advanced: Current Focus

```markdown
## Current Focus

I'm currently working on:
1. **Project Phoenix** - Q1 product launch
2. **Team hiring** - 3 open roles
3. **Learning Rust** - personal development

If I mention these, link to relevant notes in those project folders.
```

### Power User: Workflow Patterns

```markdown
## Weekly Patterns

- Monday morning: Weekly planning (might ask about last week's tasks)
- Friday afternoon: Weekly review (might ask for summaries)
- End of month: Archive completed projects
```

### Power User: Guardrails

```markdown
## Things to Watch For

- If I create a note without linking it, remind me
- If I add tasks without due dates, ask if intentional
- If I'm creating multiple notes on same topic, suggest consolidating
- Never delete without confirmation
```

### Power User: Examples

```markdown
## Examples

Good task:
`- [ ] Review Q1 metrics with Sarah @due(2026-01-20) #priority/p1`

Bad task:
`- [ ] Review metrics`  ← missing owner, date, priority

Good meeting note title:
`2026-01-16 - Weekly Sync with Product Team`

Bad meeting note title:
`Meeting notes`  ← no date, no context
```

---

## What Jasque Actually Sees

When you send a message, Jasque receives your preferences formatted like this:

```
## User Preferences

- Date format: YYYY-MM-DD
- Time format: HH:mm
- Meeting notes folder: Meetings/
- Daily notes folder: Daily/
- Projects folder: Projects/
- Response verbosity: detailed
- Prefer bullet points in responses

## Additional User Context

[Your free-form markdown content here]

---

[Your actual message here]
```

Understanding this output helps you write better input.

---

## Tips for Building Your Preferences

### Start Small, Iterate
Don't try to write the perfect file upfront. Start with basics, use Jasque for a while, notice friction, then add preferences to address it.

### Be Specific with Examples
"Use good formatting" is vague. Show an example of what good looks like.

### Update When Your System Changes
If you reorganize your vault or change your workflow, update preferences to match.

### Test Your Changes
After editing preferences, ask Jasque something that should trigger the new behavior. Verify it works.

---

## Troubleshooting

### Preferences Not Working?

1. **Check file location** — Must be exactly `_jasque/preferences.md` in vault root
2. **Check YAML syntax** — Malformed YAML causes an error (you'll see an HTTP 400)
3. **Check field names** — Typos in field names are silently ignored (defaults used)

### Common YAML Mistakes

```yaml
# Wrong: missing quotes around value with special characters
date_format: YYYY-MM-DD  # Works
date_format: MM/DD/YYYY  # Works
date_format: h:mm A      # FAILS - colon needs quotes
date_format: "h:mm A"    # Works

# Wrong: incorrect indentation
default_folders:
meeting_notes: "Meetings/"  # FAILS - needs indentation
  meeting_notes: "Meetings/"  # Works
```

### Jasque Ignoring My Preferences?

The free-form section is natural language—Jasque interprets it, doesn't execute it mechanically. If something isn't working:
- Be more explicit
- Add an example
- Move critical settings to structured YAML if a field exists

---

## Complete Example

Here's a comprehensive preferences file for inspiration:

```markdown
---
# Jasque User Preferences

date_format: "YYYY-MM-DD"
time_format: "HH:mm"

default_folders:
  meeting_notes: "Work/Meetings/"
  daily_notes: "Journal/"
  projects: "Work/Projects/"

response_style:
  verbosity: "concise"
  use_bullet_points: true
  include_timestamps: false
---

## About Me

I'm a product manager. My vault is my work second brain.

## Vault Organization

I use PARA with these top-level folders:
- **Areas/** - Ongoing responsibilities (Health, Finance, Career, Management)
- **Projects/** - Active work with deadlines
- **Resources/** - Reference material by topic
- **Archive/** - Completed/inactive items
- **Journal/** - Daily notes and reflections

## Note Formats

### Meeting Notes
- Title: `YYYY-MM-DD - Meeting with [Person/Team]`
- Include: date, attendees, agenda, notes, action items
- Action items have owner and due date

### Tasks
Format: `- [ ] Task @due(YYYY-MM-DD) @owner(Name) #priority/p1`

### Daily Notes
- Location: `Journal/YYYY/MM/YYYY-MM-DD.md`
- Include: gratitude, priorities, notes, reflection

## Tags

- Status: #active, #blocked, #done, #waiting
- Type: #meeting, #decision, #research, #idea
- Priority: #p0, #p1, #p2

## Current Focus

1. **Phoenix Launch** - shipping Q1, see `Projects/Phoenix/`
2. **Hiring** - 3 open roles, see `Areas/Management/Hiring/`

## Preferences

- Be direct, skip filler words
- Prefer bullets over paragraphs
- Link to related notes when relevant
- Ask clarifying questions rather than guessing
- End responses with 🌀
```

---

## Summary

| Section | Purpose | Flexibility |
|---------|---------|-------------|
| YAML frontmatter | Mechanical settings (dates, folders, style) | Fixed fields only |
| Free-form markdown | Everything else about how you work | Unlimited |

The more context you give Jasque about your system, your workflow, and your preferences, the more it can act like a well-trained assistant who knows you.

Start simple. Iterate as you discover friction. Your preferences file should evolve with your practice.
