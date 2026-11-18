"""Compare repeated-measures models for the questionnaire data.

The questionnaire contains four observations per participant (one per
scenario) and eight Likert responses per observation. This script reshapes
those responses to long format, checks whether the design supports
participant-clustered analysis, runs a participant bootstrap, and optionally
fits interaction models when statsmodels is installed. The models include
scenario, play position, experience group, scenario-by-group, and
question-by-group terms.

Examples:

    data/bin/python python-scripts/repeated_measures_analysis.py
    data/bin/python python-scripts/repeated_measures_analysis.py \
        --group participant_type --output analysis-results.json

The default grouping compares platforming-game experience levels 1-2 with
levels 3-4, matching the existing regression call in read_questionnaire.py.
The results are exploratory: the sample is small and the outcome is ordinal.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


DEFAULT_INPUT = Path(__file__).parent / "study-data" / "data-with-order.txt"
SCENARIOS = ("A", "B", "C", "D")
SCENARIO_QUESTION_START = 17
SCENARIO_QUESTION_COUNT = 8
EXPERIENCE_COLUMN = 14
PARTICIPANT_TYPE_COLUMNS = range(8, 14)


@dataclass(frozen=True)
class Observation:
    participant: str
    scenario: str
    play_position: int
    question: str
    rating: float
    group: str


def read_observations(path: Path, group_kind: str) -> tuple[list[Observation], int]:
    """Read valid repeated observations and return them with participant count."""
    with path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = [
            row
            for row in csv.reader(questionnaire_file, delimiter=";")
            if any(cell.strip() for cell in row)
        ]
    if not rows:
        raise ValueError(f"Questionnaire file is empty: {path}")

    headers, participant_rows = rows[0], rows[1:]
    questions = headers[
        SCENARIO_QUESTION_START : SCENARIO_QUESTION_START + SCENARIO_QUESTION_COUNT
    ]
    observations: list[Observation] = []
    participant_count = 0

    for row_number, row in enumerate(participant_rows, start=2):
        if len(row) <= EXPERIENCE_COLUMN:
            raise ValueError(f"Row {row_number} has too few columns: {len(row)}")
        participant_id = row[1].strip() or f"row-{row_number}"
        order = row[0].strip().upper()
        if len(order) != len(SCENARIOS) or set(order) != set(SCENARIOS):
            raise ValueError(f"Invalid scenario order on row {row_number}: {order!r}")

        group = _group_for_row(row, group_kind)
        if group is None:
            continue
        participant_count += 1

        for play_position, scenario in enumerate(order):
            start = SCENARIO_QUESTION_START + play_position * SCENARIO_QUESTION_COUNT
            for question_index, question in enumerate(questions):
                value = row[start + question_index].strip()
                if not value:
                    continue
                try:
                    rating = float(value)
                except ValueError as error:
                    raise ValueError(
                        f"Invalid rating on row {row_number}, column "
                        f"{start + question_index}: {value!r}"
                    ) from error
                if not 0 <= rating <= 4:
                    raise ValueError(
                        f"Rating outside expected 0-4 range on row {row_number}: {rating}"
                    )
                observations.append(
                    Observation(
                        participant_id,
                        scenario,
                        play_position + 1,
                        question,
                        rating,
                        group,
                    )
                )
    return observations, participant_count


def _group_for_row(row: list[str], group_kind: str) -> str | None:
    """Return a stable analysis group, excluding rows outside the comparison."""
    if group_kind == "experience":
        try:
            experience = float(row[EXPERIENCE_COLUMN].strip())
        except ValueError as error:
            raise ValueError(
                f"Invalid platforming-game experience level: {row[EXPERIENCE_COLUMN]!r}"
            ) from error
        if experience in (1, 2):
            return "experience_1_2"
        if experience in (3, 4):
            return "experience_3_4"
        return None

    labels = [row[index].strip() for index in PARTICIPANT_TYPE_COLUMNS]
    selected = [label for label in labels if label]
    if not selected:
        raise ValueError("Participant type is missing")
    return " + ".join(selected)


def _participant_means(
    observations: list[Observation],
    question: str,
) -> dict[str, tuple[str, float]]:
    """Return participant-level means for one question, keyed by participant."""
    values: dict[str, list[float]] = {}
    groups: dict[str, str] = {}
    for observation in observations:
        if observation.question != question:
            continue
        values.setdefault(observation.participant, []).append(observation.rating)
        groups[observation.participant] = observation.group
    return {
        participant: (groups[participant], float(np.mean(ratings)))
        for participant, ratings in values.items()
    }


def bootstrap_group_difference(
    observations: list[Observation],
    question: str,
    iterations: int,
    seed: int,
    group_pair: tuple[str, str] | None = None,
) -> dict[str, float | int | None]:
    """Bootstrap the difference in participant-level means between two groups."""
    participant_means = _participant_means(observations, question)
    by_group: dict[str, list[float]] = {}
    for group, value in participant_means.values():
        by_group.setdefault(group, []).append(value)
    if group_pair is None:
        if len(by_group) != 2:
            return {
                "estimate": None,
                "lower_95": None,
                "upper_95": None,
                "n": len(participant_means),
            }
        first, second = sorted(by_group)
    else:
        first, second = group_pair
        if first not in by_group or second not in by_group:
            return {
                "estimate": None,
                "lower_95": None,
                "upper_95": None,
                "n": len(participant_means),
            }
    if len(by_group[first]) < 2 or len(by_group[second]) < 2:
        return {"estimate": None, "lower_95": None, "upper_95": None, "n": len(participant_means)}

    first_values, second_values = np.asarray(by_group[first]), np.asarray(by_group[second])
    estimate = float(first_values.mean() - second_values.mean())
    rng = np.random.default_rng(seed)
    bootstrap = np.empty(iterations)
    for index in range(iterations):
        bootstrap[index] = (
            rng.choice(first_values, len(first_values), replace=True).mean()
            - rng.choice(second_values, len(second_values), replace=True).mean()
        )
    lower, upper = np.quantile(bootstrap, [0.025, 0.975])
    return {
        "group_a": first,
        "group_b": second,
        "estimate": estimate,
        "lower_95": float(lower),
        "upper_95": float(upper),
        "n": len(participant_means),
    }


def _bootstrap_samples(
    observations: list[Observation],
    question: str,
    iterations: int,
    seed: int,
) -> tuple[str, str, float, np.ndarray] | None:
    """Return bootstrap differences and labels for a two-group comparison."""
    participant_means = _participant_means(observations, question)
    by_group: dict[str, list[float]] = {}
    for group, value in participant_means.values():
        by_group.setdefault(group, []).append(value)
    if len(by_group) != 2:
        return None
    first, second = sorted(by_group)
    first_values = np.asarray(by_group[first])
    second_values = np.asarray(by_group[second])
    if len(first_values) < 2 or len(second_values) < 2:
        return None
    rng = np.random.default_rng(seed)
    samples = np.asarray(
        [
            rng.choice(first_values, len(first_values), replace=True).mean()
            - rng.choice(second_values, len(second_values), replace=True).mean()
            for _ in range(iterations)
        ]
    )
    return first, second, float(first_values.mean() - second_values.mean()), samples


def plot_bootstrap_distributions(
    observations: list[Observation],
    output_directory: Path,
    iterations: int,
    seed: int,
) -> list[Path]:
    """Save one histogram figure showing bootstrap differences for each item."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("Plotting requires matplotlib.") from error

    output_directory.mkdir(parents=True, exist_ok=True)
    questions = list(dict.fromkeys(observation.question for observation in observations))
    figure, axes = plt.subplots(2, 4, figsize=(18, 9), constrained_layout=True)
    saved_paths: list[Path] = []
    for index, (axis, question) in enumerate(zip(axes.flat, questions)):
        bootstrap = _bootstrap_samples(
            observations, question, iterations, seed + index
        )
        if bootstrap is None:
            axis.set_visible(False)
            continue
        first, second, estimate, samples = bootstrap
        lower, upper = np.quantile(samples, [0.025, 0.975])
        axis.hist(samples, bins=35, color="#4c78a8", alpha=0.8, edgecolor="white")
        axis.axvline(0, color="#333333", linestyle="--", linewidth=1.2, label="No difference")
        axis.axvline(
            estimate, color="#e45756", linewidth=2, label="Observed difference"
        )
        axis.axvspan(lower, upper, color="#f2cf5b", alpha=0.22, label="95% interval")
        axis.set_title(_short_question_label(question))
        axis.set_xlabel(f"Mean difference: {first} − {second}")
        axis.set_ylabel("Bootstrap resamples")
        axis.grid(axis="y", alpha=0.25)
        axis.legend(fontsize=8)

    figure.suptitle(
        "Participant-clustered bootstrap differences by questionnaire item",
        fontsize=15,
    )
    output_path = output_directory / "questionnaire-bootstrap-distributions.png"
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
    saved_paths.append(output_path)
    return saved_paths


