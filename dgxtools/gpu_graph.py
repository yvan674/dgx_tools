#!/usr/bin/python3
"""GPU Usage.

Outputs GPU usage in a Line chart along with memory usage in a bar chart.


Author:
    Yvan Satyawan <y_satyawan@hotmail.com>

Created on:
    December 13, 2019
"""
from curses import newwin, KEY_RESIZE, doupdate
import curses
from math import ceil, floor
import argparse
from threading import Timer
from sys import exit
from subprocess import Popen, PIPE
import os


def safe_float_cast(str_number):
    try:
        number = float(str_number)
    except ValueError:
        number = float('nan')
    return number


def get_gpus():
    # Call the nvidia-smi tool
    try:
        p = Popen(['nvidia-smi',
                   '--query-gpu=utilization.gpu,memory.total,memory.used,name',
                   '--format=csv,noheader,nounits'],
                  stdout=PIPE)
        stdout, stderror = p.communicate()
    except FileNotFoundError:
        return []
    output = stdout.decode('UTF-8')
    output = output.split(os.linesep)

    gpus = []

    for line in output[:-1]:
        vals = line.split(', ')
        gpu_state = {
            "load": safe_float_cast(vals[0]) / 100,
            "memory_total": safe_float_cast(vals[1]),
            "memory_used": safe_float_cast(vals[2]),
            "name": vals[3]
        }
        gpus.append(gpu_state)
    return gpus


def parse_argument():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description='graphically show GPU usage')

    parser.add_argument('-i', '--interval', type=float,
                        help='update interval in seconds')

    return parser.parse_args()


