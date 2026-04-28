# Frontier knowledge base retrieval tools and MCP server.
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

DIAGNOSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "diagnosis": {
            "type": "string",
            "description": "Primary analysis of the failure or event",
        },
        "affected_components": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Affected component identifiers (xnames, MSBs, CDUs, etc.)",
        },
        "domain": {
            "type": "string",
            "enum": ["power", "cooling", "compute", "interconnect", "storage", "cep", "scheduling", "unknown"],
            "description": "Failure domain",
        },
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"],
            "description": "Severity level",
        },
        "causal_chain": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ordered sequence of events in the failure chain",
        },
        "recommended_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete operator actions to address the failure",
        },
        "supporting_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Knowledge note name"},
                    "excerpt": {"type": "string", "description": "Relevant excerpt"},
                },
                "required": ["source", "excerpt"],
            },
            "description": "Evidence from knowledge notes supporting the diagnosis",
        },
    },
    "required": [
        "diagnosis",
        "affected_components",
        "domain",
        "severity",
        "causal_chain",
        "recommended_actions",
        "supporting_evidence",
    ],
}


def _get_knowledge_dir() -> Path:
    """Resolve the bundled knowledge directory path."""
    import importlib.resources

    return Path(str(importlib.resources.files("frontier_agent") / "data" / "knowledge"))


def resolve_note_path(name: str, knowledge_dir: Path) -> Path | None:
    """Resolve a note name (with or without wikilink brackets) to a file path.

    Handles:
    - Plain names: "hub" -> knowledge_dir/hub.md
    - Extensions: "hub.md" -> knowledge_dir/hub.md
    - Subdirectory paths: "operations/power" -> knowledge_dir/operations/power.md
    - Wikilink references: "[[operations/power]]" -> knowledge_dir/operations/power.md
    """
    # Strip wikilink brackets
    name = name.strip()
    if name.startswith("[[") and name.endswith("]]"):
        name = name[2:-2]

    # Add .md extension if missing
    if not name.endswith(".md"):
        name = name + ".md"

    path = knowledge_dir / name
    if path.is_file():
        return path

    return None


def read_note_content(name: str, knowledge_dir: Path) -> str:
    """Read a note by name, returning its content or an error message."""
    path = resolve_note_path(name, knowledge_dir)
    if path is None:
        return f"Note not found: {name}"
    return path.read_text(encoding="utf-8")


def search_notes_content(
    query: str, knowledge_dir: Path
) -> list[dict[str, str]]:
    """Search all markdown files for a query string, returning matches with context."""
    results: list[dict[str, str]] = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    for md_file in sorted(knowledge_dir.rglob("*.md")):
        rel = md_file.relative_to(knowledge_dir)
        note_name = str(rel.with_suffix(""))

        lines = md_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                # Collect context: up to 2 lines before and after
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = "\n".join(lines[start:end])
                results.append(
                    {
                        "note": note_name,
                        "line": str(i + 1),
                        "context": context,
                    }
                )

    return results


def list_notes_content(
    directory: str | None, knowledge_dir: Path
) -> list[dict[str, str]]:
    """List available notes, optionally filtered by subdirectory."""
    if directory:
        search_dir = knowledge_dir / directory
    else:
        search_dir = knowledge_dir

    if not search_dir.is_dir():
        return []

    notes: list[dict[str, str]] = []
    for md_file in sorted(search_dir.rglob("*.md")):
        rel = md_file.relative_to(knowledge_dir)
        note_name = str(rel.with_suffix(""))
        notes.append({"name": note_name})

    return notes


def create_knowledge_server(knowledge_dir: Path | None = None) -> Server:
    """Create an MCP server exposing Frontier knowledge retrieval tools.

    Args:
        knowledge_dir: Path to the knowledge directory. Defaults to the
            bundled package data directory.
    """
    if knowledge_dir is None:
        knowledge_dir = _get_knowledge_dir()

    server = Server("frontier-knowledge", version="1.0.0")

    @server.list_tools()  # type: ignore[misc]
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="read_note",
                description=(
                    "Read a Frontier knowledge note by name. Supports wikilink "
                    "references (e.g., '[[operations/power]]') and plain names "
                    "(e.g., 'hub'). Returns the full markdown content."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Note name or wikilink"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="search_notes",
                description=(
                    "Full-text search across all Frontier knowledge notes. "
                    "Returns matching note names with surrounding context lines."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search text"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_notes",
                description=(
                    "List available Frontier knowledge notes, optionally filtered "
                    "by subdirectory (e.g., 'operations', 'layout', 'telemetry')."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Subdirectory to filter by (optional)",
                        },
                    },
                },
            ),
            Tool(
                name="submit_diagnosis",
                description=(
                    "Submit a structured diagnosis after analyzing a Frontier "
                    "system failure. Call this tool once your analysis is complete "
                    "to deliver the result."
                ),
                inputSchema=DIAGNOSIS_SCHEMA,
            ),
        ]

    @server.call_tool()  # type: ignore[misc]
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "read_note":
            content = read_note_content(arguments["name"], knowledge_dir)
            return [TextContent(type="text", text=content)]

        elif name == "search_notes":
            results = search_notes_content(arguments["query"], knowledge_dir)
            if not results:
                text = "No matches found."
            else:
                parts = []
                for r in results:
                    parts.append(f"### {r['note']} (line {r['line']})\n```\n{r['context']}\n```")
                text = "\n\n".join(parts)
            return [TextContent(type="text", text=text)]

        elif name == "list_notes":
            directory = arguments.get("directory")
            notes = list_notes_content(directory, knowledge_dir)
            if not notes:
                text = "No notes found."
            else:
                text = "\n".join(f"- {n['name']}" for n in notes)
            return [TextContent(type="text", text=text)]

        elif name == "submit_diagnosis":
            return [TextContent(type="text", text="Diagnosis submitted.")]

        else:
            raise ValueError(f"Unknown tool: {name}")

    return server