AGENCY_QUESTIONS = (
    "I wanted to explore how the audio changed as I played.",
    "I felt motivated to explore the paths and areas of the game world.",
    "The audio made me adapt how I moved through the level.",
)


def _agency_scores(
    observations: list[Observation],
) -> dict[str, tuple[str, float]]:
    """Return one sonic-agency composite score per participant."""
    values: dict[str, list[float]] = {}
    groups: dict[str, str] = {}
    for observation in observations:
        if observation.question not in AGENCY_QUESTIONS:
            continue
        values.setdefault(observation.participant, []).append(observation.rating)
        groups[observation.participant] = observation.group
    return {
        participant: (groups[participant], float(np.mean(ratings)))
        for participant, ratings in values.items()
    }


def _musical_backgrounds(path: Path) -> dict[str, str]:
    """Classify questionnaire participants by reported musical background."""
    backgrounds: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = [
            row
            for row in csv.reader(questionnaire_file, delimiter=";")
            if any(cell.strip() for cell in row)
        ]
    for row in rows[1:]:
        labels = [
            row[index].strip()
            for index in PARTICIPANT_TYPE_COLUMNS
            if row[index].strip()
        ]
        if not labels or not row[1].strip():
            continue
        backgrounds[row[1].strip()] = (
            "non-musician"
            if all(label == "Non-Musician / Casual Listener" for label in labels)
            else "musician/enthusiast"
        )
    return backgrounds


