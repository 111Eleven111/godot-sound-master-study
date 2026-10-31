from pathlib import Path

paths = []

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

    print(counter)
