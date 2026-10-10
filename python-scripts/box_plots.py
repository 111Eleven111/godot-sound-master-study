import os
import re
import matplotlib.pyplot as plt

def read_folder(pfolder, sessions):
    filenames = sorted(
        filename for filename in os.listdir(pfolder) if filename.endswith(".csv")
    )[:4]
    with open(os.path.join(pfolder, "notes.txt")) as file:
        session_order = next(
            (
                [scenario.strip() for scenario in line.split(";")]
                for line in file
                if re.fullmatch(r"\s*[ABCD](?:\s*;\s*[ABCD]){3}\s*", line)
            ),
            None,
        )

    if session_order is None:
        raise ValueError(f"Could not find a four-scenario order in {pfolder}/notes.txt")
    if len(filenames) != len(session_order):
        raise ValueError(
            f"Found {len(filenames)} CSV sessions but {len(session_order)} scenarios "
            f"in {pfolder}/notes.txt"
        )

    folder_sessions = {}
    for filename in filenames:
        filepath = os.path.join(pfolder, filename)
        with open(filepath) as file:
            folder_sessions[filepath] = file.readlines()

    # Sort by the timestamp in each filename, then assign one scenario per session.
    sessions.update(
        {
            f"{os.path.splitext(filepath)[0]}_{scenario}": lines
            for (filepath, lines), scenario in zip(
                sorted(folder_sessions.items()), session_order
            )
            if scenario
        }
    )
    # print("\nProcessed folder: ", pfolder)
    # print(sessions.keys())
    return sessions

def read_all(sessions):
    study_nr = 1
    study_endfix = "./study-data/study-p" + str(study_nr) + "/"

    while study_nr <= 10:
        sessions = read_folder(study_endfix, sessions)
        study_nr += 1
        study_endfix = "./study-data/study-p" + str(study_nr) + "/"

    return sessions

def count_events(events: list) -> dict:
    event_counts = {}
    x = 1

    while x < len(events):
        event = events[x].split(",")[1].strip()
        event_counts[event] = event_counts.get(event, 0) + 1
        x += 1

    return event_counts


def _session_duration_minutes(events: list) -> float:
    """Return the elapsed session time in minutes from CSV timestamps."""
    timestamps = []
    for line in events[1:]:
        try:
            timestamps.append(float(line.split(",", 1)[0]))
        except (ValueError, IndexError):
            continue

    if len(timestamps) < 2:
        raise ValueError("A session must contain at least two valid timestamps")

    duration = (max(timestamps) - min(timestamps)) / 60
    if duration <= 0:
        raise ValueError("A session must have a positive duration")
    return duration


def _sessions_by_trial_order(sessions: dict) -> list:
    """Group sessions by participant and return them in testing order."""
    participant_sessions = {}
    for session_name, events in sessions.items():
        scenario = session_name.rsplit("_", 1)[-1]
        if scenario not in "ABCD":
            continue
        # All session files for one participant are stored in the same
        # study-pN directory. The timestamp must not be part of this key.
        participant = os.path.dirname(session_name)
        participant_sessions.setdefault(participant, []).append(
            (events, scenario)
        )

    ordered_sessions = []
    for participant, participant_data in participant_sessions.items():
        ordered_sessions.append(
            (
                participant,
                sorted(
                    participant_data,
                    key=lambda session: float(session[0][1].split(",", 1)[0]),
                ),
            )
        )
    return ordered_sessions


def plot_event_occurrences(sessions: dict, event: str) -> None:
    scenario_occurrences = {scenario: [] for scenario in "ABCD"}

    for session_name, events in sessions.items():
        scenario = session_name.rsplit("_", 1)[-1]
        if scenario in scenario_occurrences:
            scenario_occurrences[scenario].append(
                count_events(events).get(event, 0)
            )

    plt.boxplot(
        [scenario_occurrences[scenario] for scenario in "ABCD"],
        tick_labels=["A","B","C","D"],
        showmeans=True,
        showfliers=True
    )
    plt.xlabel("Scenario")
    plt.ylabel("amount of " + event + " event occurrences")
    plt.title(event + " event occurrence variance across all studies")
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_event_occurrances_counterbalance(sessions: dict, event: str) -> None:
    """
    Plot event occurrences for each scenario, excluding each participant's
    first session to reduce learning effects.

    The first session is identified by its timestamp, not by its scenario.
    """
    scenario_occurrences = {scenario: [] for scenario in "ABCD"}

    for _, participant_sessions in _sessions_by_trial_order(sessions):
        # Drop the participant's first trial, then retain all later scenarios.
        for events, scenario in participant_sessions[1:]:
            scenario_occurrences[scenario].append(count_events(events).get(event, 0))

    plt.boxplot(
        [scenario_occurrences[scenario] for scenario in "ABCD"],
        tick_labels=["A", "B", "C", "D"],
        showmeans=True,
        showfliers=True,
    )
    plt.xlabel("Scenario")
    plt.ylabel("amount of " + event + " event occurrences")
    plt.title(event + " event occurrences excluding first session")
    plt.tight_layout()
    plt.show()


