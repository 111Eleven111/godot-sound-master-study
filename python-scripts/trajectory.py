# imports

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline

TRAJECTORY_EVENTS = {"jump_executed", "jump_peak_reached", "landed"}
test = False

def plot_arch(xdata_param, ydata_param):
    # sources: 
    # https://sqlpey.com/python/how-to-adjust-y-axis-range-to-start-from-0-in-matplotlib/
    # https://www.geeksforgeeks.org/machine-learning/how-to-plot-a-smooth-curve-in-matplotlib/

    f, ax = plt.subplots()  # Create a figure and an axes
    xdata = np.asarray(xdata_param, dtype=float)
    ydata = np.asarray(ydata_param, dtype=float)

    if len(xdata) != len(ydata):
        raise ValueError("xdata and ydata must have the same length")
    if len(xdata) < 3:
        raise ValueError("At least three points are needed for a quadratic spline")

    # Use point order as the independent variable so duplicate x or y values are valid.
    t = np.arange(len(xdata), dtype=float)
    t_smooth = np.linspace(t[0], t[-1], 100)
    x_smooth = make_interp_spline(t, xdata, k=2)(t_smooth)
    y_smooth = make_interp_spline(t, ydata, k=2)(t_smooth)

    ax.plot(x_smooth, y_smooth)
    # ax.scatter(xdata, ydata)
    ax.invert_yaxis()
    plt.show()              # Display the figure
    


def read_jump_points(csv) -> list:
    with open(csv, "r") as file:
        header = file.readline()
        # print(header) # timestamp_seconds,event,x,y,velocity_x,velocity_y,action,info

        lines = file.readlines()
        data = []

        for line in lines:
            entry = line.split(",")
            if entry[1] in TRAJECTORY_EVENTS:
                data.append(entry)

        data = _filter_jumps(data)
    return data
    
def _filter_jumps(jumps: list) -> list:
    if test:
        print("TEST before _filter_jumps: ", jumps)

    x = 0
    order = ["jump_executed", "jump_peak_reached", "landed"]
    o = 0

    while x < len(jumps):
        # print(jumps[x][1], " ", o, " ", x)
        if jumps[x][1] != order[o]:
            jumps.pop(x)
            o = 0
            continue

        o += 1
        x += 1

        if o >= 3:
            o = 0

    if test:
            print("TEST after _filter_jumps: ", jumps)

    return jumps

def _get_axis_points(jump_points_param, index) -> list:
    axis_points = []

    for row in jump_points_param:
        axis_points.append(row[index])

    return axis_points

def main() -> None:
    jump_points = read_jump_points("test.csv")
    xdata = _get_axis_points(jump_points, 2)
    ydata = _get_axis_points(jump_points, 3)
    
    plot_arch(xdata, ydata)

if __name__ == "__main__":
    main()
    