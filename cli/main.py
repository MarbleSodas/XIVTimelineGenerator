#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import argparse
import questionary
from rich.console import Console
from rich.table import Table

from config import config
from schemas.timeline_schemas import TimelineGenerationRequest
from agents.orchestrator import TimelineGenerationOrchestrator


console = Console()


BANNER = r"""
 _______           ___          
/_  __(_)_ _  ___ / (_)__  ___  
 / / / /  ' \/ -_) / / _ \/ -_) 
/_/_/_/_/_/_/\__/_/_/_//_/\__/  
  / __/__________ ____  ___ ____
 _\ \/ __/ __/ _ `/ _ \/ -_) __/
/___/\__/_/  \_,_/ .__/\__/_/   
                 /_/             
                     Timeline Scraper v2.0
                     (Interactive Edition)
"""


def print_banner():
    console.print(f"[cyan]{BANNER}[/cyan]\n")


def print_boss_table():
    bosses = config.cactbot.boss_mapping
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Zone ID", style="dim")
    table.add_column("Encounter ID", style="dim")
    
    for boss_id, boss_info in bosses.items():
        table.add_row(
            boss_id,
            boss_info.get("name", "N/A"),
            str(boss_info.get("zone_id", "N/A")),
            str(boss_info.get("encounter_id", "N/A")),
        )
    
    console.print(table)


def get_boss_choice():
    bosses = config.cactbot.boss_mapping
    choices = []
    
    for boss_id, boss_info in bosses.items():
        name = boss_info.get("name", boss_id)
        choices.append(f"{boss_id} - {name}")
    
    choices.append("Exit")
    
    selected = questionary.select(
        "Select a boss:",
        choices=choices,
        qmark=">",
    ).ask()
    
    if selected == "Exit" or selected is None:
        return None
    
    return selected.split(" - ")[0].split(" - ")[0].strip()


def get_generation_options(boss_id):
    boss_config = config.get_boss_config(boss_id)
    
    report_count = questionary.text(
        "Number of FFLogs reports to analyze:",
        default="30",
        qmark=">",
        validate=lambda x: x.isdigit() and int(x) > 0,
    ).ask()
    
    include_dodgeable = questionary.confirm(
        "Include dodgeable abilities?",
        default=False,
        qmark=">",
    ).ask()
    
    if include_dodgeable:
        threshold = questionary.text(
            "Dodgeable threshold (0.0-1.0):",
            default="0.7",
            qmark=">",
            validate=lambda x: x.replace(".", "").isdigit() and 0 <= float(x) <= 1,
        ).ask()
    else:
        threshold = "0.7"
    
    output_path = questionary.text(
        "Output file path (leave empty for default):",
        default=f"src/data/bosses/{boss_config.get('mitplan_id', boss_id)}_actions.json" if boss_config else "",
        qmark=">",
    ).ask()
    
    # YouTube enrichment options
    enable_transcript = questionary.confirm(
        "Enable YouTube transcript enrichment?",
        default=True,
        qmark=">",
    ).ask()
    
    youtube_video_ids = []
    if enable_transcript:
        console.print("\n[cyan]YouTube Video IDs for transcript enrichment:[/cyan]")
        console.print("[dim]Enter video IDs (or full URLs) separated by commas,[/dim]")
        console.print("[dim]or leave empty to auto-discover guides[/dim]")
        
        video_input = questionary.text(
            "YouTube video IDs/URLs (comma-separated):",
            default="",
            qmark=">",
        ).ask()
        
        if video_input.strip():
            # Parse multiple video IDs/URLs
            for item in video_input.split(","):
                item = item.strip()
                if item:
                    # Extract video ID if it's a URL
                    if "youtube.com" in item or "youtu.be" in item:
                        from tools.youtube_transcript import YouTubeTranscriptFetcher
                        fetcher = YouTubeTranscriptFetcher()
                        video_id = fetcher.extract_video_id(item)
                        if video_id:
                            youtube_video_ids.append(video_id)
                        fetcher.close()
                    elif len(item) == 11:  # Likely a video ID
                        youtube_video_ids.append(item)
    
    return {
        "boss_id": boss_id,
        "report_count": int(report_count),
        "include_dodgeable": include_dodgeable,
        "threshold": float(threshold),
        "output_path": output_path if output_path.strip() else None,
        "youtube_video_ids": youtube_video_ids,
        "enable_transcript_enrichment": enable_transcript,
    }