def plot_sonic_agency(
    observations: list[Observation],
    output_directory: Path,
) -> Path:
    """Plot participant sonic-agency composites by experience group."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    scores = _agency_scores(observations)
    groups = sorted({group for group, _ in scores.values()})
    figure, axis = plt.subplots(figsize=(8, 6))
    rng = np.random.default_rng(2026)
    grouped_values = []
    for index, group in enumerate(groups):
        values = np.asarray(
            [score for participant_group, score in scores.values() if participant_group == group]
        )
        grouped_values.append(values)
    axis.boxplot(
        grouped_values,
        positions=range(len(groups)),
        widths=0.42,
        patch_artist=True,
        whis=(0, 100),
        boxprops={"facecolor": "#c6dbef", "edgecolor": "#4c78a8"},
        medianprops={"color": "#e45756", "linewidth": 2},
        whiskerprops={"color": "#4c78a8"},
        capprops={"color": "#4c78a8"},
    )
    for index, (group, values) in enumerate(zip(groups, grouped_values)):
        x = np.full(len(values), index, dtype=float) + rng.uniform(-0.08, 0.08, len(values))
        axis.scatter(
            x,
            values,
            color="#4c78a8",
            alpha=0.8,
            edgecolor="white",
            linewidth=0.7,
            s=70,
            zorder=3,
        )
        axis.scatter(index, values.mean(), marker="D", color="#e45756", s=70, zorder=3)
    axis.set_xticks(range(len(groups)), ["Experience 1–2", "Experience 3–4"])
    axis.set_ylabel("Sonic-agency composite (0–4)")
    axis.set_title("Sonic-agency composite by platforming experience")
    axis.set_ylim(0, 4)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                color="none",
                markerfacecolor="#4c78a8",
                markeredgecolor="white",
                markersize=8,
                label="Participant",
            ),
            Line2D(
                [],
                [],
                marker="D",
                color="#e45756",
                markersize=7,
                label="Mean",
            ),
            Line2D([], [], color="#e45756", linewidth=2, label="Median"),
            Patch(
                facecolor="#c6dbef",
                edgecolor="#4c78a8",
                label="25th–75th percentile (box)",
            ),
            Line2D([], [], color="#4c78a8", linewidth=1.5, label="Minimum–maximum"),
        ],
        loc="lower right",
        title="Plot symbols",
    )
    output_path = output_directory / "sonic-agency-by-experience.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_sonic_agency_by_background(
    observations: list[Observation],
    questionnaire_path: Path,
    output_directory: Path,
) -> Path:
    """Plot sonic-agency composites split by musical background."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    scores = _agency_scores(observations)
    backgrounds = _musical_backgrounds(questionnaire_path)
    categories = ("non-musician", "musician/enthusiast")
    groups = ("experience_1_2", "experience_3_4")
    figure, axis = plt.subplots(figsize=(9, 6))
    rng = np.random.default_rng(2027)
    offsets = {"non-musician": -0.2, "musician/enthusiast": 0.2}
    colors = {"non-musician": "#1b9e77", "musician/enthusiast": "#d95f02"}
    labels = {
        "non-musician": "Non-musician / casual listener",
        "musician/enthusiast": "Musician / enthusiast",
    }
    positions = {
        (group_index, background): group_index + offsets[background]
        for group_index in range(len(groups))
        for background in categories
    }
    plotted_values = {}
    for group_index, group in enumerate(groups):
        for background in categories:
            values = np.asarray(
                [
                    score
                    for participant, (participant_group, score) in scores.items()
                    if participant_group == group
                    and backgrounds.get(participant) == background
                ]
            )
            plotted_values[(group_index, background)] = values
            position = positions[(group_index, background)]
            axis.boxplot(
                [values],
                positions=[position],
                widths=0.3,
                patch_artist=True,
                whis=(0, 100),
                boxprops={
                    "facecolor": colors[background],
                    "edgecolor": colors[background],
                    "alpha": 0.28,
                },
                medianprops={"color": "#333333", "linewidth": 2},
                whiskerprops={"color": colors[background]},
                capprops={"color": colors[background]},
                manage_ticks=False,
            )
            x = np.full(len(values), position)
            x += rng.uniform(-0.045, 0.045, len(values))
            axis.scatter(
                x,
                values,
                color=colors[background],
                alpha=0.85,
                edgecolor="white",
                linewidth=0.7,
                s=70,
                label=labels[background] if group_index == 0 else None,
                zorder=3,
            )
    tick_labels = []
    for group_index, group in enumerate(groups):
        counts = [
            len(plotted_values[(group_index, background)])
            for background in categories
        ]
        tick_labels.append(
            f"{'Experience 1–2' if group_index == 0 else 'Experience 3–4'}\n"
            f"(n={sum(counts)})"
        )
    axis.set_xticks(range(len(groups)), tick_labels)
    axis.set_ylabel("Sonic-agency composite (0–4)")
    axis.set_title("Sonic agency by experience and musical background")
    axis.set_ylim(0, 4)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="s",
                color="none",
                markerfacecolor=colors["non-musician"],
                markeredgecolor=colors["non-musician"],
                markersize=9,
                label=labels["non-musician"],
            ),
            Line2D(
                [],
                [],
                marker="s",
                color="none",
                markerfacecolor=colors["musician/enthusiast"],
                markeredgecolor=colors["musician/enthusiast"],
                markersize=9,
                label=labels["musician/enthusiast"],
            ),
            Line2D([], [], color="#333333", linewidth=2, label="Median"),
            Line2D(
                [],
                [],
                color="#333333",
                linewidth=1.5,
                label="Minimum–maximum",
            ),
        ],
        title="Background and box symbols",
    )
    output_path = output_directory / "sonic-agency-by-background.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_agency_against_musicking(
    observations: list[Observation],
    questionnaire_path: Path,
    telemetry_path: Path,
    output_directory: Path,
) -> Path:
    """Plot participant sonic-agency scores against average musicking rate."""
    import matplotlib.pyplot as plt

    from telemetry_group_analysis import collect_telemetry

    scores = _agency_scores(observations)
    with questionnaire_path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = [
            row
            for row in csv.reader(questionnaire_file, delimiter=";")
            if any(cell.strip() for cell in row)
        ]
    study_participants = {
        f"study-p{index}": row[1].strip()
        for index, row in enumerate(rows[1:], start=1)
        if row[1].strip()
    }
    telemetry = collect_telemetry(telemetry_path, questionnaire_path)
    musicking: dict[str, list[float]] = {}
    for record in telemetry:
        participant = study_participants.get(str(record["participant"]))
        if participant is not None:
            musicking.setdefault(participant, []).append(
                float(record["musicking_per_minute"])
            )

    points = [
        (score, float(np.mean(musicking[participant])), group)
        for participant, (group, score) in scores.items()
        if participant in musicking
    ]
    figure, axis = plt.subplots(figsize=(8, 6))
    colors = {"experience_1_2": "#4c78a8", "experience_3_4": "#e45756"}
    for group in sorted({point[2] for point in points}):
        group_points = [point for point in points if point[2] == group]
        axis.scatter(
            [point[1] for point in group_points],
            [point[0] for point in group_points],
            color=colors[group],
            label=group.replace("_", " "),
            alpha=0.85,
            edgecolor="white",
            linewidth=0.7,
            s=75,
        )
    if len(points) > 1:
        correlation = float(np.corrcoef([point[1] for point in points], [point[0] for point in points])[0, 1])
        axis.text(
            0.03,
            0.97,
            f"Pearson r = {correlation:.2f}\nn = {len(points)} participants",
            transform=axis.transAxes,
            va="top",
            bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
        )
    axis.set_xlabel("Average musicking events per minute")
    axis.set_ylabel("Sonic-agency composite (0–4)")
    axis.set_title("Reported sonic agency and observed musicking")
    axis.set_ylim(0, 4)
    axis.grid(alpha=0.25)
    axis.legend(title="Experience group")
    output_path = output_directory / "sonic-agency-vs-musicking-rate.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _model_interaction_values(
    model: dict[str, object],
) -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    """Extract scenario interactions and question-level group differences."""
    coefficients = model.get("coefficients", {})
    p_values = model.get("p_values", {})
    if not isinstance(coefficients, dict) or not isinstance(p_values, dict):
        return {}, {}

    scenario_values = {}
    for scenario in ("B", "C", "D"):
        key = f"C(scenario)[T.{scenario}]:C(group)[T.experience_3_4]"
        if key in coefficients:
            scenario_values[scenario] = (
                float(coefficients[key]),
                float(p_values[key]),
            )

    group_key = "C(group)[T.experience_3_4]"
    if group_key not in coefficients:
        return scenario_values, {}
    baseline_difference = float(coefficients[group_key])
    question_values = {}
    for question in (
        "How engaging did you find the sound effects/music?",
        "How engaging did you find the gameplay/platforming?",
        "I was immersed in the game.",
        "I wanted to explore how the audio changed as I played.",
        "I felt motivated to explore the paths and areas of the game world.",
        "The audio made me adapt how I moved through the level.",
        "I enjoyed playing this scenario.",
        "I was distracted by the audio.",
    ):
        group_a_key = (
            f"C(question)[T.{question}]:C(group)[experience_1_2]"
        )
        group_b_key = (
            f"C(question)[T.{question}]:C(group)[experience_3_4]"
        )
        difference = baseline_difference
        p_value = float(p_values[group_key])
        if group_a_key in coefficients:
            difference -= float(coefficients[group_a_key])
        if group_b_key in coefficients:
            difference += float(coefficients[group_b_key])
            p_value = float(p_values[group_b_key])
        question_values[question] = (difference, p_value)
    return scenario_values, question_values


