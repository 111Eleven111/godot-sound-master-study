"""Analyze audio-related gameplay events against audio-exploration ratings."""

import csv
import re
from pathlib import Path
from statistics import mean, median, stdev

QUESTIONNAIRE_PATH = Path(__file__).parent / "study-data" / "data-with-order.txt"
STUDY_DATA_PATH = QUESTIONNAIRE_PATH.parent
SCENARIOS = ("A", "B", "C", "D")
SCENARIO_QUESTION_START = 17
AUDIO_EXPLORATION_QUESTION_INDEX = 3
AUDIO_EVENTS = ("sonification", "musicking")


def _read_questionnaire(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = [
            row
            for row in csv.reader(questionnaire_file, delimiter=";", quotechar='"')
            if any(cell.strip() for cell in row)
        ]
    if not rows:
        raise ValueError(f"Questionnaire file is empty: {path}")
    return rows[0], rows[1:]


def _read_scenario_order(notes_path: Path) -> tuple[str, ...]:
    notes = notes_path.read_text(encoding="utf-8")
    match = re.search(
        r"\b([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\s*;\s*([ABCD])\b",
        notes,
    )
    if match is None:
        raise ValueError(f"Could not find scenario order in {notes_path}")
    return match.groups()


def _session_duration_minutes(rows: list[dict[str, str]]) -> float:
    timestamps = [float(row["timestamp_seconds"]) for row in rows]
    duration = (max(timestamps) - min(timestamps)) / 60
    if duration <= 0:
        raise ValueError("A session must have a positive duration")
    return duration


def _audio_event_rate(session_path: Path) -> float:
    with session_path.open(newline="", encoding="utf-8") as session_file:
        rows = list(csv.DictReader(session_file))
    if len(rows) < 2:
        raise ValueError(f"Session has too few rows: {session_path}")

    audio_event_count = sum(row["event"] in AUDIO_EVENTS for row in rows)
    return audio_event_count / _session_duration_minutes(rows)


def collect_audio_exploration_data(
    questionnaire_path: Path = QUESTIONNAIRE_PATH,
    study_data_path: Path = STUDY_DATA_PATH,
) -> dict[str, dict[str, list[float | str]]]:
    """Return aligned audio-event rates and questionnaire ratings by scenario."""
    _, questionnaire_rows = _read_questionnaire(questionnaire_path)
    data = {
        scenario: {"participant": [], "event_rate": [], "rating": []}
        for scenario in SCENARIOS
    }

    participant_directories = sorted(
        study_data_path.glob("study-p*"),
        key=lambda path: int(path.name.removeprefix("study-p")),
    )
    if len(participant_directories) != len(questionnaire_rows):
        raise ValueError(
            "The number of participant folders does not match questionnaire rows: "
            f"{len(participant_directories)} folders vs {len(questionnaire_rows)} rows"
        )

    for participant_index, participant_directory in enumerate(
        participant_directories
    ):
        questionnaire_row = questionnaire_rows[participant_index]
        scenario_order = _read_scenario_order(
            participant_directory / "notes.txt"
        )
        if questionnaire_row[0].strip().upper() != "".join(scenario_order):
            raise ValueError(
                f"Scenario order mismatch for {participant_directory}: "
                f"questionnaire={questionnaire_row[0]!r}, "
                f"notes={''.join(scenario_order)!r}"
            )

        session_paths = sorted(participant_directory.glob("session_*.csv"))
        if len(session_paths) != len(SCENARIOS):
            raise ValueError(
                f"Expected four sessions in {participant_directory}, "
                f"found {len(session_paths)}"
            )

        for session_path, scenario in zip(session_paths, scenario_order):
            response_column = (
                SCENARIO_QUESTION_START
                + scenario_order.index(scenario) * 8
                + AUDIO_EXPLORATION_QUESTION_INDEX
            )
            response = questionnaire_row[response_column].strip()
            if not response:
                continue
            data[scenario]["participant"].append(
                participant_directory.name
            )
            data[scenario]["event_rate"].append(_audio_event_rate(session_path))
            data[scenario]["rating"].append(float(response))

    return data


def _holm_adjust(p_values: list[float]) -> list[float]:
    """Apply Holm's step-down correction while preserving input order."""
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, index in enumerate(order):
        corrected = min(1.0, (len(p_values) - rank) * p_values[index])
        corrected = max(previous, corrected)
        adjusted[index] = corrected
        previous = corrected
    return adjusted


def run_audio_exploration_analysis(
    questionnaire_path: Path = QUESTIONNAIRE_PATH,
    study_data_path: Path = STUDY_DATA_PATH,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Run descriptive, repeated-measures, pairwise, and correlation analyses."""
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha!r}")
    try:
        from scipy.stats import friedmanchisquare, spearmanr, wilcoxon
    except ImportError as error:
        raise RuntimeError(
            "This analysis requires a working SciPy installation."
        ) from error

    data = collect_audio_exploration_data(questionnaire_path, study_data_path)
    print("Audio events:", ", ".join(AUDIO_EVENTS))
    print("Rating: I wanted to explore how the audio changed as I played.")
    print(f"Alpha: {alpha}\n")

    for scenario in SCENARIOS:
        rates = data[scenario]["event_rate"]
        ratings = data[scenario]["rating"]
        print(
            f"{scenario}: n={len(rates)}, "
            f"event rate mean={mean(rates):.3f}, median={median(rates):.3f}, "
            f"sd={stdev(rates):.3f}; rating mean={mean(ratings):.3f}"
        )

    complete_participants = set.intersection(
        *(
            set(data[scenario]["participant"])
            for scenario in SCENARIOS
        )
    )

    def values_for(
        scenario: str, value_name: str, participants: set[str]
    ) -> list[float]:
        scenario_data = data[scenario]
        return [
            float(value)
            for participant, value in zip(
                scenario_data["participant"],
                scenario_data[value_name],
            )
            if participant in participants
        ]

    friedman = friedmanchisquare(
        *(
            values_for(scenario, "rating", complete_participants)
            for scenario in SCENARIOS
        )
    )
    print(
        f"\nFriedman test on ratings across scenarios: "
        f"n={len(complete_participants)}, "
        f"chi2={friedman.statistic:.4f}, p={friedman.pvalue:.4f}"
    )

    pairs = []
    pair_p_values = []
    for first_index, first in enumerate(SCENARIOS):
        for second in SCENARIOS[first_index + 1 :]:
            paired_participants = set(data[first]["participant"]) & set(
                data[second]["participant"]
            )
            first_values = values_for(first, "rating", paired_participants)
            second_values = values_for(second, "rating", paired_participants)
            result = wilcoxon(first_values, second_values)
            pairs.append(
                {
                    "first": first,
                    "second": second,
                    "n": len(paired_participants),
                    "statistic": float(result.statistic),
                    "p_value": float(result.pvalue),
                }
            )
            pair_p_values.append(float(result.pvalue))

    adjusted_p_values = _holm_adjust(pair_p_values)
    print("\nPairwise Wilcoxon signed-rank tests on ratings (Holm corrected):")
    for pair, adjusted_p in zip(pairs, adjusted_p_values):
        pair["holm_p_value"] = adjusted_p
        print(
            f"{pair['first']} vs {pair['second']}: "
            f"p={pair['p_value']:.4f}, Holm p={adjusted_p:.4f}"
        )

    correlations = {}
    print("\nSpearman correlations by scenario:")
    for scenario in SCENARIOS:
        result = spearmanr(
            values_for(
                scenario,
                "event_rate",
                set(data[scenario]["participant"]),
            ),
            values_for(
                scenario,
                "rating",
                set(data[scenario]["participant"]),
            ),
        )
        correlations[scenario] = {
            "rho": float(result.statistic),
            "p_value": float(result.pvalue),
            "n": len(data[scenario]["participant"]),
        }
        print(
            f"{scenario}: rho={result.statistic:.4f}, "
            f"p={result.pvalue:.4f}, n={len(data[scenario]['participant'])}"
        )

    return {
        "data": data,
        "friedman": {
            "statistic": float(friedman.statistic),
            "p_value": float(friedman.pvalue),
        },
        "pairwise_wilcoxon": pairs,
        "spearman": correlations,
    }


def main() -> None:
    run_audio_exploration_analysis()


if __name__ == "__main__":
    main()
