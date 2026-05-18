"""CLI principal (typer)."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint

from pos_editais_monitor import __version__
from pos_editais_monitor.core.config import get_settings
from pos_editais_monitor.core.logging import configure_logging

app = typer.Typer(
    add_completion=False,
    help="pos-editais-monitor CLI",
    no_args_is_help=True,
)


@app.callback()
def _setup() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


@app.command()
def version() -> None:
    """Imprime versao."""
    rprint(f"[bold cyan]pos-editais-monitor[/bold cyan] v{__version__}")


@app.command()
def scrape(
    source: str = typer.Option(..., "--source", "-s", help="Spider name (ex: dou, sucupira)"),
) -> None:
    """Roda um spider especifico ad-hoc."""
    from pos_editais_monitor.cli.commands import run_single_spider

    asyncio.run(run_single_spider(source))


@app.command()
def worker() -> None:
    """Sobe o worker (scheduler + pipeline). Bloqueante."""
    from pos_editais_monitor.cli.commands import run_worker

    asyncio.run(run_worker())


@app.command(name="refresh-emec")
def refresh_emec() -> None:
    """Forca refresh da whitelist e-MEC."""
    from pos_editais_monitor.scheduling.jobs import refresh_emec_job

    n = asyncio.run(refresh_emec_job())
    rprint(f"[green]Upserted[/green] {n} IES")


@app.command(name="dispatch-digest")
def dispatch_digest(
    dry_run: bool = typer.Option(False, "--dry-run", help="Nao envia, so loga"),
) -> None:
    """Envia digest do dia para todos subscribers (idempotente)."""
    from pos_editais_monitor.scheduling.jobs import dispatch_digest_job

    if dry_run:
        rprint("[yellow]dry-run: nao implementado por completo; rodando normal[/yellow]")
    asyncio.run(dispatch_digest_job())


@app.command(name="seed")
def seed_command() -> None:
    """Insere subscriber default + fontes basicas no DB."""
    from pos_editais_monitor.cli.commands import seed_initial_data

    asyncio.run(seed_initial_data())
    rprint("[green]Seed concluido[/green]")


if __name__ == "__main__":
    app()