class GpuGraph:
    def __init__(self, stdscr, colors, interval=1):
        """Creates a GpuGraph Instance, which visualizes gpu usage as graphs.

        Visualizes GPU usage as ASCII graphs within the terminal window using
        curses.

        :param stdscr: the current stdscr instance from curses
        :param colors: whether or not to use colors.
        :param interval: how often to update the screen in seconds
        :type colors: bool
        :type interval: int or float

        :returns: a GpuGraph object
        :rtype: GpuGraph
        """
        self.stdscr = stdscr
        self.interval = interval
        self.gpus = get_gpus()
        self.num_gpus = len(self.gpus)
        assert self.num_gpus > 0, "No GPUs found"

        self.val_utilizations = []
        self.mem_utilizations = [{'gpu_total': gpu['memory_total'],
                                  'gpu_usage': gpu['memory_used']}
                                 for gpu in self.gpus]
        self.windows = []
        self.sizes = None
        self.calculate_sizes()

        self.redraw = True
        self.cont = True

        self.colors = colors

    def run(self):
        # Clear screen
        self.stdscr.clear()
        self.stdscr.nodelay(True)
        self.mainloop()
        while self.cont:
            t = Timer(self.interval, self.mainloop)
            t.run()

    def mainloop(self):
        keys = self.read_keys()
        # Case by case for each key option
        if ord('q') in keys:
            self.cont = False
            return

        # Handle window resize
        if KEY_RESIZE in keys or self.sizes == -1:
            self.handle_window_resize()
            return

        if self.redraw:
            self.redraw_windows()
            self.redraw = False

        # Now run the plotting and stuff
        self.gpus = get_gpus()
        for i in range(self.num_gpus):
            # Get utilizations
            self.val_utilizations[i].append(self.gpus[i]['load'] * 100)
            self.mem_utilizations[i]['gpu_usage'] = self.gpus[i]['memory_used']

            # Actually draw the windows
            self.draw_utilization_plot(i)
            self.draw_memory_chart(i)

        doupdate()

    def read_keys(self):
        """Reads all keys pressed between calls.

            :returns: All keys pressed as their integer values.
            :rtype: list
            """
        keys = []
        while True:
            k = self.stdscr.getch()
            if k != -1:
                keys.append(k)
            else:
                return keys

    def handle_window_resize(self):
        """Handles resizing of windows."""
        self.stdscr.clear()
        self.calculate_sizes()

        # calculate_sizes has returned an error meaning the window
        # size is to small
        if self.sizes == -1:
            h, w = self.stdscr.getmaxyx()
            start_y = int((w / 2) - 11)
            start_x = int((h / 2) - 2)
            assert w > 25, 'Terminal window is too small.'

            error_string = ['Window is too small.',
                            'Please make it bigger',
                            'or press "Q" to quit.']
            for i in range(len(error_string)):
                self.stdscr.addstr(start_x + i, start_y, error_string[i])
            self.stdscr.refresh()
            self.redraw = False
        else:
            self.redraw = True

    @staticmethod
    def plot_line_chart(series: list or tuple, cfg: dict = None):
        """Returns lines of an ascii plot.

        Notes:
            Possible cfg parameters are 'minimum', 'maximum', 'offset', 'height'
            and 'format'.

        Example:
            >>> series = [2, 5, 1, 3, 4, 1]
            >>> print(GpuGraph.plot_line_chart(series, { 'height' :10 }))
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
            y0 = int(floor(series[x + 0] * ratio) - intmin2)
            y1 = int(floor(series[x + 1] * ratio) - intmin2)
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

    def redraw_windows(self):
        """Redraws windows according to screen sizes given."""
        windows = []
        val_utilizations = []
        for i, size in enumerate(self.sizes):
            win = newwin(size['nlines'], size['ncols'],
                         size['begin_y'], size['begin_x'])
            name = self.gpus[i]['name']
            if len(name) > size['ncols'] - 11:
                name = name[:size['ncols'] - 12] + "…"
            win.clear()
            if self.colors:
                win.attrset(curses.color_pair(9))
            win.border()
            win.addstr(0, 2, "GPU {}: {}".format(i, name))
            if self.colors:
                win.attrset(curses.color_pair(0))
            win.noutrefresh()
            windows.append(win)
            val_utilizations.append([0, 0])
        self.windows = windows
        self.val_utilizations = val_utilizations

    def draw_utilization_plot(self, i: int):
        """Draws the GPU utilization plot.

        :param i: the iterator representing the current GPU/window number
        """
        window = self.windows[i].derwin(self.sizes[i]['nlines'] - 4,
                                        self.sizes[i]['ncols'] - 9,
                                        2,
                                        2)
        h, w = window.getmaxyx()
        if len(self.val_utilizations[i]) > w - 7:
            self.val_utilizations[i].pop(0)

        res = self.plot_line_chart(self.val_utilizations[i],
                                   cfg={'minimum': 0,
                                        'maximum': 100,
                                        'height': h - 1,
                                        'format': '{:3.0f}%',
                                        'offset': 3})

        top_10 = floor(len(res) / 10)

        for j, line in enumerate(res):
            if self.colors:
                axis_color = [curses.color_pair(7)]
                if j <= top_10:
                    line_color = [curses.color_pair(10)]
                else:
                    line_color = [curses.color_pair(9)]
            else:
                axis_color = []
                line_color = []

            try:
                window.addstr(j, 0, line[0:6], *axis_color)
                window.addstr(j, 6, line[6:], *line_color)
            except curses.error:
                raise ValueError("window size: {}, {}, i: {}".format(h, w, j))

        window.noutrefresh()

    def draw_memory_chart(self, i: int):
        """Draws a column chart visualization of memory usage.

        :param i: the current gpu/window iterator value
        """
        window = self.windows[i].derwin(self.sizes[i]['nlines'] - 2,
                                        5,
                                        2,
                                        self.sizes[i]['ncols'] - 7)
        h, w = window.getmaxyx()

        # Clear out rows
        for y_pos in range(h - 3, -1, -1):
            window.addstr(y_pos, 0, ' ' * w)

        gpu_usage = self.mem_utilizations[i]['gpu_usage']
        gpu_total = self.mem_utilizations[i]['gpu_total']

        # Calculate number of blocks to use. Each row can either be 1 or 2
        # blocks.
        blocks = floor(gpu_usage / gpu_total * (h + h - 2))

        top_10 = floor((h - 1) / 10)
        # If this requires a half block, the value will be odd
        full_rows = floor(blocks / 2)
        half_row = False if blocks % 2 == 0 else True

        # Set value and value colors, if colors is available
        value = '{:^5.0f}'.format(gpu_usage)
        if self.colors:
            if full_rows + half_row > top_10 * 9:
                value_color = [curses.color_pair(10)]
            else:
                value_color = [curses.color_pair(9)]
        else:
            value_color = []

        # Then draw the memory used value
        window.addstr(h - 2, 0, value, *value_color)

        # Now set the default bar colors.
        if self.colors:
            bar_color = [curses.color_pair(9)]
        else:
            bar_color = []

        # Now draw in the rows. Start from the bottom.
        for i in range(h - 3, -1, -1):
            # Check to see if we've reached top 10% yet.
            if self.colors and i <= top_10:
                bar_color = [curses.color_pair(10)]

            if gpu_usage == 0:
                window.addstr(i, 0, '_' * w, *bar_color)
                break
            if full_rows == 0 and not half_row:
                break
            if full_rows != 0:
                window.addstr(i, 0, '█' * w, *bar_color)
                full_rows -= 1
            elif half_row:
                window.addstr(i, 0, '▄' * w, *bar_color)
                half_row = False

        window.noutrefresh()

    def calculate_sizes(self):
        """Calculate appropriate plot sizes.

        Calculates the sizes that should be appropriate to show plots. If the
        terminal window is large enough, it uses multiple columns. It returns
        the boxes for each GPU window. This uses a partioning algorithm, but
        non-recursively does the partioning.

        Returns:
            list or int: A list of dictionaries containing 'nlines', 'ncols',
                'begin_y', and 'begin_x' for each window object that corresponds
                to each GPU.
        """
        sizes = []
        h, w = self.stdscr.getmaxyx()
        w -= 1
        h -= 2
        # Figure out appropriate layout
        min_height = 10
        min_width = 18

        partitions = 1

        columns = 1
        rows = 1

        while partitions < self.num_gpus:
            cut_height = floor(h / rows)
            cut_width = floor(w / columns)

            if cut_width > cut_height:
                # Then we cut vertically
                columns += 1
            else:
                # Then we cut horizontally
                rows += 1
            partitions = rows * columns

        width = floor(w / columns) - 1
        height = floor(h / rows) - 1

        if width < min_width or height < min_height:
            self.sizes = -1
            return

        for i in range(self.num_gpus):
            col = i % columns
            row = floor(i / columns)

            x_pad = 1 if col > 0 else 0
            y_pad = 1 if row > 0 else 0

            x = (col * width) + x_pad
            y = (row * height) + y_pad

            sizes.append({'nlines': height, 'ncols': width, 'begin_y': y,
                          'begin_x': x})

        self.sizes = sizes


def gpu_graph():
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
            curses.use_default_colors()
            for i in range(0, 17):
                curses.init_pair(i + 1, i, -1)
            colors = True
        except curses.error:
            # Ignore and accept colorless
            colors = False

        if args.interval:
            graph = GpuGraph(stdscr, colors, args.interval)
        else:
            graph = GpuGraph(stdscr, colors)
        graph.run()
    except KeyboardInterrupt:
        exit(0)
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


if __name__ == '__main__':
    gpu_graph()
