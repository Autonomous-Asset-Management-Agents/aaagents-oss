"""
AAAgents BORA OSS — Thin-CLI

Provides a frictionless "Plug & Run" experience for the AAA Trading Platform
Community Edition via PyPI.

Usage:
    aaagents install    # Interactive setup wizard (run once)
    aaagents start      # Start all BORA containers
    aaagents stop       # Stop all BORA containers
    aaagents status     # Show container health status
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# App & console
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="aaagents",
    help="BORA OSS — Plug & Run CLI for the AAA Trading Platform Community Edition.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPOSE_FILE = "docker-compose.oss.yml"
ENV_EXAMPLE = ".env.oss.example"
ENV_TARGET = ".env.oss"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    """Walk up from cwd to find the directory containing docker-compose.oss.yml."""
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / COMPOSE_FILE).exists():
            return candidate
    return cwd  # fallback — will produce a clear error downstream


def _require_compose_file() -> Path:
    """Return the absolute path to docker-compose.oss.yml or abort with a clear error."""
    root = _find_repo_root()
    compose_path = root / COMPOSE_FILE
    if not compose_path.exists():
        console.print(
            Panel(
                f"[bold red]❌ {COMPOSE_FILE} not found.[/bold red]\n\n"
                "Run [bold]aaagents install[/bold] first, or change to the "
                "directory where the BORA stack lives.",
                title="File Not Found",
            )
        )
        raise typer.Exit(code=1)
    return compose_path


def _require_docker() -> None:
    """Abort with a helpful message if Docker is not available."""
    if shutil.which("docker") is None:
        console.print(
            Panel(
                "[bold red]❌ Docker not found in PATH.[/bold red]\n\n"
                "Please install Docker Desktop (Windows/Mac) or Docker Engine (Linux) "
                "and ensure it is running before using [bold]aaagents[/bold].\n\n"
                "→ https://docs.docker.com/get-docker/",
                title="Docker Required",
            )
        )
        raise typer.Exit(code=1)


def _run_compose(
    *args: str,
    compose_path: Path,
    capture: bool = False,
) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    """Run `docker compose -f <path> <args>` and return the result."""
    cmd = ["docker", "compose", "-f", str(compose_path), *args]
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=False,
    )


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _has_bash() -> bool:
    return shutil.which("bash") is not None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def install() -> None:
    """
    [bold]Interactive setup wizard[/bold] — run once before your first [bold]aaagents start[/bold].

    Guides you through:
    • Docker availability check
    • .env.oss configuration (POSTGRES_PASSWORD, optional Alpaca keys)
    • docker compose pull (downloads the BORA images)
    """
    console.print(
        Panel(
            "[bold cyan]AAAgents BORA OSS — Setup Wizard[/bold cyan]\n"
            "This wizard will configure your local BORA stack.",
            title="aaagents install",
        )
    )

    # 1. Docker check
    _require_docker()
    console.print("[green]✓[/green] Docker found.")

    # 2. Locate repo root
    root = _find_repo_root()
    env_example = root / ENV_EXAMPLE
    env_target = root / ENV_TARGET
    compose_path = root / COMPOSE_FILE

    if not compose_path.exists():
        console.print(
            f"[red]❌ {COMPOSE_FILE} not found in {root}.[/red]\n"
            "Please run this command from the aaagents-oss repository root."
        )
        raise typer.Exit(code=1)

    if not env_example.exists():
        console.print(
            f"[red]❌ {ENV_EXAMPLE} not found.[/red]\n"
            f"Expected at: {env_example}"
        )
        raise typer.Exit(code=1)

    # 3. .env.oss setup
    if env_target.exists():
        overwrite = typer.confirm(
            f"\n.env.oss already exists at {env_target}. Overwrite?",
            default=False,
        )
        if not overwrite:
            console.print("[yellow]Skipping .env.oss generation — using existing file.[/yellow]")
        else:
            _write_env(env_example, env_target)
    else:
        _write_env(env_example, env_target)

    # 4. docker compose pull
    console.print("\n[bold]Pulling BORA images from GHCR…[/bold]")
    result = _run_compose("pull", compose_path=compose_path)
    if result.returncode != 0:
        console.print("[red]❌ docker compose pull failed. Check the output above.[/red]")
        raise typer.Exit(code=result.returncode)

    console.print(
        Panel(
            "[bold green]✅ Setup complete![/bold green]\n\n"
            "Run [bold cyan]aaagents start[/bold cyan] to launch the trading stack.",
            title="Done",
        )
    )


def _write_env(env_example: Path, env_target: Path) -> None:
    """Interactively build .env.oss from the example template."""
    console.print("\n[bold]Configuring .env.oss…[/bold]")

    # Required: POSTGRES_PASSWORD
    postgres_pw = typer.prompt(
        "Enter a strong POSTGRES_PASSWORD (required — compose will refuse to start without it)",
        hide_input=True,
        confirmation_prompt=True,
    )

    # Optional: Alpaca keys
    configure_alpaca = typer.confirm(
        "\nConfigure Alpaca paper-trading keys now? "
        "(Skip to boot in offline mode — no live broker calls)",
        default=False,
    )
    alpaca_key = ""
    alpaca_secret = ""
    if configure_alpaca:
        alpaca_key = typer.prompt("ALPACA_API_KEY")
        alpaca_secret = typer.prompt("ALPACA_SECRET_KEY", hide_input=True)

    # Read example template and substitute values
    template = env_example.read_text(encoding="utf-8")

    lines: list[str] = []
    for line in template.splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            lines.append(f"POSTGRES_PASSWORD={postgres_pw}")
        elif line.startswith("# ALPACA_API_KEY=") and alpaca_key:
            lines.append(f"ALPACA_API_KEY={alpaca_key}")
        elif line.startswith("# ALPACA_SECRET_KEY=") and alpaca_secret:
            lines.append(f"ALPACA_SECRET_KEY={alpaca_secret}")
        else:
            lines.append(line)

    env_target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"[green]✓[/green] Written {env_target}")


@app.command()
def start(
    detach: bool = typer.Option(True, "--detach/--no-detach", "-d/-D", help="Run in background (default: detached)."),
) -> None:
    """
    [bold]Start the BORA trading stack[/bold] (Postgres, Redis, Backend, Public-API, Frontend).

    Requires a configured .env.oss — run [bold]aaagents install[/bold] first.
    """
    _require_docker()
    compose_path = _require_compose_file()

    args = ["up", "--remove-orphans"]
    if detach:
        args.append("-d")

    console.print("[bold]Starting BORA stack…[/bold]")
    result = _run_compose(*args, compose_path=compose_path)
    if result.returncode != 0:
        console.print("[red]❌ Stack failed to start. Check the output above.[/red]")
        raise typer.Exit(code=result.returncode)

    if detach:
        console.print(
            Panel(
                "[green]✅ BORA stack started.[/green]\n\n"
                "• Dashboard:  [link]http://localhost[/link]\n"
                "• Public API: [link]http://localhost:8081[/link]\n"
                "• Engine:     [link]http://localhost:8001[/link]\n\n"
                "Run [bold cyan]aaagents status[/bold cyan] to verify container health.",
                title="Stack Running",
            )
        )


@app.command()
def stop() -> None:
    """[bold]Stop all BORA containers[/bold] (volumes are preserved)."""
    _require_docker()
    compose_path = _require_compose_file()

    console.print("[bold]Stopping BORA stack…[/bold]")
    result = _run_compose("down", compose_path=compose_path)
    if result.returncode != 0:
        console.print("[red]❌ Failed to stop stack. Check the output above.[/red]")
        raise typer.Exit(code=result.returncode)

    console.print("[green]✅ BORA stack stopped.[/green]")


@app.command()
def status() -> None:
    """
    [bold]Show BORA container status and health.[/bold]

    Displays running containers, ports, and health state without
    starting or modifying anything.
    """
    _require_docker()
    compose_path = _require_compose_file()

    result = _run_compose("ps", "--format", "json", compose_path=compose_path, capture=True)

    if result.returncode != 0:
        # Fallback: plain ps output
        _run_compose("ps", compose_path=compose_path)
        raise typer.Exit(code=result.returncode)

    # Try to render a pretty Rich table from the JSON output
    try:
        import json

        rows = json.loads(result.stdout)
        if not rows:
            console.print("[yellow]No containers are currently running.[/yellow]")
            console.print(
                "Run [bold cyan]aaagents start[/bold cyan] to launch the stack."
            )
            return

        table = Table(title="BORA Stack Status", show_header=True, header_style="bold cyan")
        table.add_column("Container", style="bold")
        table.add_column("Status")
        table.add_column("Health")
        table.add_column("Ports")

        for row in rows:
            name = row.get("Name", row.get("Service", "?"))
            state = row.get("State", "?")
            health = row.get("Health", "—")
            publishers = row.get("Publishers", [])
            ports = ", ".join(
                f"{p.get('PublishedPort', '?')}→{p.get('TargetPort', '?')}"
                for p in publishers
                if p.get("PublishedPort")
            ) or "—"

            status_style = "green" if state == "running" else "red"
            health_style = "green" if health == "healthy" else ("yellow" if health == "—" else "red")

            table.add_row(
                name,
                f"[{status_style}]{state}[/{status_style}]",
                f"[{health_style}]{health}[/{health_style}]",
                ports,
            )

        console.print(table)

    except (json.JSONDecodeError, KeyError):
        # If JSON parsing fails (older Docker versions), just print raw output
        console.print(result.stdout)


@app.command()
def version() -> None:
    """Print the [bold]aaagents[/bold] CLI version."""
    from aaagents import __version__

    console.print(f"aaagents [bold cyan]{__version__}[/bold cyan]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
