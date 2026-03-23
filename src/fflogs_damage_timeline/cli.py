import argparse
import logging
import sys
from pathlib import Path

from agents.encounter_research import EncounterResearchService
from agents.encounter_research.minimax_client import MiniMaxClient
from agents.encounter_research.open_websearch_client import OpenWebSearchClient
from fflogs.encounters import EncounterLoader
from fflogs_damage_timeline.graphql_client import FFLogsGraphQLClient
from fflogs_damage_timeline.normalizer import normalize_fight_timeline
from fflogs_damage_timeline.output import (
    write_aligned_postprocessed_report,
    write_generated_timeline,
    write_postprocessed_report,
    write_report_timeline,
)
from fflogs_damage_timeline.postprocess import (
    build_aligned_postprocessed_reports,
    build_generated_timelines,
    build_postprocessed_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch structured FF Logs damage taken timelines for kill fights.",
    )
    parser.add_argument(
        "--encounter",
        required=True,
        help="Encounter code (e.g., M11S, TOP, DSR)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of matching reports to fetch (default: 30)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/"),
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--postprocessed-dir",
        type=Path,
        default=None,
        help="Base directory for post-processed report JSON (default: <output-dir>/ with suffixed filenames)",
    )
    parser.add_argument(
        "--postprocessed-aligned-dir",
        type=Path,
        default=None,
        help="Base directory for aligned post-processed report JSON (default: <output-dir>/ with suffixed filenames)",
    )
    parser.add_argument(
        "--generated-timelines-dir",
        type=Path,
        default=None,
        help="Base directory for generated timeline JSON (default: <output-dir>/ with suffixed filenames)",
    )
    parser.add_argument(
        "--research-mechanics",
        action="store_true",
        help="Enrich generated timelines with guide-backed mechanic research",
    )
    parser.add_argument(
        "--open-websearch-command",
        default="npx",
        help="Command used to launch open-webSearch (default: npx)",
    )
    parser.add_argument(
        "--open-websearch-package",
        default="open-websearch@latest",
        help="open-webSearch package or executable target (default: open-websearch@latest)",
    )
    parser.add_argument(
        "--research-cache-dir",
        type=Path,
        default=Path(".research_cache"),
        help="Directory for cached research search results and extracted actions (default: .research_cache)",
    )
    parser.add_argument(
        "--skip-live-search",
        action="store_true",
        help="Use only cached research artifacts and skip live guide discovery",
    )
    parser.add_argument(
        "--search-engines",
        default="duckduckgo,bing,exa",
        help="Comma-separated open-webSearch engines to use (default: duckduckgo,bing,exa)",
    )
    parser.add_argument(
        "--research-llm-model",
        default="MiniMax-M2.7",
        help="MiniMax OpenAI-compatible model for research extraction (default: MiniMax-M2.7)",
    )
    return parser


def load_encounter_config(encounter_code: str) -> dict:
    loader = EncounterLoader()
    encounter = loader.get_by_code(encounter_code)
    if encounter is None:
        raise ValueError(f"Unknown encounter code: {encounter_code}")
    return {
        "code": encounter.code,
        "full_name": encounter.full_name,
        "boss_name": encounter.boss_name,
        "zone_id": encounter.zone_id,
        "encounter_id": encounter.encounter_id,
        "expansion": encounter.expansion,
        "category": encounter.category,
    }


def build_report_timeline(
    encounter_config: dict,
    report_details: dict,
    fight_timelines: list[dict],
) -> dict:
    return {
        "encounter": encounter_config,
        "report": {
            "code": report_details["code"],
            "title": report_details.get("title", ""),
            "start_time_ms": report_details["startTime"],
            "end_time_ms": report_details["endTime"],
            "kill_fight_count": len(fight_timelines),
        },
        "fights": fight_timelines,
    }


def build_research_service(args: argparse.Namespace) -> EncounterResearchService:
    search_engines = [engine.strip() for engine in args.search_engines.split(",") if engine.strip()]
    search_client = OpenWebSearchClient(
        command=args.open_websearch_command,
        package=args.open_websearch_package,
        engines=search_engines or None,
    )
    llm_client = MiniMaxClient(model=args.research_llm_model)
    return EncounterResearchService(
        search_client=search_client,
        llm_client=llm_client,
        cache_dir=args.research_cache_dir,
        skip_live_search=args.skip_live_search,
    )


