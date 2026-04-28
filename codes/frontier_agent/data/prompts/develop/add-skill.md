# Skill Creation

You are creating a new skill for the Frontier agent. Skills guide the agent through specific workflows beyond general diagnosis.

## Workflow

1. **Capture intent**: Ask the user what the skill should do and when it should trigger. Understand:
   - What problem does the skill solve?
   - What inputs does it expect (syslog entries, component names, telemetry data)?
   - What output should it produce?

2. **Read the reference implementation**: Read `.claude/skills/diagnosis/SKILL.md` to understand the established structure and tone

3. **Write the skill**: Create `.claude/skills/<name>/SKILL.md` with:
   - YAML frontmatter: `name` and `description` (description determines when the agent invokes the skill)
   - Step-by-step procedure referencing knowledge base tools (`read_note`, `search_notes`, `list_notes`)
   - Clear instructions for how the agent should process input and produce output

4. **Consider tool requirements**: If the skill needs MCP tools beyond the current set (`read_note`, `search_notes`, `list_notes`, `submit_diagnosis`), note that `src/frontier_agent/agent.py`'s `allowed_tools` list needs updating

5. **Suggest test cases**: Propose 2-3 realistic test prompts the user can verify with:
   ```bash
   frontier-agent analyze "test prompt"
   ```

6. **Document test cases**: If the user wants formal test cases, create `assessments/<skill-name>/cases.json`:
   ```json
   [
     {
       "prompt": "The test scenario",
       "expected_domain": "cooling",
       "expected_severity": "medium",
       "description": "What this validates"
     }
   ]
   ```

## Skill design principles

- **Focused scope**: Each skill should handle one type of workflow. Don't combine unrelated tasks.
- **Knowledge-grounded**: Skills should direct the agent to read specific knowledge notes rather than relying on general knowledge
- **Structured output**: If the skill produces structured results, use the `submit_diagnosis` tool or define a new submission tool
- **Concrete steps**: Write explicit steps the agent can follow. Vague instructions like "analyze the situation" are less effective than "read the hub note, identify the domain, load the relevant operations note"
