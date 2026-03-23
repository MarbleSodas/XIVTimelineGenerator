"""Output helpers for structured FF Logs damage timeline data."""

from pathlib import Path
import json


def ensure_encounter_dir(output_dir: Path, encounter_code: str) -> Path:
    encounter_dir = output_dir / encounter_code
    encounter_dir.mkdir(parents=True, exist_ok=True)
    return encounter_dir


def write_report_timeline(
    output_dir: Path,
    encounter_code: str,
    report_timeline: dict,
) -> Path:
    """Write one structured timeline file per FF Logs report."""
    encounter_dir = ensure_encounter_dir(output_dir, encounter_code)

    report_code = report_timeline["report"]["code"]
    output_path = encounter_dir / f"{report_code}.json"

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(report_timeline, file_handle, indent=2)

    return output_path


def write_postprocessed_report(
    output_dir: Path,
    encounter_code: str,
    report_code: str,
    postprocessed_report: dict,
) -> Path:
    """Write a post-processed report JSON into the encounter directory."""
    encounter_dir = ensure_encounter_dir(output_dir, encounter_code)

    output_path = encounter_dir / f"{report_code}.postprocessed.json"
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(postprocessed_report, file_handle, indent=2)

    return output_path


def write_aligned_postprocessed_report(
    output_dir: Path,
    encounter_code: str,
    report_code: str,
    aligned_report: dict,
) -> Path:
    """Write an aligned post-processed report JSON into the encounter directory."""
    encounter_dir = ensure_encounter_dir(output_dir, encounter_code)

    output_path = encounter_dir / f"{report_code}.aligned.json"
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(aligned_report, file_handle, indent=2)

    return output_path


def write_generated_timeline(
    output_dir: Path,
    encounter_code: str,
    fight_index: int,
    branch_index: int,
    generated_timeline: dict,
) -> Path:
    """Write a generated timeline branch JSON into the encounter directory."""
    encounter_dir = ensure_encounter_dir(output_dir, encounter_code)

    output_path = encounter_dir / f"fight-{fight_index}-branch-{branch_index}.timeline.json"
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(generated_timeline, file_handle, indent=2)

    return output_path
