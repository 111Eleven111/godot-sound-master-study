import os
import matplotlib.pyplot as plt

def read_folder(pfolder, sessions):
    filenames = sorted(
        filename for filename in os.listdir(pfolder) if filename.endswith(".csv")
    )[:4]
    with open(os.path.join(pfolder, "notes.txt")) as file:
        file.readline()
        session_order = [scenario.strip() for scenario in file.readline().split(";")]

    folder_sessions = {}
    for filename in filenames:
        filepath = os.path.join(pfolder, filename)
        with open(filepath) as file:
            folder_sessions[filepath] = file.readlines()

    # Sort by the timestamp in each filename, then assign one scenario per session.
    sessions.update(
        {
            f"{filepath}_{scenario}": lines
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
    )
    plt.xlabel("Scenario")
    plt.ylabel("Event occurrences per session")
    plt.title("Event occurrence variance across studies")
    plt.tight_layout()
    plt.show()



def main() -> None:
    sessions = {}
    sessions = read_all(sessions)
    """
    {'session_start': 1, 'jump_peak_reached': 88, 'platform_landed': 99, 'landed': 99,'move_left_pressed': 73, 'move_right_pressed': 79, 'musicking': 4, 'jump_input_pressed': 89, 'jump_executed': 87, 'jump_input_released': 89, 'coin_collected': 14, 'sonification': 32, 'top/checkpoint reached': 1, 'scene_transition': 1, 'session_end': 1}
    """
    plot_event_occurrences(sessions, "sonification")

if __name__ == "__main__":
    main()