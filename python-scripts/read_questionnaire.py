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
GENDER_COLUMNS = {
    "female": "Female",
    "male": "Male",
    "non-binary": "Non-binary",
    "prefer not to say": "Prefer not to say",
}
EXPERIENCE_COLUMN = 14


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


def _gender_rows(
    rows: list[list[str]], headers: list[str], gender: str
) -> list[list[str]]:
    """Return rows matching a gender from the questionnaire."""
    normalized_gender = gender.strip().casefold()
    if normalized_gender == "all":
        return rows

    gender_label = GENDER_COLUMNS.get(normalized_gender)
    if gender_label is None:
        gender_label = next(
            (
                header.rsplit(".", 1)[-1]
                for header in headers[4:8]
                if header.rsplit(".", 1)[-1].casefold() == normalized_gender
            ),
            None,
        )
    if gender_label is None:
        valid_genders = ", ".join(["all", *GENDER_COLUMNS.values()])
        raise ValueError(
            f"Unknown gender {gender!r}. Choose one of: {valid_genders}."
        )

    return [
        row
        for row in rows
        if any(
            cell.strip().casefold() == gender_label.casefold()
            for cell in row[4:8]
        )
    ]


def _experience_rows(
    rows: list[list[str]], experience_levels: set[float]
) -> list[list[str]]:
    """Return rows matching numeric platforming-game experience levels."""
    matching_rows = []
    for row in rows:
        try:
            experience_level = float(row[EXPERIENCE_COLUMN].strip())
        except (IndexError, ValueError) as error:
            value = (
                row[EXPERIENCE_COLUMN]
                if len(row) > EXPERIENCE_COLUMN
                else "<missing>"
            )
            raise ValueError(
                "Invalid platforming-game experience level in questionnaire "
                f"row: {value!r}"
            ) from error
        if experience_level in experience_levels:
            matching_rows.append(row)
    return matching_rows


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