def check_credentials():
    client_id = config.fflogs_client_id
    client_secret = config.fflogs_client_secret
    
    if not client_id or not client_secret:
        console.print("\n[yellow]FFLogs credentials not found in .env file[/yellow]")
        
        new_client_id = questionary.text(
            "Enter FFLogs Client ID:",
            qmark=">",
        ).ask()
        
        new_client_secret = questionary.password(
            "Enter FFLogs Client Secret:",
            qmark=">",
        ).ask()
        
        if new_client_id and new_client_secret:
            return new_client_id, new_client_secret
        return None, None
    
    return client_id, client_secret


def check_llm_api_key():
    llm_api_key = config.llm_api_key or os.environ.get("MINIMAX_API_KEY", "")
    
    if not llm_api_key:
        console.print("\n[yellow]LLM API key not found[/yellow]")
        
        new_api_key = questionary.password(
            "Enter Minimax API Key:",
            qmark=">",
        ).ask()
        
        if new_api_key:
            return new_api_key
    
    return llm_api_key


def generate_timeline(options, client_id, client_secret):
    console.print(f"\n[cyan]Generating timeline for {options['boss_id']}...[/cyan]\n")
    
    try:
        llm_client = config.get_llm_client()
    except Exception as e:
        console.print(f"[red]Error: Failed to initialize LLM client: {e}[/red]")
        return False
    
    console.print(f"[green]Using atomic agents with {config.llm_model}[/green]\n")
    
    youtube_video_ids = options.get("youtube_video_ids", [])
    enable_transcript = options.get("enable_transcript_enrichment", True)
    
    if youtube_video_ids:
        console.print(f"[green]Using {len(youtube_video_ids)} YouTube video(s) for transcript enrichment[/green]\n")
    elif enable_transcript:
        console.print("[green]YouTube transcript enrichment enabled (auto-discover)[/green]\n")
    
    request = TimelineGenerationRequest(
        boss_id=options["boss_id"],
        report_count=options["report_count"],
        output_path=options["output_path"],
        include_dodgeable=options["include_dodgeable"],
        dodgeable_threshold=options["threshold"],
        fflogs_client_id=client_id,
        fflogs_client_secret=client_secret,
        youtube_video_ids=youtube_video_ids,
        enable_transcript_enrichment=enable_transcript,
    )
    
    orchestrator = TimelineGenerationOrchestrator(
        client_id,
        client_secret,
        llm_client,
        youtube_api_key=config.youtube_api_key or os.environ.get("YOUTUBE_API_KEY", ""),
    )
    result = orchestrator.run(request)
    
    if result.success:
        console.print("[green]✓ Timeline generated successfully![/green]\n")
        
        if result.summary:
            console.print("[blue]=== Summary ===[/blue]")
            console.print(f"  Unique abilities: {result.summary.unique_abilities}")
            console.print(f"  Total events: {result.summary.total_events}")
            console.print(f"  Reports used: {result.summary.reports_used}")
            console.print(f"  Tank busters: {result.summary.tank_busters}")
            console.print(f"  Raidwides: {result.summary.raidwides}")
            console.print(f"  Variants detected: {result.summary.variants_detected}")
            console.print(f"  Default coverage: {result.summary.default_coverage:.1%}")
        
        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  ⚠ {warning}")
        
        if result.output_path:
            console.print(f"\n[green]Output: {result.output_path}[/green]")
        
        return True
    else:
        console.print("[red]✗ Failed to generate timeline[/red]")
        
        for error in result.errors:
            console.print(f"  [red]Error: {error}[/red]")
        
        return False