def plot_model_interactions(
    models: dict[str, object],
    output_directory: Path,
) -> Path:
    """Plot LMM/GEE scenario interactions and item-level group differences."""
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    colors = {"linear_mixed_effects": "#4c78a8", "gee": "#e45756"}
    labels = {"linear_mixed_effects": "LMM", "gee": "GEE"}
    scenario_names = ("B vs A", "C vs A", "D vs A")
    scenario_positions = np.arange(len(scenario_names))
    question_names = (
        "Sound/music",
        "Gameplay",
        "Immersion",
        "Audio exploration",
        "World exploration",
        "Movement adaptation",
        "Enjoyment",
        "Distraction",
    )
    question_positions = np.arange(len(question_names))

    for model_name, color in colors.items():
        model = models.get(model_name)
        if not isinstance(model, dict) or "coefficients" not in model:
            continue
        scenario_values, question_values = _model_interaction_values(model)
        scenario_coefficients = [
            scenario_values.get(scenario, (np.nan, np.nan))[0]
            for scenario in ("B", "C", "D")
        ]
        scenario_p_values = [
            scenario_values.get(scenario, (np.nan, np.nan))[1]
            for scenario in ("B", "C", "D")
        ]
        offset = -0.07 if model_name == "linear_mixed_effects" else 0.07
        axes[0].errorbar(
            scenario_positions + offset,
            scenario_coefficients,
            fmt="o",
            color=color,
            label=labels[model_name],
            capsize=4,
        )
        for position, coefficient, p_value in zip(
            scenario_positions + offset,
            scenario_coefficients,
            scenario_p_values,
        ):
            if np.isfinite(coefficient):
                axes[0].annotate(
                    f"p={p_value:.2f}",
                    (position, coefficient),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                    color=color,
                )

        question_coefficients = [
            question_values.get(question, (np.nan, np.nan))[0]
            for question in AGENCY_QUESTIONS
        ]
        question_labels = (
            "Audio exploration",
            "World exploration",
            "Movement adaptation",
        )
        selected_positions = np.arange(len(question_labels))
        axes[1].plot(
            selected_positions + offset,
            question_coefficients,
            "o",
            color=color,
            label=labels[model_name],
        )
        for position, coefficient in zip(
            selected_positions + offset,
            question_coefficients,
        ):
            axes[1].annotate(
                f"{coefficient:.2f}",
                (position, coefficient),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=color,
            )

    for axis in axes:
        axis.axhline(0, color="#333333", linestyle="--", linewidth=1)
        axis.grid(axis="y", alpha=0.25)
        axis.legend()
    axes[0].set_xticks(scenario_positions, scenario_names)
    axes[0].set_ylabel("Interaction coefficient")
    axes[0].set_title("Scenario × experience interaction")
    axes[0].text(
        0.02,
        0.03,
        "Values near zero indicate similar\nexperience-group differences across scenarios.",
        transform=axes[0].transAxes,
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
    )
    axes[1].set_xticks(
        np.arange(len(AGENCY_QUESTIONS)),
        ("Audio exploration", "World exploration", "Movement adaptation"),
    )
    axes[1].set_ylabel("Estimated experienced − less experienced difference")
    axes[1].set_title(
        "Estimated experience-group difference\nfor agency items"
    )
    axes[1].set_ylim(-1.5, 1.5)
    axes[1].tick_params(axis="x", rotation=25)

    output_path = output_directory / "model-interaction-effects.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_all(
    observations: list[Observation],
    questionnaire_path: Path,
    telemetry_path: Path,
    models: dict[str, object],
    output_directory: Path,
    iterations: int,
    seed: int,
) -> list[Path]:
    """Generate the bootstrap and sonic-agency figure set."""
    output_directory.mkdir(parents=True, exist_ok=True)
    return [
        *plot_bootstrap_distributions(observations, output_directory, iterations, seed),
        plot_sonic_agency(observations, output_directory),
        plot_sonic_agency_by_background(
            observations, questionnaire_path, output_directory
        ),
        plot_agency_against_musicking(
            observations, questionnaire_path, telemetry_path, output_directory
        ),
        plot_model_interactions(models, output_directory),
    ]