def regression(
    path: Path = QUESTIONNAIRE_PATH,
    filter_for: (
        str
        | list[str]
        | tuple[str | list[str] | tuple[str, ...], ...]
        | None
    ) = None,
    filter_for_age_groups: list[list[int | float]] | None = None,
    filter_for_genders: (
        str
        | list[str]
        | tuple[str | list[str] | tuple[str, ...], ...]
        | None
    ) = None,
    filter_for_experience_levels: list[list[int | float]] | None = None,
    plots_per_figure: int = 4,
) -> dict[str, dict[str, list[float | None]]]:
    """Regress and plot mean questionnaire responses against play order.

    The scenario sequence in the first column determines the play position,
    while the scenario identity is intentionally ignored.

    A list of participant types is treated as one combined group. To compare
    combined groups, pass an outer tuple or list, for example::

        filter_for=(
            ["Semi-Professional Musician", "Amateur Musician"],
            "Non-Musician / Casual Listener",
        )

    ``None`` includes all participants.

    ``filter_for_age_groups`` can compare age groups instead of participant
    types. Each inner list defines one combined age group, for example::

        filter_for_age_groups=[[23, 24, 25], [26, 27, 28]]

    ``filter_for`` and ``filter_for_age_groups`` cannot be used together.

    ``filter_for_genders`` filters on gender instead of participant type. A
    tuple of gender names creates separate comparison groups, for example
    ``filter_for_genders=("Female", "Male")``. A list of gender names combines
    them into one group, for example
    ``filter_for_genders=["Female", "Non-binary"]``.

    ``filter_for_experience_levels`` compares groups of numeric answers to the
    platforming-game experience question. For example,
    ``filter_for_experience_levels=[[2], [3, 4]]`` compares level 2 with
    levels 3 and 4 combined.

    Combine ``filter_for_experience_levels`` with ``filter_for`` to compare
    participant types within an experience group. For example, use
    ``filter_for_experience_levels=[[3, 4]]`` together with
    ``filter_for=("Non-Musician / Casual Listener", [
    "Semi-Professional Musician", "Amateur Musician",
    "Music Enthusiast / Active Listener"])``.

    Only one of the age, gender, or experience filters can be used at a time.

    ``plots_per_figure`` controls how many questionnaire plots are shown in
    each figure. It defaults to 4 and must be a positive integer.

    filter options:
    "Professional musician",
    "Semi-Professional Musician",
    "Amateur Musician",
    "Music Enthusiast / Active Listener",
    "Non-Musician / Casual Listener",
    "Other"
    """
    headers, rows = read_questionnaire(path)
    if not isinstance(plots_per_figure, int) or isinstance(
        plots_per_figure, bool
    ) or plots_per_figure < 1:
        raise ValueError(
            "plots_per_figure must be a positive integer"
        )

    questions = headers[
        SCENARIO_QUESTION_START:
        SCENARIO_QUESTION_START + SCENARIO_QUESTION_COUNT
    ]
    if filter_for is not None and filter_for_age_groups is not None:
        raise ValueError(
            "Use either filter_for or filter_for_age_groups, not both"
        )
    demographic_filters = sum(
        filter_value is not None
        for filter_value in (
            filter_for_age_groups,
            filter_for_genders,
        )
    )
    if demographic_filters > 1:
        raise ValueError(
            "Use only one of filter_for_age_groups or filter_for_genders"
        )

    experience_rows = rows
    if filter_for_experience_levels is not None and filter_for is not None:
        if len(filter_for_experience_levels) != 1:
            raise ValueError(
                "When comparing participant types, "
                "filter_for_experience_levels must contain exactly one group"
            )
        experience_group = filter_for_experience_levels[0]
        if not experience_group:
            raise ValueError(
                "Each experience group must contain at least one level"
            )
        experience_rows = _experience_rows(
            rows, {float(level) for level in experience_group}
        )

    if filter_for_age_groups is not None:
        if not filter_for_age_groups:
            raise ValueError(
                "filter_for_age_groups must contain at least one age group"
            )
        filters = []
        for age_group in filter_for_age_groups:
            if not age_group:
                raise ValueError(
                    "Each age group must contain at least one age"
                )
            ages = {float(age) for age in age_group}
            age_label = f"Age {min(ages):g}-{max(ages):g}"
            group_rows = []
            for row in rows:
                try:
                    participant_age = float(row[3].strip())
                except (IndexError, ValueError) as error:
                    raise ValueError(
                        f"Invalid participant age in questionnaire row: {row[3]!r}"
                    ) from error
                if participant_age in ages:
                    group_rows.append(row)
            filters.append((age_label, group_rows))
    elif filter_for_experience_levels is not None and filter_for is None:
        if not filter_for_experience_levels:
            raise ValueError(
                "filter_for_experience_levels must contain at least one group"
            )
        filters = []
        for experience_group in filter_for_experience_levels:
            if not experience_group:
                raise ValueError(
                    "Each experience group must contain at least one level"
                )
            levels = {float(level) for level in experience_group}
            experience_label = (
                f"Experience {min(levels):g}-{max(levels):g}"
                if len(levels) > 1
                else f"Experience {next(iter(levels)):g}"
            )
            filters.append(
                (experience_label, _experience_rows(rows, levels))
            )
    elif filter_for_genders is not None:
        if isinstance(filter_for_genders, str):
            filters = [
                (filter_for_genders, _gender_rows(rows, headers, filter_for_genders))
            ]
        elif isinstance(filter_for_genders, tuple) and all(
            isinstance(gender, str) for gender in filter_for_genders
        ):
            filters = [
                (gender, _gender_rows(rows, headers, gender))
                for gender in filter_for_genders
            ]
        elif all(isinstance(gender, str) for gender in filter_for_genders):
            gender_options = [
                gender
                for gender in filter_for_genders
                if isinstance(gender, str)
            ]
            filters = [
                (
                    " + ".join(gender_options),
                    [
                        row
                        for gender in gender_options
                        for row in _gender_rows(rows, headers, gender)
                    ],
                )
            ]
        else:
            filters = []
            for gender_group in filter_for_genders:
                group_options = (
                    [gender_group]
                    if isinstance(gender_group, str)
                    else list(gender_group)
                )
                if not group_options:
                    raise ValueError(
                        "Each gender group must contain at least one gender"
                    )
                group_rows = [
                    row
                    for gender in group_options
                    for row in _gender_rows(rows, headers, gender)
                ]
                filters.append((" + ".join(group_options), group_rows))
    elif filter_for is None:
        filters = [("All participants", rows)]
    elif isinstance(filter_for, str):
        filters = [
            (filter_for, _participant_type_rows(experience_rows, filter_for))
        ]
    elif all(isinstance(participant_type, str) for participant_type in filter_for):
        filters = [
            (
                " + ".join(filter_for),
                [
                    row
                    for participant_type in filter_for
                    for row in _participant_type_rows(
                        experience_rows, participant_type
                    )
                ],
            )
        ]
    else:
        filters = []
        for participant_group in filter_for:
            group_options = (
                [participant_group]
                if isinstance(participant_group, str)
                else list(participant_group)
            )
            if not group_options:
                raise ValueError(
                    "Each filter group must contain at least one participant type"
                )
            group_rows = [
                row
                for participant_type in group_options
                for row in _participant_type_rows(
                    experience_rows, participant_type
                )
            ]
            filters.append((" + ".join(group_options), group_rows))

    if not filters:
        raise ValueError("filter_for must contain at least one participant type")

    averages_by_group: dict[str, dict[str, list[float | None]]] = {}
    for group_name, group_rows in filters:
        responses_by_position = {
            position: {question: [] for question in questions}
            for position in range(len(SCENARIOS))
        }

        for row in group_rows:
            scenario_order = row[0].strip()
            if len(scenario_order) != len(SCENARIOS):
                raise ValueError(f"Invalid scenario order: {scenario_order!r}")

            for position in range(len(SCENARIOS)):
                start = SCENARIO_QUESTION_START + (
                    position * SCENARIO_QUESTION_COUNT
                )
                for question_index, question in enumerate(questions):
                    value = row[start + question_index].strip()
                    if value:
                        responses_by_position[position][question].append(
                            float(value)
                        )

        averages_by_group[group_name] = {
            question: [
                float(np.mean(responses_by_position[position][question]))
                if responses_by_position[position][question]
                else None
                for position in range(len(SCENARIOS))
            ]
            for question in questions
        }

    play_positions = np.arange(1, len(SCENARIOS) + 1)
    print("Questionnaire response averages and regressions by play order:")
    questions_per_figure = plots_per_figure
    for figure_index, question_start in enumerate(
        range(0, len(questions), questions_per_figure), start=1
    ):
        question_batch = questions[
            question_start : question_start + questions_per_figure
        ]
        columns = min(2, len(question_batch))
        rows_per_figure = (len(question_batch) + 1) // 2
        question_figure, question_axes = plt.subplots(
            rows_per_figure,
            columns,
            figsize=(6 * columns, 4.5 * rows_per_figure),
            squeeze=False,
        )

        for question_index, question in enumerate(question_batch):
            axis = question_axes.flat[question_index]
            axis.set_title(_question_label(question))
            axis.set_xlabel("Play order")
            axis.set_ylabel("Mean response")
            axis.set_xlim(0.5, len(SCENARIOS) + 0.5)
            axis.set_ylim(0, 4.5)
            axis.set_xticks(play_positions)
            axis.grid(axis="y", alpha=0.3)

            for group_index, (group_name, group_averages) in enumerate(
                averages_by_group.items()
            ):
                question_averages = group_averages[question]
                formatted_averages = ", ".join(
                    f"play {position + 1}={average:.3f}"
                    if average is not None
                    else f"play {position + 1}=n/a"
                    for position, average in enumerate(question_averages)
                )
                valid_points = [
                    (position, average)
                    for position, average in zip(play_positions, question_averages)
                    if average is not None
                ]
                color = f"C{group_index}"

                if len(valid_points) >= 2:
                    x_values = np.array([point[0] for point in valid_points])
                    y_values = np.array([point[1] for point in valid_points])
                    slope, intercept = np.polyfit(x_values, y_values, 1)
                    predicted_values = slope * x_values + intercept
                    residual_sum_squares = np.sum(
                        (y_values - predicted_values) ** 2
                    )
                    total_sum_squares = np.sum(
                        (y_values - np.mean(y_values)) ** 2
                    )
                    r_squared = (
                        1 - residual_sum_squares / total_sum_squares
                        if total_sum_squares
                        else 1.0
                    )
                    line_x = np.linspace(x_values.min(), x_values.max(), 100)
                    axis.plot(
                        line_x,
                        slope * line_x + intercept,
                        color=color,
                        label=f"{group_name} (R²={r_squared:.3f})",
                    )
                    print(
                        f"{group_name} - {_question_label(question)}: "
                        f"{formatted_averages}; slope={slope:.3f}, "
                        f"R²={r_squared:.3f}"
                    )
                else:
                    print(
                        f"{group_name} - {_question_label(question)}: "
                        f"{formatted_averages}; regression unavailable "
                        "(need at least two averages)"
                    )

                axis.scatter(
                    play_positions,
                    [
                        average if average is not None else np.nan
                        for average in question_averages
                    ],
                    color=color,
                    marker="o",
                )
            axis.legend()

        for axis in question_axes.flat[len(question_batch):]:
            axis.set_visible(False)

        question_figure.suptitle(
            "Questionnaire response trends by scenario play order "
            f"(questions {question_start + 1}-{question_start + len(question_batch)} "
            "of 8; 0–4 scale)"
        )
        question_figure.tight_layout()
        plt.show()

    return averages_by_group

