import argparse
import logging
import sys
from pathlib import Path
from typing import cast

from fflogs_damage_timeline.graphql_client import FFLogsGraphQLClient
from fflogs_damage_timeline.filters import filter_damage_events, Event
from fflogs_damage_timeline.normalizer import normalize_timestamps
from fflogs_damage_timeline.output import write_timeline
from fflogs.encounters import EncounterLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch FFLogs damage timelines for encounters.",
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
        help="Number of kill reports to fetch (default: 30)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/"),
        help="Output directory (default: output/)",
    )
    return parser


def load_encounter_config(encounter_code: str) -> dict:
    """Load encounter configuration from YAML using EncounterLoader."""
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


def run(args: argparse.Namespace) -> int:
    try:
        encounter_config = load_encounter_config(args.encounter)
    except ValueError as e:
        logger.error("Failed to load encounter config: %s", e)
        return 1

    logger.info(
        "Fetching damage timeline for %s (%s, zone_id=%d)",
        encounter_config["full_name"],
        encounter_config["code"],
        encounter_config["zone_id"],
    )

    try:
        client = FFLogsGraphQLClient()
    except ValueError as e:
        logger.error("Failed to create client: %s", e)
        return 1

    logger.info("Fetching kill reports (limit=%d)...", args.limit)
    reports = client.fetch_reports(
        zone_id=encounter_config["zone_id"],
        encounter_id=encounter_config["encounter_id"] or 0,
    )
    logger.info("Found %d kill reports", len(reports))

    if not reports:
        logger.warning("No kill reports found")
        return 0

    total_fights = 0
    successful_fights = 0
    skipped_fights = 0
    failed_fights = 0

    for report in reports[: args.limit]:
        report_code = report["code"]
        logger.info("Processing report %s: %s", report_code, report.get("title", ""))

        try:
            fights = client.fetch_fights(report_code, encounter_config["encounter_id"] or 0)
        except Exception as e:
            logger.error("Failed to fetch fights for report %s: %s", report_code, e)
            continue

        for fight in fights:
            fight_id = fight["id"]
            total_fights += 1

            fight_data = {
                "encounter": encounter_config,
                "fight": {
                    "fight_id": fight_id,
                    "start_time": fight["startTime"],
                    "end_time": fight["endTime"],
                    "encounter_id": fight["encounterID"],
                    "difficulty": fight.get("difficulty"),
                },
                "report": {
                    "code": report_code,
                    "title": report.get("title", ""),
                    "start_time": report["startTime"],
                    "end_time": report["endTime"],
                },
            }

            output_path = args.output_dir / encounter_config["code"] / f"{report_code}-fight-{fight_id}.json"
            if output_path.exists():
                logger.debug("Skipping existing file: %s", output_path)
                skipped_fights += 1
                continue

            try:
                events = client.fetch_events(
                    report_code,
                    fight_id,
                    fight["startTime"],
                    fight["endTime"],
                )
            except Exception as e:
                logger.error(
                    "Failed to fetch events for report %s fight %d: %s",
                    report_code,
                    fight_id,
                    e,
                )
                failed_fights += 1
                continue

            try:
                filtered = filter_damage_events(cast(list[Event], events), {})
                normalized = normalize_timestamps(filtered, fight["startTime"])
            except Exception as e:
                logger.error(
                    "Failed to process events for report %s fight %d: %s",
                    report_code,
                    fight_id,
                    e,
                )
                failed_fights += 1
                continue

            try:
                write_timeline(args.output_dir, encounter_config["code"], fight_data, normalized)
                successful_fights += 1
                logger.info(
                    "Wrote timeline: %s/fight-%d (%d events)",
                    report_code,
                    fight_id,
                    len(normalized),
                )
            except Exception as e:
                logger.error(
                    "Failed to write timeline for report %s fight %d: %s",
                    report_code,
                    fight_id,
                    e,
                )
                failed_fights += 1
                continue

    logger.info(
        "Done. Total fights: %d, Successful: %d, Skipped: %d, Failed: %d",
        total_fights,
        successful_fights,
        skipped_fights,
        failed_fights,
    )

    return 0 if failed_fights == 0 else 1


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