def show_boss_info(boss_id):
    boss_config = config.get_boss_config(boss_id)
    
    if not boss_config:
        console.print(f"[red]Unknown boss ID: {boss_id}[/red]")
        return
    
    console.print(f"\n[yellow]Boss Information:[/yellow]\n")
    console.print(f"  ID: [cyan]{boss_id}[/cyan]")
    console.print(f"  Name: [white]{boss_config.get('name', 'N/A')}[/white]")
    console.print(f"  Zone ID: {boss_config.get('zone_id', 'N/A')}")
    console.print(f"  Encounter ID: {boss_config.get('encounter_id', 'N/A')}")
    console.print(f"  Timeline: {boss_config.get('timeline_path', 'N/A')}")
    console.print(f"  MitPlan ID: {boss_config.get('mitplan_id', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description="MitPlan Timeline Scraper v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("command", nargs="?", help="Command to run (generate, list-bosses, info)")
    parser.add_argument("boss", nargs="?", help="Boss ID (e.g., r7s)")
    parser.add_argument("-c", "--count", type=int, default=30, help="Number of reports to analyze")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--include-dodgeable", action="store_true", help="Include dodgeable abilities")
    parser.add_argument("-t", "--threshold", type=float, default=0.7, help="Dodgeable threshold (0.0-1.0)")
    parser.add_argument("--client-id", help="FFLogs client ID")
    parser.add_argument("--client-secret", help="FFLogs client secret")
    parser.add_argument("--name", help="Boss display name")
    parser.add_argument("--llm-api-key", help="LLM API key (defaults to MINIMAX_API_KEY env var)")
    parser.add_argument("--youtube-video-id", help="YouTube video ID(s) for transcript enrichment (comma-separated, or URLs)")
    parser.add_argument("--youtube-api-key", help="YouTube Data API key for video search")
    parser.add_argument("--no-transcript-enrichment", action="store_true", help="Disable YouTube transcript enrichment")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Check if we should run in interactive mode
    if args.interactive or not args.command:
        run_interactive()
        return
    
    # Handle non-interactive commands
    if args.command == "list-bosses":
        print_banner()
        console.print("\n[yellow]Available Boss IDs:[/yellow]\n")
        print_boss_table()
        return
    
    if args.command == "info":
        if not args.boss:
            console.print("[red]Error: Boss ID required for info command[/red]")
            sys.exit(1)
        print_banner()
        show_boss_info(args.boss)
        return
    
    if args.command == "generate":
        if not args.boss:
            console.print("[red]Error: Boss ID required for generate command[/red]")
            sys.exit(1)
        
        print_banner()
        
        client_id = args.client_id or config.fflogs_client_id
        client_secret = args.client_secret or config.fflogs_client_secret
        
        if not client_id or not client_secret:
            console.print("[red]Error: FFLogs client_id and client_secret required[/red]")
            console.print("[yellow]Set via arguments or MITPLAN_FFLOGS_CLIENT_ID/MITPLAN_FFLOGS_CLIENT_SECRET environment variables[/yellow]")
            sys.exit(1)
        
        llm_api_key = args.llm_api_key or config.llm_api_key or os.environ.get("MINIMAX_API_KEY", "")
        if not llm_api_key:
            console.print("[red]Error: LLM API key required for atomic agents[/red]")
            console.print("[yellow]Set via --llm-api-key argument or MINIMAX_API_KEY environment variable[/yellow]")
            sys.exit(1)
        
        try:
            llm_client = config.get_llm_client()
        except Exception as e:
            console.print(f"[red]Error: Failed to initialize LLM client: {e}[/red]")
            sys.exit(1)
        
        console.print(f"[green]Using atomic agents with {config.llm_model}[/green]\n")
        
        output_path = args.output
        if not output_path:
            boss_config = config.get_boss_config(args.boss)
            if boss_config:
                output_path = f"src/data/bosses/{boss_config.get('mitplan_id', args.boss)}_actions.json"
        
        # Parse YouTube video IDs (comma-separated)
        youtube_video_ids = []
        if args.youtube_video_id:
            for item in args.youtube_video_id.split(","):
                item = item.strip()
                if item:
                    # Extract video ID if it's a URL
                    if "youtube.com" in item or "youtu.be" in item:
                        from tools.youtube_transcript import YouTubeTranscriptFetcher
                        fetcher = YouTubeTranscriptFetcher()
                        video_id = fetcher.extract_video_id(item)
                        if video_id:
                            youtube_video_ids.append(video_id)
                        fetcher.close()
                    elif len(item) == 11:  # Likely a video ID
                        youtube_video_ids.append(item)
        
        if youtube_video_ids:
            console.print(f"[green]Using {len(youtube_video_ids)} YouTube video(s) for transcript enrichment[/green]\n")
        
        request = TimelineGenerationRequest(
            boss_id=args.boss,
            boss_name=args.name,
            report_count=args.count,
            output_path=output_path,
            include_dodgeable=args.include_dodgeable,
            dodgeable_threshold=args.threshold,
            fflogs_client_id=client_id,
            fflogs_client_secret=client_secret,
            youtube_video_ids=youtube_video_ids,
            enable_transcript_enrichment=not args.no_transcript_enrichment,
        )
        
        console.print(f"[cyan]Generating timeline for {args.boss}...[/cyan]\n")
        
        youtube_api_key = args.youtube_api_key or config.youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")
        orchestrator = TimelineGenerationOrchestrator(
            client_id,
            client_secret,
            llm_client,
            youtube_api_key=youtube_api_key,
        )
        result = orchestrator.run(request)
        
        if result.success:
            console.print("[green]✓ Timeline generated successfully![/green]\n")
            
            if result.summary:
                console.print("[blue]=== Summary ===[/blue]")
                console.print(f"  Unique abilities: {result.summary.unique_abilities}")
                console.print(f"  Total events: {result.summary.total_events}")
                console.print(f"  Reports used: {result.summary.reports_used}")
                console.print(f"  Tank busters: {result.summary.tank_busters}")
                console.print(f"  Raidwides: {result.summary.raidwides}")
                console.print(f"  Variants detected: {result.summary.variants_detected}")
                console.print(f"  Default coverage: {result.summary.default_coverage:.1%}")
            
            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  ⚠ {warning}")
            
            if result.output_path:
                console.print(f"\n[green]Output: {result.output_path}[/green]")
        else:
            console.print("[red]✗ Failed to generate timeline[/red]")
            
            for error in result.errors:
                console.print(f"  [red]Error: {error}[/red]")
            
            sys.exit(1)
        
        return
    
    # Unknown command
    console.print(f"[red]Unknown command: {args.command}[/red]")
    parser.print_help()


def run_interactive():
    print_banner()
    
    while True:
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                "Generate timeline for a boss",
                "List available bosses",
                "Show boss info",
                "Exit",
            ],
            qmark=">",
        ).ask()
        
        if choice == "Generate timeline for a boss":
            boss_id = get_boss_choice()
            if boss_id is None:
                continue
            
            client_id, client_secret = check_credentials()
            if not client_id or not client_secret:
                console.print("[red]FFLogs credentials required to generate timeline[/red]")
                continue
            
            llm_api_key = check_llm_api_key()
            if not llm_api_key:
                console.print("[red]LLM API key required to generate timeline[/red]")
                continue
            
            options = get_generation_options(boss_id)
            
            generate_timeline(options, client_id, client_secret)
            
            questionary.press_any_key_to_continue("\n[dim]Press any key to continue...[/dim]").ask()
            
        elif choice == "List available bosses":
            console.print("\n[yellow]Available Boss IDs:[/yellow]\n")
            print_boss_table()
            console.print()
            questionary.press_any_key_to_continue("[dim]Press any key to continue...[/dim]").ask()
            
        elif choice == "Show boss info":
            boss_id = get_boss_choice()
            if boss_id is None:
                continue
            
            show_boss_info(boss_id)
            console.print()
            questionary.press_any_key_to_continue("[dim]Press any key to continue...[/dim]").ask()
            
        elif choice == "Exit" or choice is None:
            console.print("\n[cyan]Goodbye![/cyan]\n")
            break


if __name__ == "__main__":
    main()
