# imports

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import numpy as np
from scipy.interpolate import make_interp_spline

TRAJECTORY_EVENTS = ["jump_executed", "jump_peak_reached", "landed"]
test = False

def plot_arch(xdata_param, ydata_param, time_param):
    # sources: 
    # https://sqlpey.com/python/how-to-adjust-y-axis-range-to-start-from-0-in-matplotlib/
    # https://www.geeksforgeeks.org/machine-learning/how-to-plot-a-smooth-curve-in-matplotlib/
    # https://matplotlib.org/stable/gallery/widgets/slider_demo.html

    init_time = 0

    f, ax = plt.subplots()  # Create a figure and an axes
    xdata = np.asarray(xdata_param, dtype=float)
    ydata = np.asarray(ydata_param, dtype=float)
    times = np.asarray(time_param, dtype=float)

    if not (len(xdata) == len(ydata) == len(times)):
        raise ValueError("xdata, ydata, and time_param must have the same length")

    def draw_jumps(until_time):
        ax.clear()
        ax.invert_yaxis()

        # Plot only jumps whose landing has happened by the selected time.
        for start in range(0, len(xdata) - 2, 3):
            jump_times = times[start:start + 3]
            if jump_times[-1] > until_time:
                continue

            jump_x = xdata[start:start + 3]
            jump_y = ydata[start:start + 3]

            # Use point order as the independent variable so duplicate x or y values are valid.
            t = np.arange(3, dtype=float)
            t_smooth = np.linspace(t[0], t[-1], 100)
            x_smooth = make_interp_spline(t, jump_x, k=2)(t_smooth)
            y_smooth = make_interp_spline(t, jump_y, k=2)(t_smooth)

            ax.plot(x_smooth, y_smooth)

        ax.set_title(f"Jumps up to {until_time:.2f} seconds")
        ax.set_xlabel("X position")
        ax.set_ylabel("Y position")

    # Leave room below the plot for the time slider.
    f.subplots_adjust(bottom=0.2)
    axfreq = f.add_axes((0.25, 0.06, 0.65, 0.03))
    time_slider = Slider(
    ax=axfreq,
    label='Time [Seconds]',
    valmin=0.0,
    valmax=float(times[-1]),
    valinit=init_time,
    )

    time_slider.on_changed(draw_jumps)
    draw_jumps(init_time)

    # ax.scatter(xdata, ydata)
    plt.show()              # Display the figure
    


def read_points(csv, events) -> list:
    with open(csv, "r") as file:
        header = file.readline()
        # print(header) # timestamp_seconds,event,x,y,velocity_x,velocity_y,action,info

        lines = file.readlines()
        data = []

        for line in lines:
            entry = line.split(",")
            if entry[1] in events:
                data.append(entry)

    return data
    
def _filter_jumps(jumps: list) -> list:
    if test:
        print("TEST before _filter_jumps: ", jumps)

    filtered_jumps = []
    execution_indices = [
        index for index, row in enumerate(jumps)
        if row[1] == "jump_executed"
    ]

    # Group events by the jump they belong to, not by their raw row order.
    # Peak and landing can be recorded in either order near a platform collision.
    for execution_number, execution_index in enumerate(execution_indices):
        next_execution_index = (
            execution_indices[execution_number + 1]
            if execution_number + 1 < len(execution_indices)
            else len(jumps)
        )
        jump_events = jumps[execution_index:next_execution_index]
        peak = next((row for row in jump_events if row[1] == "jump_peak_reached"), None)
        landing = next((row for row in jump_events if row[1] == "landed"), None)

        if peak is not None and landing is not None:
            filtered_jumps.extend([jumps[execution_index], peak, landing])

    if test:
        print("TEST after _filter_jumps: ", filtered_jumps)

    return filtered_jumps

def _get_axis_points(jump_points_param, index) -> list:
    axis_points = []

    for row in jump_points_param:
        axis_points.append(row[index])

    return axis_points

def main() -> None:
    jump_points = read_points("test.csv", TRAJECTORY_EVENTS)
    jump_points = _filter_jumps(jump_points)
    xdata = _get_axis_points(jump_points, 2)
    ydata = _get_axis_points(jump_points, 3)
    time_data = _get_axis_points(jump_points, 0)
    
    plot_arch(xdata, ydata, time_data)

if __name__ == "__main__":
    main()
    