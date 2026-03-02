"""CLI entry point for XIV Timeline Generator."""

import json
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from xiv_timeline.agent import run_timeline_generation
from xiv_timeline.models import BOSS_NAME_MAPPING

app = typer.Typer(
    name="xiv-timeline",
    help="AI-powered FFXIV boss timeline generator",
    add_completion=False,
)

console = Console()


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
            result = run_timeline_generation(
                boss_name=boss,
                expansion=expansion,
                encounter_type=encounter_type,
                difficulty=difficulty,
            )

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

                if synthesized.get("variations"):
                    console.print("")
                    console.print("[bold]Variations found:[/bold]")
                    for var in synthesized["variations"]:
                        console.print(f"  - {var['title']} ({var['type']})")

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


if __name__ == "__main__":
    app()
