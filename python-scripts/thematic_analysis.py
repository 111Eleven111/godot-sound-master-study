def main():
    with open("study-data/data-with-order.txt") as file:
        for line in file:
            
            if len(line) > 3:
                print("\n")
                print(line.split(";")[-2])

if __name__ == "__main__":
    main()