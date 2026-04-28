# frontier_agent

Claude Agent SDK-based CLI for assesing and evaluating Frontier supercomputer failures causal links. The agent queries a built-in knowledge base (MCP server) and returns structured responses.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Batch analysis — returns structured JSON
frontier-agent analyze "SYS_KERNEL_CTX: critical"

# Interactive chat
frontier-agent chat

# Edit knowledge base / skills
frontier-agent develop
frontier-agent develop ingest
frontier-agent develop add-skill

# Explain causal edges CSV
frontier-agent causal causal_edges.csv --output out.json

# Global flags: --model [sonnet|opus|haiku], --effort [low|medium|high|max], --no-kb
```

Requires `ANTHROPIC_API_KEY`.

## Structure

- `agent.py` — builds `ClaudeAgentOptions`, wraps `claude_agent_sdk`
- `cli.py` — Click entry point
- `tools.py` / `mcp_server.py` — MCP server exposing knowledge base tools (`read_note`, `search_notes`, `list_notes`, `submit_diagnosis`)
- `data/knowledge/` — Markdown notes organized under `overview/`, `layout/`, `operations/`, `telemetry/`
- `data/prompts/system.md` — system prompt for the agent