def _short_question_label(question: str) -> str:
    """Make questionnaire text readable as a plot title."""
    labels = {
        "How engaging did you find the sound effects/music?": "Sound/music engagement",
        "How engaging did you find the gameplay/platforming?": "Gameplay engagement",
        "I was immersed in the game.": "Immersion",
        "I wanted to explore how the audio changed as I played.": "Audio exploration",
        "I felt motivated to explore the paths and areas of the game world.": "World exploration",
        "The audio made me adapt how I moved through the level.": "Movement adaptation",
        "I enjoyed playing this scenario.": "Enjoyment",
        "I was distracted by the audio.": "Audio distraction",
    }
    return labels.get(question, question)


def _fit_statsmodels(observations: list[Observation]) -> dict[str, object]:
    """Fit LME and GEE, or return an explicit dependency message."""
    try:
        import pandas as pd
        import statsmodels.api as sm
        from statsmodels.formula.api import gee, mixedlm
    except ImportError as error:
        return {
            "status": "not_run",
            "reason": "Install statsmodels and pandas to run LME/GEE: "
            f"{error}",
        }

    frame = pd.DataFrame([observation.__dict__ for observation in observations])
    formula = (
        "rating ~ C(scenario) + C(play_position) + C(group) "
        "+ C(scenario):C(group) + C(question):C(group) "
        "+ C(play_position):C(group)"
    )
    results: dict[str, object] = {
        "status": "run",
        "formula": formula,
        "interpretation": {
            "scenario_group": (
                "Tests whether experience groups respond differently to specific scenarios."
            ),
            "question_group": (
                "Tests whether experience differences are concentrated in specific questionnaire items."
            ),
            "play_position_group": (
                "Tests whether changes across play position differ by experience group."
            ),
        },
    }
    try:
        lme = mixedlm(formula, frame, groups=frame["participant"]).fit(
            reml=False, method="lbfgs"
        )
        results["linear_mixed_effects"] = {
            "converged": bool(lme.converged),
            "coefficients": {key: float(value) for key, value in lme.params.items()},
            "p_values": {key: float(value) for key, value in lme.pvalues.items()},
            "interaction_terms": _interaction_results(lme),
        }
    except (ValueError, np.linalg.LinAlgError) as error:
        results["linear_mixed_effects"] = {"status": "failed", "reason": str(error)}

    try:
        gee_result = gee(
            formula,
            "participant",
            frame,
            cov_struct=sm.cov_struct.Exchangeable(),
            family=sm.families.Gaussian(),
        ).fit()
        results["gee"] = {
            "coefficients": {
                key: float(value) for key, value in gee_result.params.items()
            },
            "p_values": {
                key: float(value) for key, value in gee_result.pvalues.items()
            },
            "interaction_terms": _interaction_results(gee_result),
        }
    except (ValueError, np.linalg.LinAlgError) as error:
        results["gee"] = {"status": "failed", "reason": str(error)}
    return results


