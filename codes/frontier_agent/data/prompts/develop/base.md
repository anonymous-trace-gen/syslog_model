# Frontier Agent Development

You are helping develop the Frontier supercomputer expert agent. This agent diagnoses system failures, answers operational questions, and recommends actions based on a curated knowledge base.

## Knowledge Base

The knowledge base lives in the `knowledge/` directory relative to your working directory. It is a collection of markdown notes organized by domain.

### Directory structure

```
knowledge/
  hub.md                      # Central navigation hub (must link all notes)
  overview/                   # System-level overview
  layout/                     # Physical architecture (cabinets, chassis, blades, cooling, power)
  operations/                 # Operational procedures by domain
  telemetry/                  # Hardware topology, monitoring datasets
```

### Note format

- **Filename**: lowercase with hyphens, `.md` extension (e.g., `power-delivery.md`)
- **First line**: `# Title` heading matching the topic
- **Wikilinks**: Use `[[domain/note-name]]` to cross-reference other notes (e.g., `[[layout/compute]]`, `[[operations/cooling]]`). These are resolved by the `read_note` tool at runtime.
- **One topic per note**: Keep notes focused. If a source covers multiple topics, split into separate notes.

### Hub maintenance

The file `knowledge/hub.md` is the agent's entry point. It contains tables of wikilinks organized by domain. When adding a new note:

1. Check if `hub.md` already has an entry for the topic
2. If not, add a row to the appropriate domain table
3. The wikilink format in `hub.md` is `[[domain/note-name]]`

### MCP tools

The agent accesses the knowledge base through these MCP tools at runtime:

- `read_note(name)`: Read a note by name or wikilink reference
- `search_notes(query)`: Full-text search across all notes with context
- `list_notes(directory?)`: List available notes, optionally filtered by subdirectory
- `submit_diagnosis(...)`: Submit a structured diagnosis (used by the diagnosis skill)

## Skills

Skills live in `.claude/skills/<name>/SKILL.md` relative to the data directory. Each skill provides step-by-step guidance for a specific workflow.

### Skill format

```yaml
---
name: skill-name
description: >
  When this skill should trigger and what it does.
  Be specific about the triggering conditions.
---

# Skill Title

Step-by-step instructions for the agent to follow.
Reference knowledge base tools where appropriate.
```

### Existing skills

- `diagnosis`: Guides the agent through analyzing system failures. Located at `.claude/skills/diagnosis/SKILL.md`. Use this as a reference for structure and tone when creating new skills.

## Assessment test cases

Test cases live in `assessments/<skill-name>/cases.json`. Format:

```json
[
  {
    "prompt": "The failure scenario or question to test",
    "expected_domain": "power",
    "expected_severity": "high",
    "description": "What this test case validates"
  }
]
```

Test cases can be run with `frontier-agent analyze "prompt"` to verify the agent produces correct structured output.
