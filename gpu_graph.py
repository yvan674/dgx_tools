"""GPU Usage.

Outputs GPU usage in a Line chart along with memory usage in a bar chart.


Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    December 13, 2019
"""
from curses import newwin, KEY_RESIZE, doupdate
import curses
from time import sleep
import GPUtil
from math import ceil, floor
import argparse


def parse_argument():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description='graphically show GPU usage')

    parser.add_argument('-i', '--interval', type=float,
                        help='update interval in seconds')

    return parser.parse_args()


def read_keys(stdscr):
    """Reads all keys pressed between calls.

    :returns: All keys pressed as their integer values.
    :rtype: list
    """
    keys = []
    while True:
        k = stdscr.getch()
        if k != -1:
            keys.append(k)
        else:
            return keys


def plot(series: list or tuple, cfg: dict = None):
    """Returns lines of an ascii plot.

    Notes:
        Possible cfg parameters are 'minimum', 'maximum', 'offset', 'height'
        and 'format'.

    Example:
        >>> series = [2, 5, 1, 3, 4, 1]
        >>> print(plot(series, { 'height' :10 }))
    """
    cfg = cfg or {}
    minimum = cfg['minimum'] if 'minimum' in cfg else min(series)
    maximum = cfg['maximum'] if 'maximum' in cfg else max(series)

    interval = abs(float(maximum) - float(minimum))
    offset = cfg['offset'] if 'offset' in cfg else 3
    height = cfg['height'] if 'height' in cfg else interval
    ratio = height / interval
    min2 = floor(float(minimum) * ratio)
    max2 = ceil(float(maximum) * ratio)

    intmin2 = int(min2)
    intmax2 = int(max2)

    rows = abs(intmax2 - intmin2)
    width = len(series) + offset
    placeholder = cfg['format'] if 'format' in cfg else '{:8.2f} '

    result = [[' '] * width for _ in range(rows + 1)]

    # axis and labels
    for y in range(intmin2, intmax2 + 1):
        label = placeholder.format(
            float(maximum) - ((y - intmin2) * interval / rows))
        result[y - intmin2][max(offset - len(label), 0)] = label
        result[y - intmin2][offset - 1] = '┼' if y == 0 else '┤'

    y0 = int(series[0] * ratio - min2)
    result[rows - y0][offset - 1] = '┼'  # first value

    for x in range(0, len(series) - 1):  # plot the line
        y0 = int(round(series[x + 0] * ratio) - intmin2)
        y1 = int(round(series[x + 1] * ratio) - intmin2)
        if y0 == y1:
            result[rows - y0][x + offset] = '─'
        else:
            result[rows - y1][x + offset] = '╰' if y0 > y1 else '╭'
            result[rows - y0][x + offset] = '╮' if y0 > y1 else '╯'
            start = min(y0, y1) + 1
            end = max(y0, y1)
            for y in range(start, end):
                result[rows - y][x + offset] = '│'

    return [''.join(row) for row in result]


def redraw_windows(gpus, sizes):
    """Redraws windows according to screen sizes given

    :param gpus: list of gpu objects returned by GPUtil
    :param sizes: list of dictionaries containing the sizes of each window
    :type sizes: list
    :type gpus: list
    :return: tuple containing (list of curses window objects, val_utilizations)
    :rtype: tuple
    """
    windows = []
    val_utilizations = []
    for i, size in enumerate(sizes):
        win = newwin(size['nlines'], size['ncols'],
                     size['begin_y'], size['begin_x'])
        win.clear()
        win.border()
        win.addstr(0, 2, "GPU {}: {}".format(i, gpus[i].name))
        win.noutrefresh()
        windows.append(win)
        val_utilizations.append([0, 0])

    return windows, val_utilizations


def draw_utilization_plot(window, values: list) -> list:
    """Draws the GPU utilization plot.

    Args:
        window: Window to draw the chart in.
        values: The values to draw on the chart.

    Returns:
        The utilization list, truncated if it's
    """
    h, w = window.getmaxyx()
    if len(values) > w - 7:
        values.pop(0)

    res = plot(values, cfg={'minimum': 0, 'maximum': 100,
                            'height': h - 1, 'format': '{:3.0f}%',
                            'offset': 3})

    for i, line in enumerate(res):
        window.addstr(i, 0, line)
    window.noutrefresh()
    return values


