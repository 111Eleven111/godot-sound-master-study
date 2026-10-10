import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


QUESTIONNAIRE_PATH = (
    Path(__file__).parent
    / "study-data"
    / "data-648517-2026-10-09-1553.txt"
)
SCENARIOS = ("A", "B", "C", "D")
SCENARIO_QUESTION_COUNT = 8
SCENARIO_QUESTION_START = 17


def read_questionnaire(path: Path = QUESTIONNAIRE_PATH) -> tuple[list[str], list[list[str]]]:
    """Read the semicolon-delimited questionnaire export."""
    with path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = list(csv.reader(questionnaire_file, delimiter=";", quotechar='"'))

    if not rows:
        raise ValueError(f"Questionnaire file is empty: {path}")
    return rows[0], rows[1:]


def _scenario_responses(
    rows: list[list[str]], headers: list[str]
) -> dict[str, dict[str, list[float]]]:
    questions = headers[
        SCENARIO_QUESTION_START:
        SCENARIO_QUESTION_START + SCENARIO_QUESTION_COUNT
    ]
    responses = {
        scenario: {question: [] for question in questions}
        for scenario in SCENARIOS
    }

    for row in rows:
        scenario_order = row[0].strip()
        if len(scenario_order) != len(SCENARIOS):
            raise ValueError(f"Invalid scenario order: {scenario_order!r}")

        for scenario_index, scenario in enumerate(scenario_order):
            start = SCENARIO_QUESTION_START + (
                scenario_index * SCENARIO_QUESTION_COUNT
            )
            for question_index, question in enumerate(questions):
                value = row[start + question_index].strip()
                if value:
                    responses[scenario][question].append(float(value))

    return responses


def _question_label(question: str) -> str:
    labels = {
        "How engaging did you find the sound effects/music?": "Sound/music engagement",
        "How engaging did you find the gameplay/platforming?": "Gameplay engagement",
        "I was immersed in the game.": "Immersion",
        "I wanted to explore how the audio changed as I played.": "Audio exploration",
        "I felt motivated to explore the paths and areas of the game world.": "World exploration",
        "The audio made me adapt how I moved through the level.": "Audio affected movement",
        "I enjoyed playing this scenario.": "Enjoyment",
        "I was distracted by the audio.": "Audio distraction",
    }
    return labels.get(question, question)


def plot_questionnaire_charts(
    path: Path = QUESTIONNAIRE_PATH,
) -> None:
    """Plot participant demographics and every scenario question."""
    headers, rows = read_questionnaire(path)
    responses = _scenario_responses(rows, headers)

    demographic_figure, demographic_axes = plt.subplots(1, 3, figsize=(15, 5))
    age_counts = Counter(row[3].strip() for row in rows if row[3].strip())
    demographic_axes[0].pie(
        age_counts.values(),
        labels=age_counts.keys(),
        autopct="%1.0f%%",
    )
    demographic_axes[0].set_title("Participant ages")

    gender_counts = Counter(
        next(
            (
                header.rsplit(".", 1)[-1]
                for header, value in zip(headers[4:8], row[4:8])
                if value.strip()
            ),
            "Unanswered",
        )
        for row in rows
    )
    demographic_axes[1].pie(
        gender_counts.values(),
        labels=gender_counts.keys(),
        autopct="%1.0f%%",
    )
    demographic_axes[1].set_title("Gender")

    musician_headers = headers[8:14]
    musician_counts = Counter(
        header.rsplit(".", 1)[-1]
        for row in rows
        for header, value in zip(musician_headers, row[8:14])
        if value.strip()
    )
    demographic_axes[2].pie(
        musician_counts.values(),
        labels=musician_counts.keys(),
        autopct="%1.0f%%",
    )
    demographic_axes[2].set_title("Musician identity")
    demographic_figure.tight_layout()

    questions = list(responses["A"])
    question_figure, question_axes = plt.subplots(2, 4, figsize=(18, 9))
    for axis, question in zip(question_axes.flat, questions):
        means = [
            np.mean(responses[scenario][question])
            if responses[scenario][question]
            else np.nan
            for scenario in SCENARIOS
        ]
        axis.bar(SCENARIOS, means)
        axis.set_title(_question_label(question))
        axis.set_ylim(0, 4.5)
        axis.set_ylabel("Mean response")
        axis.grid(axis="y", alpha=0.3)

    question_figure.suptitle(
        "Questionnaire responses by scenario (0–4 scale)", fontsize=14
    )
    question_figure.tight_layout()
    plt.show()


def main() -> None:
    plot_questionnaire_charts()


if __name__ == "__main__":
    main()
