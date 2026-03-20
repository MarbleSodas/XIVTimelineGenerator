"""Output module for FF Logs damage timeline data."""

from pathlib import Path
import json


def write_timeline(output_dir: Path, encounter_code: str, fight_data: dict, events: list) -> Path:
    """
    Write timeline data to a JSON file.

    Creates output directory if it doesn't exist. Skips writing if file already exists.

    Args:
        output_dir: Base output directory
        encounter_code: Encounter code (e.g., "M11S")
        fight_data: Dictionary containing encounter, fight, and report info
        events: List of damage events to write

    Returns:
        Path to the written JSON file

    File is written to: output_dir/encounter_code/{report_code}-fight-{fight_id}.json
    """
    # Create output directory structure
    encounter_dir = output_dir / encounter_code
    encounter_dir.mkdir(parents=True, exist_ok=True)

    # Build output data structure
    output_data = {
        "encounter": fight_data["encounter"],
        "fight": fight_data["fight"],
        "report": fight_data["report"],
        "damage_events": events,
    }

    # Determine filename
    report_code = fight_data["report"]["code"]
    fight_id = fight_data["fight"]["fight_id"]
    filename = f"{report_code}-fight-{fight_id}.json"
    output_path = encounter_dir / filename

    # Skip if file already exists
    if output_path.exists():
        return output_path

    # Write JSON file
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    return output_path
