"""Measure returns to previously landed-on platforms.

Each ``platform_landed`` event contains a platform identifier in its ``info``
column. A return is counted when that identifier has already appeared earlier
in the same session. This measures revisiting a known platform rather than
inferring backtracking from horizontal direction.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


SCENARIOS = ("A", "B", "C", "D")
DEFAULT_DATA_ROOT = Path(__file__).parent / "study-data"


def read_scenario_order(notes_path: Path) -> tuple[str, ...]:
    text = notes_path.read_text(encoding="utf-8")
    match = re.search(r"\b([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\b", text)
    if match is None:
        raise ValueError(f"Could not find four-scenario order in {notes_path}")
    return match.groups()


def landed_platform_ids(session_path: Path) -> list[str]:
    """Return platform identifiers in the order they were landed on."""
    with session_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    platform_ids = []
    for row in rows:
        if row.get("event") != "platform_landed":
            continue
        platform_id = (row.get("info") or "").strip()
        if not platform_id:
            raise ValueError(
                f"platform_landed event has no platform ID in {session_path}"
            )
        platform_ids.append(platform_id)
    return platform_ids


def measure_backtracking(
    platform_ids: list[str],
) -> dict[str, int | float]:
    """Calculate returns to known platforms and distinct revisited platforms."""
    visited: set[str] = set()
    revisited: set[str] = set()
    return_landings = 0
    return_episodes = 0
    in_return = False

    for platform_id in platform_ids:
        is_return = platform_id in visited
        if is_return:
            return_landings += 1
            revisited.add(platform_id)
            if not in_return:
                return_episodes += 1
        in_return = is_return
        visited.add(platform_id)

    return {
        "platform_landings": len(platform_ids),
        "unique_platforms": len(visited),
        "return_landings": return_landings,
        "revisited_platforms": len(revisited),
        "return_episodes": return_episodes,
    }


def analyze(data_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for participant_path in sorted(data_root.glob("study-p*")):
        if not participant_path.is_dir():
            continue
        session_paths = sorted(participant_path.glob("session_*.csv"))
        if len(session_paths) != 4:
            raise ValueError(
                f"Expected four sessions in {participant_path}, found {len(session_paths)}"
            )
        order = read_scenario_order(participant_path / "notes.txt")
        for play_position, (session_path, scenario) in enumerate(
            zip(session_paths, order), start=1
        ):
            platform_ids = landed_platform_ids(session_path)
            metrics = measure_backtracking(platform_ids)
            records.append({
                "participant": participant_path.name,
                "scenario": scenario,
                "play_position": play_position,
                **metrics,
            })
    return records


def write_csv(records: list[dict[str, object]], output_path: Path) -> None:
    if not records:
        raise ValueError("No participant sessions found")
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path, default=Path("backtracking-results.csv"))
    args = parser.parse_args()
    records = analyze(args.data_root)
    write_csv(records, args.output)
    print(f"Wrote {len(records)} session rows to {args.output}")


if __name__ == "__main__":
    main()
