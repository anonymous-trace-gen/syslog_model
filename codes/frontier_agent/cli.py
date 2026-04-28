# Click CLI entry point for the Frontier agent.
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import TYPE_CHECKING

import click
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown

from frontier_agent.logging import configure_logging

if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient


@click.group()
@click.option("--verbose", is_flag=True, help="Enable DEBUG level logging.")
@click.option("--quiet", is_flag=True, help="Suppress INFO, show WARNING+ only.")
@click.option("--log-file", type=str, default=None, help="Write logs to file.")
@click.option("--api-key", type=str, default=None, help="Anthropic API key.")
@click.option(
    "--model",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    default="sonnet",
    help="Claude model: sonnet (default, balanced), opus (deeper reasoning), haiku (fast).",
)
@click.option(
    "--effort",
    type=click.Choice(["low", "medium", "high", "max"]),
    default=None,
    help="Thinking effort level. Omit for no extended thinking.",
)
@click.option("--no-kb", is_flag=True, help="Disable knowledge base lookups.")
@click.pass_context
def main(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    log_file: str | None,
    api_key: str | None,
    model: str,
    effort: str | None,
    no_kb: bool,
) -> None:
    """Frontier supercomputer expert agent."""
    configure_logging(verbose=verbose, quiet=quiet, log_file=log_file)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["model"] = model
    ctx.obj["effort"] = effort
    ctx.obj["no_kb"] = no_kb
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key


@main.command()
@click.argument("prompt", required=False)
@click.option("--input", "input_file", type=click.Path(exists=True), help="Read prompt from file.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown"]),
    default="json",
    help="Output format (default: json).",
)
@click.option("--domain", type=str, default=None, help="Domain hint (power, cooling, etc.).")
@click.pass_context
def analyze(
    ctx: click.Context,
    prompt: str | None,
    input_file: str | None,
    output_format: str,
    domain: str | None,
) -> None:
    """Analyze a system failure or answer a question about Frontier."""
    if input_file:
        with open(input_file, encoding="utf-8") as f:
            text = f.read()
    elif prompt:
        text = prompt
    else:
        click.echo("Error: provide a prompt argument or --input file.", err=True)
        sys.exit(1)

    if domain:
        text = f"[Domain hint: {domain}]\n\n{text}"

    output_json = output_format == "json"
    asyncio.run(_run_analyze(
        text, output_json=output_json, model=ctx.obj["model"],
        effort=ctx.obj["effort"], no_kb=ctx.obj["no_kb"],
    ))


