"""Rich-powered Command Line Interface (CLI) and Autonomous GitHub Bot for PatchPilot."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from patchpilot import __version__
from patchpilot.core.orchestrator import PatchPilotOrchestrator
from patchpilot.core.universal_scanner import UniversalCodeScanner

app = typer.Typer(
    name="patchpilot",
    help="Autonomous Issue-to-Verified-Patch Engine for Open Source Maintainers.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]PatchPilot[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    pass


@app.command("scan")
def scan_repo(
    path: Path = typer.Argument(Path("."), help="Path to repository root to scan."),
):
    """Scan and index repository symbols across Python, JS/TS, Go, Rust, and C/C++."""
    resolved_path = path.resolve()
    console.print(Panel(f"[bold cyan]Universal Multi-Language Scanner:[/bold cyan] {resolved_path}", border_style="cyan"))

    scanner = UniversalCodeScanner(resolved_path)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Scanning symbols across all languages...", total=None)
        files_map = scanner.scan()

    table = Table(title="Universal Codebase Index", show_header=True, header_style="bold magenta")
    table.add_column("File Path", style="cyan")
    table.add_column("Language", style="magenta")
    table.add_column("Lines", justify="right", style="green")
    table.add_column("Symbols (Funcs/Structs/Classes)", justify="right", style="yellow")
    table.add_column("Imports/Dependencies", justify="right", style="blue")

    for rel_path, meta in list(files_map.items())[:20]:
        table.add_row(
            rel_path,
            meta.language,
            str(meta.total_lines),
            str(len(meta.symbols)),
            str(len(meta.imports)),
        )

    console.print(table)
    console.print(f"[green][OK][/green] Successfully indexed [bold]{len(files_map)}[/bold] polyglot source files.")


@app.command("triage")
def triage_issue(
    title: str = typer.Argument(..., help="Issue title or summary"),
    body: str = typer.Option("", "--body", "-b", help="Issue description / markdown body"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to markdown issue file"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Path to repository"),
):
    """Analyze an issue, extract stack traces, and rank relevant code files across all languages."""
    if file and file.exists():
        body = file.read_text(encoding="utf-8")

    orchestrator = PatchPilotOrchestrator(repo_dir=path, provider="mock")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Triaging issue against Universal Codebase map...", total=None)
        triage_info = orchestrator.triage(title=title, body=body)

    parsed = triage_info["parsed_issue"]
    top_files = triage_info["top_relevant_files"]

    console.print(Panel(f"[bold green]Issue:[/bold green] {parsed.title}", border_style="green"))
    console.print(f"[bold]Detected Error Types:[/bold] {', '.join(parsed.error_types) or 'None'}")
    console.print(f"[bold]Referenced Files in Issue:[/bold] {', '.join(parsed.referenced_files) or 'None'}")

    table = Table(title="Top Relevant Code Files", show_header=True, header_style="bold cyan")
    table.add_column("Rank", justify="center", style="dim")
    table.add_column("File Path", style="yellow")

    for idx, fpath in enumerate(top_files, start=1):
        table.add_row(str(idx), fpath)

    console.print(table)


@app.command("solve")
def solve_issue(
    title: str = typer.Argument(..., help="Issue title or summary"),
    body: str = typer.Option("", "--body", "-b", help="Issue description or traceback"),
    provider: str = typer.Option("mock", "--provider", help="LLM Provider: openai, gemini, ollama, mock"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for OpenAI or Gemini"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    max_retries: int = typer.Option(3, "--max-retries", help="Max verification attempts"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Path to repository"),
):
    """Run full autonomous reproduction, patch synthesis, and verification loop."""
    console.print(
        Panel(
            f"[bold cyan]PatchPilot Autonomous Engine[/bold cyan]\n"
            f"Provider: [yellow]{provider}[/yellow] | Max Retries: [yellow]{max_retries}[/yellow]",
            border_style="cyan",
        )
    )

    orchestrator = PatchPilotOrchestrator(
        repo_dir=path,
        provider=provider,
        api_key=api_key,
        model=model,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Executing Red-to-Green verification loop...", total=None)
        try:
            result = orchestrator.solve(
                title=title,
                body=body,
                max_iterations=max_retries,
            )
        except Exception as exc:
            console.print(f"[bold red]Execution error:[/bold red] {exc}")
            raise typer.Exit(code=1)

    outcome = result.outcome
    if outcome.success:
        console.print(Panel(f"[bold green]SUCCESS: Verified Patch Generated![/bold green] (in {outcome.iterations} iteration(s))", border_style="green"))
        console.print("[bold]Unified Git Diff:[/bold]")
        console.print(outcome.final_diff or "[dim]No changes required[/dim]")
    else:
        console.print(Panel(f"[bold red]FAILED: Could not achieve clean GREEN state.[/bold red]\n{outcome.error_message}", border_style="red"))

    console.print("\n[bold]Step Logs:[/bold]")
    for log in outcome.step_logs:
        console.print(f"  • {log}")


@app.command("bot")
def run_github_bot():
    """Headless entry point executed in GitHub Actions when an issue is reported."""
    from patchpilot.bot.github_bot import GitHubActionBot
    bot = GitHubActionBot()
    bot.run()


def main():
    app()


if __name__ == "__main__":
    main()