def plot_event_occurrances_normalized(sessions: dict) -> None:
    """
    Plot movement and jump input events per minute.

    Movement is the combined count of left- and right-movement inputs.
    """
    normalized_events = {
        "movement events": {scenario: [] for scenario in "ABCD"},
        "jump inputs": {scenario: [] for scenario in "ABCD"},
    }

    for session_name, events in sessions.items():
        scenario = session_name.rsplit("_", 1)[-1]
        if scenario not in normalized_events["movement events"]:
            continue

        duration = _session_duration_minutes(events)
        event_counts = count_events(events)
        normalized_events["movement events"][scenario].append(
            (
                event_counts.get("move_left_pressed", 0)
                + event_counts.get("move_right_pressed", 0)
            )
            / duration
        )
        normalized_events["jump inputs"][scenario].append(
            event_counts.get("jump_input_pressed", 0) / duration
        )

    figure, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    for axis, event_type in zip(axes, ("movement events", "jump inputs")):
        axis.boxplot(
            [normalized_events[event_type][scenario] for scenario in "ABCD"],
            tick_labels=["A", "B", "C", "D"],
            showmeans=True,
            showfliers=True,
        )
        axis.set_xlabel("Scenario")
        axis.set_title(event_type.capitalize())

    axes[0].set_ylabel("events per minute")
    figure.suptitle("Normalized movement and jump input rates")
    plt.tight_layout()
    plt.show()


# Correctly-spelled aliases for the public functions above.
plot_event_occurrences_counterbalance = plot_event_occurrances_counterbalance
plot_event_occurrences_normalized = plot_event_occurrances_normalized

def get_event_legend(sessions: dict) -> set:
    """
    {'session_start': 1, 'jump_peak_reached': 88, 'platform_landed': 99, 'landed': 99,'move_left_pressed': 73, 'move_right_pressed': 79, 'musicking': 4, 'jump_input_pressed': 89, 'jump_executed': 87, 'jump_input_released': 89, 'coin_collected': 14, 'sonification': 32, 'top/checkpoint reached': 1, 'scene_transition': 1, 'session_end': 1}
    """
    unique_events = set()

    for value in sessions.values():
        for line in value:
            unique_events.add(line.split(',')[1])

    return unique_events

    # print(sessions['./study-data/study-p1/session_2026-09-29T11-54-49_B'][2].split(",")[1])

def main() -> None:
    sessions = {}
    sessions = read_all(sessions)

    # assert that ./study-data/study-p3/session_2026-09-29T17-39-19 has become ./study-data/study-p3/session_2026-09-29T17-39-19_A because first scenario that was performed for sudy python-scripts/study-data/study-p3/notes.txt was A

    # plot_event_occurrences(sessions, "sonification")
    # print(get_event_legend(sessions))
    # event_legend:
    """
    {'jump_executed', 'jump_input_released', 'sonification', 'scene_transition',
    'top/checkpoint reached', 'platform_landed', 'musicking', 'move_right_pressed',
    'move_left_pressed', 'jump_peak_reached', 'session_end', 'coin_collected', 'landed',
    'jump_input_pressed', 'session_start', 'event', 'time_limit_reached'}
    """

    # for event in get_event_legend(sessions):
    #     plot_event_occurrences(sessions, event)

    for event in get_event_legend(sessions):
        plot_event_occurrences_counterbalance(sessions, event)

    # plot_event_occurrences(sessions, "sonification"

if __name__ == "__main__":
    main()