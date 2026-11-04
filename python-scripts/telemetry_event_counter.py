from pathlib import Path

paths = []


def count_top_reaches_by_scenario(sessions: dict) -> dict:
    """Count all top/checkpoint reaches grouped by scenario."""
    top_reaches = {scenario: 0 for scenario in "ABCD"}

    for session_name, events in sessions.items():
        scenario = session_name.rsplit("_", 1)[-1]
        if scenario not in top_reaches:
            continue

        top_reaches[scenario] += sum(
            1
            for line in events[1:]
            if line.split(",", 2)[1].strip() == "top/checkpoint reached"
        )

    return top_reaches


if __name__ == "__main__":
    """
    Find 
    """

    PATH = Path("study-data")
    folders = [path for path in PATH.iterdir() if path.is_dir()]
    
    for folder in folders:
        paths.extend([session for session in folder.iterdir() if session.is_file() and session.suffix == ".csv"])

    # print(paths)

    ex = set(["session_end", "scene_transition", "session_start", "event"])
    counter = 0

    for path in paths:
        with open(path) as file:
            for line in file.readlines():
                event = line.split(",")[1]
                if str(event) not in ex:
                    counter += 1