def _interaction_results(model: object) -> dict[str, dict[str, float]]:
    """Extract scenario/group and question/group terms for easy interpretation."""
    params = model.params
    p_values = model.pvalues
    return {
        key: {
            "coefficient": float(value),
            "p_value": float(p_values[key]),
        }
        for key, value in params.items()
        if ":C(group)" in key
    }


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


def _p_value_tables(models: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    """Build raw and Holm-adjusted tables for pre-specified interaction families."""
    families = {
        "scenario_x_experience": [
            ("Scenario B × experience", "C(scenario)[T.B]:C(group)[T.experience_3_4]"),
            ("Scenario C × experience", "C(scenario)[T.C]:C(group)[T.experience_3_4]"),
            ("Scenario D × experience", "C(scenario)[T.D]:C(group)[T.experience_3_4]"),
        ],
        "agency_question_x_experience": [
            (
                "Audio exploration × experience",
                "C(question)[T.I wanted to explore how the audio changed as I played.]:C(group)[experience_1_2]",
            ),
            (
                "World exploration × experience",
                "C(question)[T.I felt motivated to explore the paths and areas of the game world.]:C(group)[experience_1_2]",
            ),
            (
                "Movement adaptation × experience",
                "C(question)[T.The audio made me adapt how I moved through the level.]:C(group)[experience_1_2]",
            ),
        ],
        "play_position_x_experience": [
            (
                "Play position 2 × experience",
                "C(play_position)[T.2]:C(group)[T.experience_3_4]",
            ),
            (
                "Play position 3 × experience",
                "C(play_position)[T.3]:C(group)[T.experience_3_4]",
            ),
            (
                "Play position 4 × experience",
                "C(play_position)[T.4]:C(group)[T.experience_3_4]",
            ),
        ],
    }
    tables: dict[str, list[dict[str, object]]] = {}
    for family, terms in families.items():
        for model_name in ("linear_mixed_effects", "gee"):
            model = models.get(model_name)
            if not isinstance(model, dict):
                continue
            coefficients = model.get("coefficients", {})
            p_values = model.get("p_values", {})
            if not isinstance(coefficients, dict) or not isinstance(p_values, dict):
                continue
            available = [
                (label, term, float(coefficients[term]), float(p_values[term]))
                for label, term in terms
                if term in coefficients and term in p_values
            ]
            adjusted = _holm_adjust([row[3] for row in available])
            for (label, term, estimate, p_value), adjusted_p in zip(
                available, adjusted
            ):
                tables.setdefault(f"{family}_p_values", []).append(
                    {
                        "family": family,
                        "model": "LMM" if model_name == "linear_mixed_effects" else "GEE",
                        "term": label,
                        "coefficient": estimate,
                        "p_value_unadjusted": p_value,
                        "p_value_holm": adjusted_p,
                        "source_term": term,
                    }
                )
    return tables


def _write_p_value_markdown(
    tables: dict[str, list[dict[str, object]]],
    path: Path,
) -> None:
    """Write a thesis-friendly Markdown summary of interaction p-values."""
    lines = [
        "# Interaction p-value tables",
        "",
        "Unadjusted p-values are exploratory Wald tests from the fitted LMM/GEE.",
        "Holm adjustment is applied separately within each pre-specified family.",
        "",
        "## Scenario x experience",
        "",
        "| Model | Term | Coefficient | Unadjusted p | Holm-adjusted p |",
        "|---|---|---:|---:|---:|",
    ]
    for row in tables.get("scenario_x_experience_p_values", []):
        lines.append(
            f"| {row['model']} | {row['term']} | {row['coefficient']:.3f} | "
            f"{row['p_value_unadjusted']:.4g} | {row['p_value_holm']:.4g} |"
        )
    lines.extend(
        [
            "",
            "## Agency-question x experience",
            "",
            "| Model | Term | Coefficient | Unadjusted p | Holm-adjusted p |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in tables.get("agency_question_x_experience_p_values", []):
        lines.append(
            f"| {row['model']} | {row['term']} | {row['coefficient']:.3f} | "
            f"{row['p_value_unadjusted']:.4g} | {row['p_value_holm']:.4g} |"
        )
    lines.extend(
        [
            "",
            "## Play-position x experience",
            "",
            "| Model | Term | Coefficient | Unadjusted p | Holm-adjusted p |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in tables.get("play_position_x_experience_p_values", []):
        lines.append(
            f"| {row['model']} | {row['term']} | {row['coefficient']:.3f} | "
            f"{row['p_value_unadjusted']:.4g} | {row['p_value_holm']:.4g} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(
    path: Path = DEFAULT_INPUT,
    group_kind: str = "experience",
    bootstrap_iterations: int = 5000,
    seed: int = 2026,
) -> dict[str, object]:
    """Run feasibility checks, bootstrap comparisons, and optional models."""
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    observations, filtered_participants = read_observations(path, group_kind)
    participants = {observation.participant for observation in observations}
    participant_groups = {
        observation.participant: observation.group for observation in observations
    }
    groups = Counter(participant_groups.values())
    questions = list(dict.fromkeys(observation.question for observation in observations))
    complete_scenarios = sum(
        all(
            any(
                observation.participant == participant
                and observation.scenario == scenario
                for observation in observations
            )
            for scenario in SCENARIOS
        )
        for participant in participants
    )
    result: dict[str, object] = {
        "input": str(path),
        "group_kind": group_kind,
        "feasibility": {
            "filtered_participants": filtered_participants,
            "participants_with_valid_responses": len(participants),
            "observations": len(observations),
            "groups": dict(groups),
            "questions": len(questions),
            "participants_with_all_scenarios": complete_scenarios,
            "recommendation": (
                "Use participant-clustered bootstrap as the baseline. "
                "LME/GEE are reasonable exploratory sensitivity analyses; "
                "interpret p-values cautiously because the sample is small "
                "and ratings are ordinal."
            ),
        },
        "bootstrap": {},
        "models": _fit_statsmodels(observations),
    }
    result["p_value_tables"] = _p_value_tables(result["models"])
    group_names = sorted(groups)
    for question_index, question in enumerate(questions):
        if len(group_names) <= 2:
            result["bootstrap"][question] = bootstrap_group_difference(
                observations, question, bootstrap_iterations, seed + question_index
            )
        else:
            result["bootstrap"][question] = {
                f"{first} vs {second}": bootstrap_group_difference(
                    observations,
                    question,
                    bootstrap_iterations,
                    seed + question_index + pair_index,
                    (first, second),
                )
                for pair_index, (first, second) in enumerate(
                    (pair for index, first in enumerate(group_names) for pair in
                     ((first, second) for second in group_names[index + 1 :]))
                )
            }
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--group",
        choices=("experience", "participant_type"),
        default="experience",
        help="Grouping variable to compare (default: experience levels 1-2 vs 3-4).",
    )
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--p-value-table",
        type=Path,
        help="Optional Markdown path for the LMM/GEE p-value tables.",
    )
    parser.add_argument(
        "--plot-dir",
        type=Path,
        help="Save bootstrap and sonic-agency PNGs to this directory.",
    )
    args = parser.parse_args(argv)

    result = analyze(
        args.input, args.group, args.bootstrap_iterations, args.seed
    )
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    if args.p_value_table:
        _write_p_value_markdown(result["p_value_tables"], args.p_value_table)
    if args.plot_dir:
        observations, _ = read_observations(args.input, args.group)
        paths = plot_all(
            observations,
            args.input,
            args.input.parent,
            result["models"],
            args.plot_dir,
            args.bootstrap_iterations,
            args.seed,
        )
        print("Saved plots:", ", ".join(str(path) for path in paths), file=sys.stderr)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
