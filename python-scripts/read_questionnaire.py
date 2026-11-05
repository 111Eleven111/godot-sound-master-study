import csv
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

DEBUG = True 
QUESTIONNAIRE_PATH = (
    Path(__file__).parent
    / "study-data"
    / "data-with-order.txt"
)
SCENARIOS = ("A", "B", "C", "D")
SCENARIO_QUESTION_COUNT = 8
SCENARIO_QUESTION_START = 17
PARTICIPANT_TYPE_COLUMNS = {
    "professional": "Professional musician",
    "semi-professional": "Semi-Professional Musician",
    "amateur": "Amateur Musician",
    "music enthusiast": "Music Enthusiast / Active Listener",
    "non-musician": "Non-Musician / Casual Listener",
    "other": "Other",
}


def read_questionnaire(path: Path = QUESTIONNAIRE_PATH) -> tuple[list[str], list[list[str]]]:
    """Read the semicolon-delimited questionnaire export."""
    with path.open(newline="", encoding="utf-8-sig") as questionnaire_file:
        rows = [
            row
            for row in csv.reader(questionnaire_file, delimiter=";", quotechar='"')
            if any(cell.strip() for cell in row)
        ]

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

    if DEBUG:
        print("TEST: ")
        print(rows)

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


def _participant_type_rows(
    rows: list[list[str]], participant_type: str
) -> list[list[str]]:
    """Return rows matching a participant type from the questionnaire."""
    normalized_type = participant_type.strip().casefold()
    if normalized_type == "all":
        return rows

    participant_label = PARTICIPANT_TYPE_COLUMNS.get(normalized_type)
    if participant_label is None:
        participant_label = next(
            (
                label
                for label in PARTICIPANT_TYPE_COLUMNS.values()
                if label.casefold() == normalized_type
            ),
            None,
        )
    if participant_label is None:
        valid_types = ", ".join(["all", *PARTICIPANT_TYPE_COLUMNS])
        raise ValueError(
            f"Unknown participant type {participant_type!r}. "
            f"Choose one of: {valid_types}."
        )

    return [
        row
        for row in rows
        if any(
            cell.strip().casefold() == participant_label.casefold()
            for cell in row[8:14]
        )
    ]


def _plot_questionnaire_responses(
    responses: dict[str, dict[str, list[float]]],
    title: str,
) -> None:
    """Plot mean responses for each scenario and questionnaire question."""
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

    question_figure.suptitle(title, fontsize=14)
    question_figure.tight_layout()
    plt.show()


def plot_questionnaire_charts_participant_type(
    participant_type: str,
    path: Path = QUESTIONNAIRE_PATH,
) -> None:
    """Plot scenario-question responses for one participant type.

    ``participant_type`` can be ``all``, ``professional``, ``semi-professional``,
    ``amateur``, ``music enthusiast``, ``non-musician``, or ``other``.
    """
    headers, rows = read_questionnaire(path)
    filtered_rows = _participant_type_rows(rows, participant_type)
    if not filtered_rows:
        raise ValueError(
            f"No questionnaire responses found for participant type "
            f"{participant_type!r}."
        )

    responses = _scenario_responses(filtered_rows, headers)
    _plot_questionnaire_responses(
        responses,
        f"Questionnaire responses for {participant_type} participants "
        "(0–4 scale)",
    )


def run_shapiro_wilk_tests(
    participant_type: str = "all",
    path: Path = QUESTIONNAIRE_PATH,
    alpha: float = 0.05,
) -> dict[str, dict[str, dict[str, float | int | bool | None]]]:
    """Run Shapiro-Wilk normality tests for every scenario/question combination.

    The returned values contain ``n``, ``statistic``, ``p_value``, and
    ``is_normal``. ``is_normal`` is ``None`` when fewer than three responses
    are available, because the Shapiro-Wilk test cannot be run.
    """
    try:
        from scipy.stats import shapiro
    except ImportError as error:
        raise RuntimeError(
            "The Shapiro-Wilk test requires a working SciPy installation."
        ) from error

    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha!r}")

    headers, rows = read_questionnaire(path)
    filtered_rows = _participant_type_rows(rows, participant_type)
    if not filtered_rows:
        raise ValueError(
            f"No questionnaire responses found for participant type "
            f"{participant_type!r}."
        )

    responses = _scenario_responses(filtered_rows, headers)
    results: dict[str, dict[str, dict[str, float | int | bool | None]]] = {}

    print(f"Shapiro-Wilk normality tests for participant type: {participant_type}")
    print(f"Null hypothesis: responses are normally distributed (alpha={alpha})")
    for scenario in SCENARIOS:
        results[scenario] = {}
        for question, values in responses[scenario].items():
            sample_size = len(values)
            if sample_size < 3:
                result = {
                    "n": sample_size,
                    "statistic": None,
                    "p_value": None,
                    "is_normal": None,
                }
                print(
                    f"{scenario} - {_question_label(question)}: "
                    f"n={sample_size}, test not available (need at least 3)"
                )
            else:
                statistic, p_value = shapiro(values)
                result = {
                    "n": sample_size,
                    "statistic": float(statistic),
                    "p_value": float(p_value),
                    "is_normal": bool(p_value >= alpha),
                }
                interpretation = (
                    "consistent with normality"
                    if result["is_normal"]
                    else "evidence against normality"
                )
                print(
                    f"{scenario} - {_question_label(question)}: "
                    f"n={sample_size}, W={statistic:.4f}, "
                    f"p={p_value:.4f} ({interpretation})"
                )
            results[scenario][question] = result

    return results


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

    _plot_questionnaire_responses(
        responses,
        "Questionnaire responses by scenario (0–4 scale)",
    )

def regression():
    """
    Look at quetionere answers in:
     /home/bagus/uioAndCode/master/godot-sound-master-study/python-scripts/study-data/data-with-order.txt
       and store 
    """
    print(read_questionnaire(QUESTIONNAIRE_PATH))
    

def main() -> None:
    regression()
    # plot_questionnaire_charts()
    # plot_questionnaire_charts_participant_type(participant_type="music enthusiast")
    # print(run_shapiro_wilk_tests())



if __name__ == "__main__":
    main()
