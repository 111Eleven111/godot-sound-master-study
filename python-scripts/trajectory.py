import matplotlib

with open("test.csv") as file:
    headers = file.readline()
    
    lines = file.readlines()
    print(lines[1])
