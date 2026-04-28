# Agent construction and execution using the Claude Agent SDK.
from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path
from typing import Any, AsyncIterator

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    query,
)
from loguru import logger


def _data_dir() -> Path:
    """Resolve the bundled data directory path."""
    return Path(str(importlib.resources.files("frontier_agent") / "data"))


def _load_prompt(*parts: str) -> str:
    """Load a prompt file from bundled data.

    Args:
        parts: Path components relative to data/prompts/ (e.g., "system" or "develop", "base").
    """
    prompt_path = _data_dir() / "prompts" / "/".join(parts)
    if not prompt_path.suffix:
        prompt_path = prompt_path.with_suffix(".md")
    return prompt_path.read_text(encoding="utf-8")


def _base_options(
    *,
    model: str = "sonnet",
    effort: str | None = None,
    max_turns: int | None = 20,
    no_kb: bool = False,
) -> ClaudeAgentOptions:
    """Build common agent options shared between batch and chat modes."""
    data_dir = _data_dir()

    logger.debug("Data directory: {}", data_dir)
    logger.debug("Loading skills from: {}/.claude/skills/", data_dir)

    mcp_servers: dict[str, dict[str, Any]] = {}
    allowed_tools = ["Skill"]

    if not no_kb:
        mcp_servers["frontier-knowledge"] = {
            "command": sys.executable,
            "args": ["-m", "frontier_agent.mcp_server"],
        }
        allowed_tools.extend([
            "mcp__frontier-knowledge__read_note",
            "mcp__frontier-knowledge__search_notes",
            "mcp__frontier-knowledge__list_notes",
            "mcp__frontier-knowledge__submit_diagnosis",
        ])

    return ClaudeAgentOptions(
        system_prompt=_load_prompt("system"),
        cwd=str(data_dir),
        setting_sources=["project"],
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        model=model,
        effort=effort,
        max_turns=max_turns,
        extra_args={"strict-mcp-config": None},
    )


async def run_batch(
    prompt: str, *, model: str = "sonnet", effort: str | None = None, no_kb: bool = False,
) -> AsyncIterator[Any]:
    """Run a single batch analysis and yield SDK messages.

    Args:
        prompt: The syslog text, failure description, or question.
        model: Claude model short name (sonnet, opus, haiku).
        effort: Thinking effort level (low, medium, high, max).
        no_kb: If True, disable knowledge base MCP server and tools.
    """
    options = _base_options(model=model, effort=effort, no_kb=no_kb)

    logger.info("Starting batch analysis")
    logger.debug("Prompt: {}", prompt[:200])

    async for message in query(prompt=prompt, options=options):
        yield message


def create_chat_client(
    *, model: str = "sonnet", effort: str | None = None, no_kb: bool = False,
) -> ClaudeSDKClient:
    """Create a ClaudeSDKClient for interactive chat sessions."""
    options = _base_options(model=model, effort=effort, max_turns=None, no_kb=no_kb)
    logger.info("Creating chat session")
    return ClaudeSDKClient(options=options)


_DEVELOP_FOCUS_PROMPTS = {
    "ingest": "ingest",
    "add-skill": "add-skill",
}


def _develop_options(
    *,
    focus: str | None = None,
    model: str = "sonnet",
    effort: str | None = None,
    no_kb: bool = False,
) -> ClaudeAgentOptions:
    """Build agent options for development sessions (knowledge/skill editing)."""
    data_dir = _data_dir()

    prompt_parts = [_load_prompt("develop", "base")]
    if focus and focus in _DEVELOP_FOCUS_PROMPTS:
        prompt_parts.append(_load_prompt("develop", _DEVELOP_FOCUS_PROMPTS[focus]))
    system_prompt = "\n\n".join(prompt_parts)

    logger.debug("Data directory: {}", data_dir)
    logger.debug("Development session focus: {}", focus or "general")

    mcp_servers: dict[str, dict[str, Any]] = {}
    allowed_tools = [
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "Skill",
    ]

    if not no_kb:
        mcp_servers["frontier-knowledge"] = {
            "command": sys.executable,
            "args": ["-m", "frontier_agent.mcp_server"],
        }
        allowed_tools.extend([
            "mcp__frontier-knowledge__read_note",
            "mcp__frontier-knowledge__search_notes",
            "mcp__frontier-knowledge__list_notes",
        ])

    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(data_dir),
        setting_sources=["project"],
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        model=model,
        effort=effort,
        max_turns=None,
        extra_args={"strict-mcp-config": None},
    )


def create_develop_client(
    *, focus: str | None = None, model: str = "sonnet", effort: str | None = None, no_kb: bool = False,
) -> ClaudeSDKClient:
    """Create a ClaudeSDKClient for development sessions."""
    options = _develop_options(focus=focus, model=model, effort=effort, no_kb=no_kb)
    logger.info("Creating development session")
    return ClaudeSDKClient(options=options)
