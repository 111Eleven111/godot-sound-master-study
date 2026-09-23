import matplotlib
from trajectory import read_points

# ALL_EVENTS = ["musicking", "jump_executed", "jump_peak_reached", "landed"]
EVENTS = ["musicking"]

# /study-data/pilot-study-p1/p1-s1session_2026-09-09T14-23-14.csv
# /Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p1/p1-s1session_2026-09-09T14-23-14.csv

def main() -> None:
    participant1_musicking_scenario2 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p1/p1-s2-session_2026-09-09T14-14-17.csv", EVENTS)
    participant1_musicking_scenario1 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p1/p1-s1session_2026-09-09T14-23-14.csv", EVENTS)
    participant1_musicking_scenario3 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p1/p1-s3session_2026-09-09T14-18-12.csv", EVENTS)
    participant1_musicking_scenario4 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p1/p1-s4session_2026-09-09T14-20-46.csv", EVENTS)

    participant2_musicking_scenario1 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p2/p2-s1-session_2026-09-10T11-25-29.csv", EVENTS)
    participant2_musicking_scenario2 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p2/p2-s2-session_2026-09-10T11-15-47.csv", EVENTS)
    participant2_musicking_scenario3 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p2/p2-s3-session_2026-09-10T11-18-13.csv", EVENTS)
    participant2_musicking_scenario4 = read_points("/Users/bagusandreaarvak/uioAndCode/master/repos/master-repo/godot-sound-master-study/python-scripts/study-data/pilot-study-p2/p2-s4-session_2026-09-10T10-58-04.csv", EVENTS)


if __name__ == "__main__":
    main()