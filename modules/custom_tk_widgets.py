import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.scrolledtext
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
matplotlib.use('TkAgg')


class EmbeddedFigure(tk.Frame):  # todo: This is written kinda crappy - rebuild.

    def __init__(self, figsize=(1,1), tracking=False, maxrecords=300, style="-", *args,**kwargs):
        super().__init__(*args, **kwargs)
        self.fig = plt.figure(figsize=figsize)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.tracking = tracking
        self.maxrecords = maxrecords
        self.hard_limits = False

        self.ax = self.fig.add_subplot()
        self.y_max = 1
        self.y_min = -1
        self.ax.set_ylim([self.y_min, self.y_max])

        self.ax.grid("minor")

        if tracking:
            self.ax.set_xlim([0, self.maxrecords])
            locs = self.ax.get_xticks()
            self.ax.set_xticklabels(np.array(np.flip(locs) * 60/self.maxrecords, dtype=float))

        self.lines = [self.ax.plot([], [], style)[0]]
        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.canvas.draw()
        self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        self.canvas.blit(self.fig.bbox)

    def draw(self):
        self.canvas.draw()

    def plot(self, lines, x_data, y_data):

        self.canvas.restore_region(self.bg)

        lines.set_xdata(x_data)
        lines.set_ydata(y_data)

        if not self.hard_limits:

            self.y_max = 1
            self.y_min = -1
            for line in self.lines:
                line_data = list(line.get_ydata())

                if line_data:
                    if self.y_max < max(line_data):
                        self.y_max = max(line_data)

                    if self.y_min > min(line_data):
                        self.y_min = min(line_data)

            self.ax.set_ylim([self.y_min, self.y_max])

        locs = self.ax.get_xticks()
        if self.tracking:
            self.ax.set_xticklabels(np.array(np.flip(locs) * 60/self.maxrecords, dtype=float))
        else:
            self.ax.set_xlim([min(x_data), max(x_data)])
        self.canvas.draw()
        self.canvas.blit(self.fig.bbox)
        self.canvas.flush_events()

    def reset_plot(self):
        if not self.hard_limits:
            self.y_max = 1
            self.y_min = -1
            self.ax.set_ylim([self.y_min, self.y_max])
        for line in self.lines:
            line.set_xdata([])
            line.set_ydata([])
        self.canvas.draw()

    def add_lines_object(self, style="-"):
        self.lines.append(self.ax.plot([], [], style)[0])

    def legend(self, labels, **kwargs):
        self.ax.legend(self.lines, labels, **kwargs)

    def xlabel(self, label):
        self.ax.set_xlabel(label)

    def ylabel(self, label):
        self.ax.set_ylabel(label)

    def set_hard_y_limits(self, lims):
        self.hard_limits = True
        self.y_min = min(lims)
        self.y_max = max(lims)
        self.ax.set_ylim([self.y_min, self.y_max])


class SlidingIndicator(tk.Frame):

    def __init__(self, label="Speed", unit="RPM",orientation="vertical", from_=5, to=0.1, res=0.1,
                 length=180, width=45, entry_pos="bot", opt=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min = min((from_, to))
        self.label = tk.Label(self, text=label)
        self.slider = tk.Scale(self, from_=from_, to=to, orient=orientation,
                               resolution=res, length=length, command=self.update_entry, showvalue=0, width=width)
        self.slider.configure(cursor="dot")
        if opt:
            self.slider.bind("<ButtonRelease-1>", opt)

        self.entry_frame = tk.Frame(self)
        self.var = tk.DoubleVar()
        self.var.set(self.min)
        self.entry = tk.Entry(self.entry_frame, textvariable=self.var)
        self.entry.configure(width=3, state="disabled", disabledbackground="white",
                             disabledforeground="black", justify="center")
        self.unit_var = tk.StringVar()
        self.unit_var.set(unit)
        self.entry_label = tk.Label(self.entry_frame,textvariable=self.unit_var)
        self.entry.grid(row=0, column=0, padx=10, pady=5)

        if entry_pos == "bot":
            self.entry_label.grid(row=1, column=0)
        elif entry_pos == "right":
            self.entry_label.grid(row=0, column=1)

        self.label.grid(row=0,column=0)
        self.slider.grid(row=1,column=0)
        if entry_pos == "bot":
            self.entry_frame.grid(row=2, column=0, sticky="N")
        elif entry_pos == "right":
            self.entry_frame.grid(row=1, column=1,sticky="E")

    def update_entry(self, *args):

        self.var.set(args[0])

    def get_value(self):

        return self.var.get()

    def configure_state(self, state):
        if state == "disabled":
            self.slider.configure(troughcolor="#f3f3f3")
        else:
            self.slider.configure(troughcolor="#c2ebc0")
        self.slider.configure(state=state)

    def reset(self):
        self.configure_state(state="normal")
        self.slider.set(self.min)
        self.var.set(self.min)
        self.configure_state(state="disabled")


class Console(tk.scrolledtext.ScrolledText):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_config("MESSAGE", foreground="green")
        self.tag_config("ERROR", foreground="red")
        self.tag_config("CCS", foreground="red")
        self.tag_config("DIRECTION", foreground="red")
        self.tag_config("CONTROLLER", foreground="magenta")
        self.tag_config("TCP", foreground="magenta")
        self.configure(state="disabled")

    def println(self, string, headline=None, msg_type="MESSAGE"):
        time = datetime.now()
        if headline is not None:
            headline = time.strftime("%Y/%m/%d %H:%M:%S ") + headline
        else:
            headline = time.strftime("%Y/%m/%d %H:%M:%S: ")

        self.configure(state="normal")
        self.insert("end", headline, msg_type)
        self.insert("end", string + '\n', "TEXT")
        self.configure(state="disabled")
        self.see("end")

    def clear(self):
        self.configure(state="normal")
        self.delete("0.0", "end")
        self.configure(state="disabled")


if __name__ == "__main__":
    app = tk.Tk()
    app.title("widget test")
    # term = TerminalEmulator(master=app)
    # term.pack()
    app.mainloop()
