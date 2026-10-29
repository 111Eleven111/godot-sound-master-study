orders = []
data_lines = []
path = "study-p"
x = 1
AMOUNT_OF_STUDIES = 18
QUESTIONNAIRE_DATA_PATH = "data-648517-2026-10-19-2100.txt"

# Read study orders
while x <= AMOUNT_OF_STUDIES:
    with open(path + str(x) + "/notes.txt") as file:
        file.readline()
        orders.append(file.readline().strip())

    x += 1

# Copy questionnaire data:
with open("data-648517-2026-10-19-2100.txt") as file:
    data_lines = file.readlines()

# Write study orders to files
with open("test.txt", "w") as file:
    i = -1

    for line in data_lines:
        if i == -1:
            file.write("order;" + line)

            i += 1
            continue

        line = "\"" + str(orders[i]).replace(";", "") + "\"" + ";" + line + "\n"
        file.write(line)

        i += 1
