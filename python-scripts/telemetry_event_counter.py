import glob


if __name__ == "__main__":
    PATH = "study-data/session*"

    for file_path in glob.glob(PATH):
        with open(file_path, "r") as file:
            for line in file:
                print(line.split(",")[1])