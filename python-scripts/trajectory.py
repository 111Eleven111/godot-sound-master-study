# imports

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

TRAJECTORY_EVENTS = {"jump_executed", "jump_peak_reached", "landed"}

def plot_arch():
    # sources: 
    # https://sqlpey.com/python/how-to-adjust-y-axis-range-to-start-from-0-in-matplotlib/
    # https://www.geeksforgeeks.org/machine-learning/how-to-plot-a-smooth-curve-in-matplotlib/

    f, ax = plt.subplots()  # Create a figure and an axes
    xdata = [1, 4, 8]       # X-axis data points
    ydata = [10, 20, 10]    # Y-axis data points
    spline = make_interp_spline(xdata, ydata, k=2)
    x_smooth = np.linspace(xdata[0], xdata[-1], 100)
    ax.plot(x_smooth, spline(x_smooth))
    ax.scatter(xdata, ydata)
    # plt.show()              # Display the figure
    


def read_jump_points(csv) -> list:
    with open(csv, "r") as file:
        header = file.readline()
        # print(header) # timestamp_seconds,event,x,y,velocity_x,velocity_y,action,info

        lines = file.readlines()
        print(lines[0])
        data = []

        for line in lines:
            if line[1] in TRAJECTORY_EVENTS:
                data.append(line)
                

    return []


def main() -> None:
    read_jump_points("test.csv")
    plot_arch()
    


if __name__ == "__main__":
    main()
    