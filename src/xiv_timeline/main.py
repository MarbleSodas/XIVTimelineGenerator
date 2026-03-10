"""CLI entry point for XIV Timeline Generator."""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
import readchar

from xiv_timeline.graph import run_timeline_generation
from xiv_timeline.llm import configure_langsmith
from xiv_timeline.models import BOSS_NAME_MAPPING

app = typer.Typer(
    name="xiv-timeline",
    help="AI-powered FFXIV boss timeline generator",
    add_completion=False,
    invoke_without_command=True,
)

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            console=console,
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )],
    )
    # Quiet noisy third-party loggers unless in debug mode
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("langchain_core").setLevel(logging.WARNING)
        logging.getLogger("langchain_openai").setLevel(logging.WARNING)
        logging.getLogger("langgraph").setLevel(logging.WARNING)
        logging.getLogger("langsmith").setLevel(logging.WARNING)


def normalize_boss_name(boss_name: str) -> str:
    """Normalize boss name for folder naming."""
    # Remove special characters, keep alphanumeric and hyphens
    name = "".join(c if c.isalnum() or c in "-_" else "_" for c in boss_name)
    return name.lower().strip("-")


@app.command()
def generate(
    boss: str = typer.Argument(..., help="Boss name or ID (e.g., p12s, Zodiark)"),
    expansion: str | None = typer.Option(
        None,
        "--expansion",
        "-e",
        help="Expansion code (06-ew, 05-shb, etc.)",
    ),
    encounter_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Encounter type (raid, trial, ultimate)",
    ),
    difficulty: str | None = typer.Option(
        None,
        "--difficulty",
        "-d",
        help="Difficulty (n, s, u)",
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output",
        "-o",
        help="Output directory base path",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Generate an FFXIV boss timeline.

    Examples:
        xiv-timeline generate p12s
        xiv-timeline generate Zodiark --expansion 06-ew
        xiv-timeline generate p12s --output ./timelines
    """
    console.print(f"[bold blue]XIV Timeline Generator[/bold blue]")
    console.print(f"Generating timeline for: [bold]{boss}[/bold]")

    # Configure logging and tracing
    setup_logging(verbose)
    configure_langsmith()

    # Show resolved parameters
    resolved = BOSS_NAME_MAPPING.get(boss.lower().strip())
    if resolved:
        console.print(f"[dim]Resolved: {resolved['expansion'].display_name} / {resolved['type'].value} / {resolved['difficulty'].value}[/dim]")
    elif expansion or encounter_type or difficulty:
        console.print(f"[dim]Using: {expansion or 'auto'} / {encounter_type or 'auto'} / {difficulty or 'auto'}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching cactbot data...", total=None)

        try:
            # Run the generation pipeline
            result = asyncio.run(run_timeline_generation(
                boss_name=boss,
                expansion=expansion,
                encounter_type=encounter_type,
                difficulty=difficulty,
            ))

            progress.update(task, description="Processing timeline data...")

            # Normalize boss name for folder
            folder_name = normalize_boss_name(boss)
            boss_output_dir = output_dir / folder_name
            cactbot_dir = boss_output_dir / "cactbot"

            # Create directories
            boss_output_dir.mkdir(parents=True, exist_ok=True)
            cactbot_dir.mkdir(parents=True, exist_ok=True)

            # Write JSON output
            json_path = boss_output_dir / "timeline.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result["synthesized"], f, indent=2, ensure_ascii=False)

            progress.update(task, description="Writing cactbot files...")

            # Write cactbot export (with synthesis annotations)
            cactbot_synth_path = cactbot_dir / f"{folder_name}_synth.txt"
            cactbot_synth_path.write_text(result["cactbot_export"], encoding="utf-8")

            # Write raw cactbot timeline
            cactbot_raw_path = cactbot_dir / f"{folder_name}.txt"
            cactbot_raw_path.write_text(result["cactbot_raw"], encoding="utf-8")

            progress.update(task, description="Done!")

            # Summary output
            synthesized = result["synthesized"]
            console.print("")
            console.print(f"[bold green]Timeline generated successfully![/bold green]")
            console.print("")
            console.print(f"[bold]Boss:[/bold] {synthesized['boss_name']}")
            console.print(f"[bold]Expansion:[/bold] {synthesized['expansion']}")
            console.print(f"[bold]Difficulty:[/bold] {synthesized['difficulty']}")
            console.print(f"[bold]Phases:[/bold] {len(synthesized['phases'])}")
            console.print(f"[bold]Confidence:[/bold] {synthesized['confidence']:.0%}")
            console.print("")
            console.print(f"[bold]Output files:[/bold]")
            console.print(f"  - JSON: {json_path}")
            console.print(f"  - Cactbot (synthesized): {cactbot_synth_path}")
            console.print(f"  - Cactbot (raw): {cactbot_raw_path}")

            if verbose:
                console.print("")
                console.print("[bold]Notes:[/bold]")
                for note in synthesized.get("notes", []):
                    console.print(f"  - {note}")

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            if verbose:
                import traceback
                console.print(traceback.format_exc())
            raise typer.Exit(1)


@app.command()
def list_bosses() -> None:
    """List all available boss IDs."""
    console.print("[bold]Available boss IDs:[/bold]")
    console.print("")

    # Group by expansion
    by_expansion = {}
    for boss_id, info in BOSS_NAME_MAPPING.items():
        exp = info["expansion"].display_name
        if exp not in by_expansion:
            by_expansion[exp] = []
        by_expansion[exp].append((boss_id, info["type"].value, info["difficulty"].value))

    for exp, bosses in sorted(by_expansion.items()):
        console.print(f"[bold]{exp}:[/bold]")
        for boss_id, enc_type, diff in sorted(bosses, key=lambda x: (x[0], x[1])):
            diff_label = {"n": "Normal", "s": "Savage", "u": "Ultimate"}.get(diff, diff)
            console.print(f"  {boss_id:8} - {enc_type:8} ({diff_label})")
        console.print("")


@app.command()
def cache_clear() -> None:
    """Clear the local cactbot cache."""
    from xiv_timeline.cactbot_client import CACHE_DIR

    if CACHE_DIR.exists():
        import shutil
        shutil.rmtree(CACHE_DIR)
        console.print(f"[green]Cache cleared:[/green] {CACHE_DIR}")
    else:
        console.print("[yellow]No cache to clear[/yellow]")


def run_menu(title: str, options: list[dict[str, str]], allow_back: bool = True) -> str | None:
    """Helper to run a generic selection menu."""
    selected_index = 0
    while True:
        console.clear()
        console.print(f"[bold blue] {title} [/bold blue]")
        console.print(" ─────────────────────────────────────────")
        
        for i, opt in enumerate(options):
            if i == selected_index:
                console.print(f"  [bold cyan]> {opt['label']}[/bold cyan]")
            else:
                console.print(f"    {opt['label']}")
                
        controls = "[↑↓] Scroll  [Enter] Select  [Q] Quit"
        if allow_back:
            controls += "  [B] Back"
        console.print(f"\n [dim]{controls}[/dim]")
        
        key = readchar.readkey()
        if key.lower() == 'q':
            console.print("\n[yellow]Exiting.[/yellow]")
            raise typer.Exit()
        elif key.lower() == 'b' and allow_back:
            return None
        elif key == readchar.key.UP:
            selected_index = (selected_index - 1) % len(options)
        elif key == readchar.key.DOWN:
            selected_index = (selected_index + 1) % len(options)
        elif key == readchar.key.ENTER:
            return options[selected_index]["value"]

def interactive_menu():
    """Run an interactive TUI for boss selection."""
    by_expansion = {}
    for boss_id, info in BOSS_NAME_MAPPING.items():
        exp = info["expansion"].display_name
        if exp not in by_expansion:
            by_expansion[exp] = {}
        enc_type = info["type"].value
        if enc_type not in by_expansion[exp]:
            by_expansion[exp][enc_type] = []
        
        diff_label = {"n": "Normal", "s": "Savage", "u": "Ultimate"}.get(info["difficulty"].value, info["difficulty"].value)
        by_expansion[exp][enc_type].append((boss_id, diff_label))

    expansions = sorted(by_expansion.keys(), reverse=True)
    
    while True:
        exp_options = [{"label": exp, "value": exp} for exp in expansions]
        selected_exp = run_menu("XIV Timeline Generator - Select Expansion", exp_options, allow_back=False)
        
        while True:
            types = sorted(by_expansion[selected_exp].keys())
            type_options = [{"label": t.title(), "value": t} for t in types]
            selected_type = run_menu(f"Select Encounter Type - {selected_exp}", type_options)
            
            if not selected_type:
                break
            
            while True:
                bosses = sorted(by_expansion[selected_exp][selected_type])
                boss_options = [{"label": f"{boss_id} ({diff})", "value": boss_id} for boss_id, diff in bosses]
                selected_boss = run_menu(f"Select Boss - {selected_exp} {selected_type.title()}", boss_options)
                
                if not selected_boss:
                    break
                
                return selected_boss

@app.command("interactive")
def interactive_cmd() -> None:
    """Start interactive mode."""
    boss_id = interactive_menu()
    if boss_id:
        generate(
            boss=boss_id,
            expansion=None,
            encounter_type=None,
            difficulty=None,
            output_dir=Path("output"),
            verbose=False,
        )

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        boss_id = interactive_menu()
        if boss_id:
            generate(
                boss=boss_id,
                expansion=None,
                encounter_type=None,
                difficulty=None,
                output_dir=Path("output"),
                verbose=False,
            )

if __name__ == "__main__":
    app()