def draw_memory_chart(window, gpu_total: float or int, gpu_usage: float or int):
    """Draws a bar chart.

    Args:
        window: Window to draw the chart in
        gpu_total: The total memory a GPU has.
        gpu_usage: The total memory currently being used on the GPU
    """
    h, w = window.getmaxyx()

    # Clear out rows
    for i in range(h - 3, -1, -1):
        window.addstr(i, 0, ' ' * w)

    # Calculate number of blocks to use. Each row can either be 1 or 2 blocks.
    blocks = round(gpu_usage / gpu_total * (h + h - 2))
    # If this requires a half block, the value will be odd
    full_rows = floor(blocks / 2)
    half_row = False if blocks % 2 == 0 else True

    # Draw the label
    value = '{:5.0f}'.format(gpu_usage)
    # First, center it
    start_pos = int((w / 2)) - int((len(value) / 2))
    window.addstr(h - 2, start_pos, value)
    # Now draw in the rows
    for i in range(h - 3, -1, -1):
        if full_rows == 0 and not half_row:
            break
        if full_rows != 0:
            window.addstr(i, 0, '█' * w)
            full_rows -= 1
        elif half_row:
            window.addstr(i, 0, '▄' * w)
            half_row = False

    window.noutrefresh()


def calculate_sizes(stdscr, num_gpus: int) -> list or int:
    """Calculate appropriate plot sizes.

    Calculates the sizes that should be appropriate to show plots. If the
    terminal window is large enough, it uses multiple columns. It returns the
    boxes for each GPU window

    Returns:
        A list of 4-tuples containing (x, y, w, h), or -1 if the window is
        too small.
    """
    out_dict = []
    h, w = stdscr.getmaxyx()
    w -= 1
    h -= 2

    # Figure out appropriate layout
    min_height = 10
    min_width = 35

    columns = floor(w / min_width)
    rows = ceil(num_gpus / columns)

    width = floor(w / columns)
    height = floor(h / rows)

    if width < min_width or height < min_height:
        return -1

    for i in range(num_gpus):
        col = i % columns
        row = floor(i / columns)

        x_pad = 1 if col > 0 else 0
        y_pad = 1 if row > 0 else 0

        x = (col * width) + x_pad
        y = (row * height) + y_pad

        out_dict.append({'nlines': height, 'ncols': width, 'begin_y': y,
                         'begin_x': x})

    return out_dict


def main(stdscr, update_interval: float = 1.):
    # Clear screen
    stdscr.clear()
    stdscr.nodelay(True)

    sleep_interval = update_interval / 2

    gpus = GPUtil.getGPUs()

    if len(gpus) == 0:
        raise Exception("No GPUs found")

    val_utilizations = []
    mem_utilizations = [{'gpu_total': gpu.memoryTotal,
                         'gpu_usage': gpu.memoryUsed}
                        for gpu in gpus]
    windows = []
    sizes = calculate_sizes(stdscr, len(gpus))
    redraw = True

    while True:
        # Refresh
        keys = read_keys(stdscr)
        # Case by case for each key option
        if ord('q') in keys:
            return

        # Handle window resize
        if KEY_RESIZE in keys or sizes == -1:
            stdscr.clear()
            sizes = calculate_sizes(stdscr, len(gpus))

            # calculate_sizes has returned an error meaning the window
            # size is to small
            if sizes == -1:
                h, w = stdscr.getmaxyx()
                assert w > 21, 'Terminal window is too small.'

                error_string = ['Window is too small.',
                                'Please make it bigger',
                                'or press "Q" to quit.']
                for i in range(len(error_string)):
                    stdscr.addstr(i, 0, error_string[i])
                stdscr.refresh()
                redraw = False
            else:
                redraw = True

            sleep(sleep_interval)
            continue

        if redraw:
            windows, val_utilizations = redraw_windows(gpus, sizes)
            redraw = False

        # Now run the plotting and stuff
        gpus = GPUtil.getGPUs()
        for i, gpu in enumerate(gpus):
            # Get utilizations
            val_utilizations[i].append(gpu.load * 100)
            mem_utilizations[i]['gpu_usage'] = gpu.memoryUsed

            # Create plot for GPU utilization
            util_window = windows[i].derwin(sizes[i]['nlines'] - 4,
                                            sizes[i]['ncols'] - 9,
                                            2,
                                            2)

            val_utilizations[i] = draw_utilization_plot(util_window,
                                                        val_utilizations[i])

            # Create bar chart for memory utilization
            mem_window = windows[i].derwin(
                sizes[i]['nlines'] - 2, 5, 2, sizes[i]['ncols'] - 7
            )
            draw_memory_chart(mem_window, **mem_utilizations[i])
            # windows[i].noutrefresh()
        #
        doupdate()
        sleep(sleep_interval)


if __name__ == '__main__':
    args = parse_argument()
    try:
        # Initialize curses
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        curses.curs_set(0)

        try:
            curses.start_color()
        except curses.error:
            pass
        if args.interval:
            main(stdscr, args.interval)
        else:
            main(stdscr)
    finally:
        # Set everything back to normal
        if 'stdscr' in locals():
            stdscr.clear()
            stdscr.refresh()
            stdscr.keypad(0)
        curses.curs_set(1)
        curses.echo()
        curses.nocbreak()
        curses.endwin()
