from scipy.stats import shapiro
import matplotlib.pyplot as plt

def main():
    with open("./study-data/questionnaire-data-648517-2026-10-06-1347.txt") as file:
        file_content = file.readlines()
    
    # headers = file_content[0].split(";")
    # index = 0
    # for head in headers:
    #     print("index ",index,":", head)
    #     index += 1

    """
    index  0 : "$submission_id"
    index  1 : "$created"
    index  2 : "How old are you?"
    index  3 : "What is your gender?.Female"
    index  4 : "What is your gender?.Male"
    index  5 : "What is your gender?.Non-binary"
    index  6 : "What is your gender?.Prefer not to say"
    index  7 : "What kind of musician would you describe yourself as?.Professional musician"
    index  8 : "What kind of musician would you describe yourself as?.Semi-Professional Musician"
    index  9 : "What kind of musician would you describe yourself as?.Amateur Musician"
    index  10 : "What kind of musician would you describe yourself as?.Music Enthusiast / Active Listener"
    index  11 : "What kind of musician would you describe yourself as?.Non-Musician / Casual Listener"
    index  12 : "What kind of musician would you describe yourself as?.Other"
    index  13 : "How much prior experience do you have with platforming video-games?"
    index  14 : "Do you use any vision aid like glasses?"
    index  15 : "Do you use any hearing aids or similar tools?"
    index  16 : "How engaging did you find the sound effects/music?"
    index  17 : "How engaging did you find the gameplay/platforming?"
    index  18 : "I was immersed in the game."
    index  19 : "I wanted to explore how the audio changed as I played."
    index  20 : "I felt motivated to explore the paths and areas of the game world."
    index  21 : "The audio made me adapt how I moved through the level."
    index  22 : "I enjoyed playing this scenario."
    index  23 : "I was distracted by the audio."
    index  24 : "How engaging did you find the sound effects/music?"
    index  25 : "How engaging did you find the gameplay/platforming?"
    index  26 : "I was immersed in the game."
    index  27 : "I wanted to explore how the audio changed as I played."
    index  28 : "I felt motivated to explore the paths and areas of the game world."
    index  29 : "The audio made me adapt how I moved through the level."
    index  30 : "I enjoyed playing this scenario."
    index  31 : "I was distracted by the audio."
    index  32 : "How engaging did you find the sound effects/music?"
    index  33 : "How engaging did you find the gameplay/platforming?"
    index  34 : "I was immersed in the game."
    index  35 : "I wanted to explore how the audio changed as I played."
    index  36 : "I felt motivated to explore the paths and areas of the game world."
    index  37 : "The audio made me adapt how I moved through the level."
    index  38 : "I enjoyed playing this scenario."
    index  39 : "I was distracted by the audio."
    index  40 : "How engaging did you find the sound effects/music?"
    index  41 : "How engaging did you find the gameplay/platforming?"
    index  42 : "I was immersed in the game."
    index  43 : "I wanted to explore how the audio changed as I played."
    index  44 : "I felt motivated to explore the paths and areas of the game world."
    index  45 : "The audio made me adapt how I moved through the level."
    index  46 : "I enjoyed playing this scenario."
    index  47 : "I was distracted by the audio."
    index  48 : "How much music and interactive sound effects do you think a game like this should have?"
    index  49 : "I felt I was good at playing this game."
    index  50 : "The goals of the game were clear to me."
    index  51 : "What motivated you the most during play?"
    index  52 : "$answer_time_ms"
    """
    
    data = file_content[1:]
    data = [x.split(";") for x in data]

    females = [row[3].strip() for row in data]
    males = [row[4].strip() for row in data]
    nb = [row[5].strip() for row in data]
    prefer_not_to_say = [row[6].strip() for row in data]

    counts = [
        females.count('"Female"'),
        males.count('"Male"'),
        nb.count('"Non-binary"'),
        prefer_not_to_say.count('"Prefer not to say"')
    ]
    labels = ["Female", "Male", "Non-binary", "Prefer not to say"]

    fig, ax = plt.subplots()
    ax.pie(counts, labels=labels)
    plt.show()



    


if __name__ == "__main__":
    main()