def run(args: argparse.Namespace) -> int:
    try:
        encounter_config = load_encounter_config(args.encounter)
    except ValueError as error:
        logger.error("Failed to load encounter config: %s", error)
        return 1

    logger.info(
        "Fetching damage taken timelines for %s (%s, zone_id=%d)",
        encounter_config["full_name"],
        encounter_config["code"],
        encounter_config["zone_id"],
    )

    client = FFLogsGraphQLClient()

    try:
        encounter_id = encounter_config["encounter_id"] or client.resolve_encounter_id(
            zone_id=encounter_config["zone_id"],
            boss_name=encounter_config["boss_name"],
            full_name=encounter_config["full_name"],
        )
    except Exception as error:
        logger.error("Failed to resolve encounter ID: %s", error)
        return 1

    encounter_config = {**encounter_config, "encounter_id": encounter_id}
    postprocessed_dir = args.postprocessed_dir or args.output_dir
    aligned_postprocessed_dir = args.postprocessed_aligned_dir or args.output_dir
    generated_timelines_dir = args.generated_timelines_dir or args.output_dir

    logger.info("Fetching reports until %d matching kill reports are found...", args.limit)
    try:
        reports = client.fetch_reports(
            zone_id=encounter_config["zone_id"],
            encounter_id=encounter_id,
            limit=args.limit,
        )
    except Exception as error:
        logger.error("Failed to fetch matching reports: %s", error)
        return 1

    logger.info("Found %d matching kill reports", len(reports))
    if not reports:
        logger.warning("No matching kill reports found")
        return 0

    successful_reports = 0
    failed_reports = 0
    postprocessed_reports: list[dict] = []

    for report in reports:
        report_code = report["code"]
        logger.info(
            "Processing report %s: %s (%d kill fights)",
            report_code,
            report.get("title", ""),
            len(report.get("fights") or []),
        )

        try:
            report_details = client.fetch_report_details(report_code, encounter_id)
            if report_details is None:
                raise ValueError(f"Report {report_code} was not found")

            fight_timelines: list[dict] = []
            for fight in report_details["fights"]:
                events = client.fetch_events(
                    report_code,
                    fight["id"],
                    fight["startTime"],
                    fight["endTime"],
                )
                fight_timelines.append(
                    normalize_fight_timeline(
                        fight=fight,
                        report_start_time=report_details["startTime"],
                        events=events,
                        actors=report_details["actors"],
                        abilities=report_details["abilities"],
                    )
                )

            if not fight_timelines:
                logger.warning("Skipping report %s because it has no kill fights", report_code)
                continue

            report_timeline = build_report_timeline(
                encounter_config=encounter_config,
                report_details=report_details,
                fight_timelines=fight_timelines,
            )
            postprocessed_report = build_postprocessed_report(report_timeline)
            output_path = write_report_timeline(
                output_dir=args.output_dir,
                encounter_code=encounter_config["code"],
                report_timeline=report_timeline,
            )
            postprocessed_output_path = write_postprocessed_report(
                output_dir=postprocessed_dir,
                encounter_code=encounter_config["code"],
                report_code=report_code,
                postprocessed_report=postprocessed_report,
            )
            postprocessed_reports.append(postprocessed_report)
            successful_reports += 1
            logger.info(
                "Wrote %s and %s with %d fight timelines",
                output_path,
                postprocessed_output_path,
                len(fight_timelines),
            )
        except Exception as error:
            failed_reports += 1
            logger.error("Failed to process report %s: %s", report_code, error)

    if postprocessed_reports:
        aligned_reports = build_aligned_postprocessed_reports(postprocessed_reports)
        for aligned_report in aligned_reports:
            report_code = aligned_report["report"]["code"]
            aligned_output_path = write_aligned_postprocessed_report(
                output_dir=aligned_postprocessed_dir,
                encounter_code=encounter_config["code"],
                report_code=report_code,
                aligned_report=aligned_report,
            )
            logger.info("Wrote aligned post-processed report: %s", aligned_output_path)

        generated_timelines = build_generated_timelines(aligned_reports)
        if args.research_mechanics:
            search_client = None
            try:
                research_service = build_research_service(args)
                search_client = research_service.search_client
                generated_timelines = research_service.enrich_generated_timelines(
                    encounter_config,
                    generated_timelines,
                )
                logger.info(
                    "Enriched %d generated timelines with encounter research",
                    len(generated_timelines),
                )
            except Exception as error:
                logger.warning(
                    "Research enrichment failed; writing base generated timelines instead: %s",
                    error,
                )
            finally:
                if search_client is not None and hasattr(search_client, "close"):
                    search_client.close()

        for generated_timeline in generated_timelines:
            generated_output_path = write_generated_timeline(
                output_dir=generated_timelines_dir,
                encounter_code=generated_timeline["encounter_code"],
                fight_index=generated_timeline["fight_index"],
                branch_index=generated_timeline["branch_index"],
                generated_timeline=generated_timeline,
            )
            logger.info("Wrote generated timeline: %s", generated_output_path)

    logger.info(
        "Done. Successful reports: %d, Failed reports: %d",
        successful_reports,
        failed_reports,
    )
    return 0 if failed_reports == 0 else 1


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