async def _run_analyze(prompt: str, *, output_json: bool, model: str, effort: str | None, no_kb: bool = False) -> None:
    """Execute batch analysis and print results."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

    from frontier_agent.agent import run_batch

    result_text = ""
    diagnosis: dict | None = None

    async for message in run_batch(prompt, model=model, effort=effort, no_kb=no_kb):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name == "mcp__frontier-knowledge__submit_diagnosis":
                    diagnosis = block.input
                elif isinstance(block, TextBlock):
                    result_text = block.text
        elif isinstance(message, ResultMessage):
            logger.info("Analysis complete (cost: ${:.4f})", message.total_cost_usd or 0)

    if output_json:
        if diagnosis:
            click.echo(json.dumps(diagnosis, indent=2))
        else:
            click.echo("Error: model did not call submit_diagnosis.", err=True)
            if result_text:
                click.echo(result_text, err=True)
            sys.exit(1)
    else:
        if not result_text:
            click.echo("No analysis produced.", err=True)
            sys.exit(1)
        click.echo(result_text)


@main.command()
@click.pass_context
def chat(ctx: click.Context) -> None:
    """Interactive chat with the Frontier expert (TUI)."""
    from frontier_agent.agent import create_chat_client

    client = create_chat_client(model=ctx.obj["model"], effort=ctx.obj["effort"], no_kb=ctx.obj["no_kb"])
    asyncio.run(_interactive_session(client, banner="Frontier Expert Chat"))


@main.command()
@click.argument("focus", required=False, type=click.Choice(["ingest", "add-skill"]))
@click.pass_context
def develop(ctx: click.Context, focus: str | None) -> None:
    """Interactive session for editing knowledge base and skills."""
    from frontier_agent.agent import create_develop_client

    client = create_develop_client(
        focus=focus, model=ctx.obj["model"], effort=ctx.obj["effort"], no_kb=ctx.obj["no_kb"],
    )
    banner = "Frontier Development"
    if focus:
        banner += f" ({focus})"
    asyncio.run(_interactive_session(client, banner=banner))


@main.command()
@click.argument("csv_file", type=click.Path(exists=True), default="causal_edges.csv")
@click.option("--output", "output_file", type=str, default="causal_edges_operational.json", show_default=True, help="Output JSON file path.")
@click.pass_context
def causal(ctx: click.Context, csv_file: str, output_file: str) -> None:
    """Explain causal edges from a CSV as operational HPC knowledge."""
    asyncio.run(_run_causal(csv_file, output_file, model=ctx.obj["model"]))


async def _run_causal(csv_file: str, output_file: str, *, model: str) -> None:
    """Process each causal edge and write operational explanations to JSON."""
    import csv

    import anthropic

    MODEL_IDS = {
        "sonnet": "claude-sonnet-4-6",
        "opus": "claude-opus-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }
    model_id = MODEL_IDS.get(model, "claude-sonnet-4-6")

    PROMPT_TEMPLATE = (
        "You are an expert in HPC system administration on Frontier supercomputer "
        "(AMD MI250X GPUs, Slingshot CXI network, Lustre filesystem). "
        "A causal analysis of 18.3 billion system logs discovered this edge:\n"
        "  Cause: {cause}\n"
        "  Effect: {effect}\n"
        "  Statistical strength (ATE): {ate:.3%}\n\n"
        "Provide a concise operational explanation (2-3 sentences):\n"
        "  1. The physical mechanism connecting these events\n"
        "  2. Why this makes sense on Frontier HPC\n"
        "  3. What operators should do about it\n\n"
        'Respond ONLY with valid JSON matching this schema (no markdown fences):\n'
        '{{"mechanism": "physical explanation", "hpc_context": "why specific to Frontier", '
        '"operator_action": "what to monitor or do", "severity": "CRITICAL|HIGH|MEDIUM|LOW"}}'
    )

    client = anthropic.Anthropic()
    results: list[dict] = []

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info("Processing {} causal edges with model {}", len(rows), model_id)

    for i, row in enumerate(rows, 1):
        cause = row["cause"]
        effect = row["effect"]
        ate = float(row["ate"])

        prompt = PROMPT_TEMPLATE.format(cause=cause, effect=effect, ate=ate)
        logger.debug("Edge {}/{}: {} -> {}", i, len(rows), cause, effect)

        message = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        try:
            explanation = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed for edge {} -> {}, storing raw text", cause, effect)
            explanation = {"raw": raw}

        results.append({
            "cause": cause,
            "effect": effect,
            "ate": ate,
            "ci_lo": float(row.get("ci_lo", 0)),
            "ci_hi": float(row.get("ci_hi", 0)),
            **explanation,
        })
        logger.info("[{}/{}] {} -> {} ({})", i, len(rows), cause, effect, explanation.get("severity", "?"))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info("Saved {} explanations to {}", len(results), output_file)
    click.echo(f"Saved {len(results)} explanations to {output_file}")


async def _interactive_session(client: ClaudeSDKClient, *, banner: str) -> None:
    """Run an interactive REPL loop with a ClaudeSDKClient."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

    console = Console()
    console.print(f"[bold]{banner}[/bold]")
    console.print("Type your message, or 'quit' to exit.\n")

    try:
        async with client:
            while True:
                try:
                    user_input = console.input("[bold green]> [/bold green]")
                except (EOFError, KeyboardInterrupt):
                    break

                if user_input.strip().lower() in ("quit", "exit", "q"):
                    break

                if not user_input.strip():
                    continue

                await client.query(user_input)

                response_parts: list[str] = []
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_parts.append(block.text)
                    elif isinstance(message, ResultMessage):
                        logger.debug(
                            "Turn cost: ${:.4f}",
                            message.total_cost_usd or 0,
                        )

                if response_parts:
                    full_response = "\n".join(response_parts)
                    console.print()
                    console.print(Markdown(full_response))
                    console.print()

    except Exception as exc:
        logger.error("Session error: {}", exc)
        raise

    console.print("\n[dim]Session ended.[/dim]")
