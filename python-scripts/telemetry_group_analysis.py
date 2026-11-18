"""Compare telemetry behaviour between platforming-experience groups.

The unit of inference is the participant, not the individual telemetry event.
Each participant contributes up to four scenario sessions. Counts are also
reported as rates per minute because session durations differ.

The default comparison is experience levels 1-2 versus 3-4. The bootstrap
resamples participants within each group, preserving the repeated sessions
belonging to each participant.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


SCRIPT_DIR = Path(__file__).parent
QUESTIONNAIRE_PATH = SCRIPT_DIR / "study-data" / "data-with-order.txt"
TELEMETRY_PATH = SCRIPT_DIR / "study-data"
SCENARIOS = ("A", "B", "C", "D")
EXPERIENCE_COLUMN = 14
EVENT_METRICS = {
    "audio_events": {"sonification", "musicking"},
    "sonification": {"sonification"},
    "musicking": {"musicking"},
    "jumps": {"jump_executed"},
    "landings": {"landed"},
    "coins": {"coin_collected"},
    "top_reaches": {"top/checkpoint reached"},
}


def _read_orders(path: Path) -> dict[str, tuple[str, ...]]:
    orders = {}
    for notes_path in sorted(path.glob("study-p*/notes.txt")):
        match = re.search(r"\b([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\b",
                          notes_path.read_text(encoding="utf-8"))
        if match is None:
            raise ValueError(f"Could not find four-scenario order in {notes_path}")
        orders[notes_path.parent.name] = match.groups()
    return orders


def _experience_groups(questionnaire_path: Path) -> dict[str, str]:
    with questionnaire_path.open(newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.reader(file, delimiter=";") if any(row)]
    groups = {}
    for index, row in enumerate(rows[1:], start=1):
        if len(row) <= EXPERIENCE_COLUMN:
            raise ValueError(f"Questionnaire row {index + 1} has too few columns")
        try:
            experience = float(row[EXPERIENCE_COLUMN].strip())
        except ValueError as error:
            raise ValueError(
                f"Invalid experience value on questionnaire row {index + 1}: "
                f"{row[EXPERIENCE_COLUMN]!r}"
            ) from error
        if experience in (1, 2):
            groups[f"study-p{index}"] = "experience_1_2"
        elif experience in (3, 4):
            groups[f"study-p{index}"] = "experience_3_4"
    return groups


def _session_metrics(session_path: Path) -> dict[str, float]:
    with session_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if len(rows) < 2:
        raise ValueError(f"Telemetry session has too few rows: {session_path}")
    timestamps = [float(row["timestamp_seconds"]) for row in rows]
    duration_minutes = (max(timestamps) - min(timestamps)) / 60
    if duration_minutes <= 0:
        raise ValueError(f"Telemetry session has no positive duration: {session_path}")

    metrics = {}
    for metric, event_names in EVENT_METRICS.items():
        count = sum(row["event"] in event_names for row in rows)
        metrics[f"{metric}_count"] = float(count)
        metrics[f"{metric}_per_minute"] = count / duration_minutes

    far_falls = sum(
        "far-fall" in (row.get("info", "") or "").lower()
        for row in rows
    )
    metrics["far_falls_count"] = float(far_falls)
    metrics["far_falls_per_minute"] = far_falls / duration_minutes
    metrics["duration_minutes"] = duration_minutes
    return metrics


def collect_telemetry(
    telemetry_path: Path = TELEMETRY_PATH,
    questionnaire_path: Path = QUESTIONNAIRE_PATH,
) -> list[dict[str, object]]:
    """Align each telemetry session with participant, scenario, and group."""
    orders = _read_orders(telemetry_path)
    groups = _experience_groups(questionnaire_path)
    records: list[dict[str, object]] = []
    for participant, group in groups.items():
        participant_path = telemetry_path / participant
        session_paths = sorted(participant_path.glob("session_*.csv"))
        if len(session_paths) != 4:
            raise ValueError(
                f"Expected four sessions in {participant_path}, found {len(session_paths)}"
            )
        for play_position, (session_path, scenario) in enumerate(
            zip(session_paths, orders[participant]), start=1
        ):
            record: dict[str, object] = {
                "participant": participant,
                "group": group,
                "scenario": scenario,
                "play_position": play_position,
            }
            record.update(_session_metrics(session_path))
            records.append(record)
    return records


def _participant_metric_means(
    records: list[dict[str, object]], metric: str
) -> dict[str, tuple[str, float]]:
    values: dict[str, list[float]] = defaultdict(list)
    groups: dict[str, str] = {}
    for record in records:
        participant = str(record["participant"])
        values[participant].append(float(record[metric]))
        groups[participant] = str(record["group"])
    return {
        participant: (groups[participant], float(np.mean(metric_values)))
        for participant, metric_values in values.items()
    }


def bootstrap_difference(
    records: list[dict[str, object]],
    metric: str,
    iterations: int,
    seed: int,
) -> dict[str, object]:
    participant_means = _participant_metric_means(records, metric)
    grouped: dict[str, list[float]] = defaultdict(list)
    for group, value in participant_means.values():
        grouped[group].append(value)
    first, second = sorted(grouped)
    first_values = np.asarray(grouped[first])
    second_values = np.asarray(grouped[second])
    rng = np.random.default_rng(seed)
    samples = np.array([
        rng.choice(first_values, len(first_values), replace=True).mean()
        - rng.choice(second_values, len(second_values), replace=True).mean()
        for _ in range(iterations)
    ])
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "group_a": first,
        "group_b": second,
        "estimate_a_minus_b": float(first_values.mean() - second_values.mean()),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "participant_counts": {first: len(first_values), second: len(second_values)},
    }


def fit_mixed_models(records: list[dict[str, object]], metrics: list[str]) -> dict[str, object]:
    """Fit exploratory participant-random-intercept models if dependencies exist."""
    try:
        import pandas as pd
        from statsmodels.formula.api import mixedlm
    except ImportError as error:
        return {"status": "not_run", "reason": str(error)}

    frame = pd.DataFrame(records)
    results: dict[str, object] = {"status": "run"}
    for metric in metrics:
        formula = f"{metric} ~ C(scenario) + C(play_position) + C(group)"
        try:
            model = mixedlm(formula, frame, groups=frame["participant"]).fit(
                reml=False, method="lbfgs"
            )
            results[metric] = {
                "formula": formula,
                "converged": bool(model.converged),
                "group_coefficient": float(model.params["C(group)[T.experience_3_4]"]),
                "group_p_value": float(model.pvalues["C(group)[T.experience_3_4]"]),
            }
        except (KeyError, ValueError, np.linalg.LinAlgError) as error:
            results[metric] = {"formula": formula, "status": "failed", "reason": str(error)}
    return results


def analyze(
    telemetry_path: Path = TELEMETRY_PATH,
    questionnaire_path: Path = QUESTIONNAIRE_PATH,
    bootstrap_iterations: int = 5000,
    seed: int = 2026,
) -> dict[str, object]:
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    records = collect_telemetry(telemetry_path, questionnaire_path)
    metrics = [
        "audio_events_per_minute",
        "sonification_per_minute",
        "musicking_per_minute",
        "jumps_per_minute",
        "far_falls_per_minute",
        "landings_per_minute",
        "coins_per_minute",
        "top_reaches_per_minute",
    ]
    return {
        "feasibility": {
            "participants": len({record["participant"] for record in records}),
            "sessions": len(records),
            "groups": {
                group: len({
                    record["participant"]
                    for record in records
                    if record["group"] == group
                })
                for group in sorted({record["group"] for record in records})
            },
            "unit_of_bootstrap": "participant",
        },
        "descriptive_means": {
            metric: {
                group: float(np.mean([
                    float(record[metric])
                    for record in records
                    if record["group"] == group
                ]))
                for group in sorted({record["group"] for record in records})
            }
            for metric in metrics
        },
        "bootstrap": {
            metric: bootstrap_difference(records, metric, bootstrap_iterations, seed + index)
            for index, metric in enumerate(metrics)
        },
        "mixed_models": fit_mixed_models(records, metrics),
        "records": records,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry", type=Path, default=TELEMETRY_PATH)
    parser.add_argument("--questionnaire", type=Path, default=QUESTIONNAIRE_PATH)
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = analyze(
        args.telemetry,
        args.questionnaire,
        args.bootstrap_iterations,
        args.seed,
    )
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
