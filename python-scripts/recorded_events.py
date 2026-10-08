import os

def read_folder(pfolder):
    filenames = sorted(
        filename for filename in os.listdir(pfolder) if filename.endswith(".csv")
    )[:4]
    sessions = {}
    session_order = []

    with open("./study-data/study-p1/notes.txt") as file:
        file.readline()
        session_order = file.readline().split(";")


    for filename in filenames:
        filepath = os.path.join(pfolder, filename)
        with open(filepath) as file:
            sessions[filepath] = file.readlines()

    # Sort by the timestamp in each filename, then assign one scenario per session.
    sessions = {
        f"{filepath}_{session_order[index].strip()}": lines
        for index, (filepath, lines) in enumerate(sorted(sessions.items()))
    }
    print("\nProcessed folder: ", pfolder)
    print(sessions.keys())
    return sessions

def read_all():
    study_nr = 1
    study_endfix = "./study-data/study-p" + str(study_nr) + "/"

    while study_nr <= 10:
        read_folder(study_endfix)
        study_nr += 1
        study_endfix = "./study-data/study-p" + str(study_nr) + "/"


def main() -> None:
    read_all()
    

if __name__ == "__main__":
    main()