def count_participants(
    age_group: list[int | float] | tuple[int | float, ...],
    path: Path = QUESTIONNAIRE_PATH,
) -> int:
    """Count participants whose age is included in ``age_group``."""
    if not age_group:
        raise ValueError("age_group must contain at least one age")

    ages = {float(age) for age in age_group}
    _, rows = read_questionnaire(path)
    participant_count = 0

    for row in rows:
        try:
            participant_age = float(row[3].strip())
        except (IndexError, ValueError) as error:
            raise ValueError(
                f"Invalid participant age in questionnaire row: {row[3]!r}"
            ) from error
        if participant_age in ages:
            participant_count += 1

    return participant_count


def main() -> None:
    # regression(
    #     filter_for=(
    #         "Non-Musician / Casual Listener",
    #         ["Semi-Professional Musician", "Amateur Musician", "Music Enthusiast / Active Listener"]
    #     ),
    # )

    # print(count_participants(age_group=[31,32,33,35,44]))

    # regression(
    #     filter_for_age_groups=
    #         [[20,21,22,23,24,25,26,27],[31,32,33,35,44]]
    # )

    # regression(filter_for_genders=("Female", "Male"))
    # regression(filter_for_experience_levels=[[1,2], [3, 4]])

    regression(
    filter_for_experience_levels=[[3, 4]],
    filter_for=(
        [
            "Non-Musician / Casual Listener", 
            "Music Enthusiast / Active Listener"],
        [
            "Semi-Professional Musician",
            "Amateur Musician",
        ],
    ),
    plots_per_figure=1
)

    # plot_questionnaire_charts()
    # plot_questionnaire_charts_participant_type(participant_type="music enthusiast")
    # print(run_shapiro_wilk_tests())



if __name__ == "__main__":
    main()
