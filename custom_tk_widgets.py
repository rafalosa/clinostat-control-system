import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.scrolledtext
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np


class EmbeddedFigure(tk.Frame):

    def __init__(self,parent, figsize=(1,1), maxrecords=100,*args,**kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.fig = plt.figure(figsize=figsize)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.ax = self.fig.add_subplot()
        self.ax.grid("minor")
        self.lines = [self.ax.plot([], [])[0]]
        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.canvas.draw()
        self.y_max = 1
        self.y_min = -1
        self.ax.set_ylim([self.y_min, self.y_max])

    def draw(self):
        self.canvas.draw()

    def plot(self,lines, x_data, y_data,tracking=True):

        if self.y_max < max(y_data):
            self.y_max = max(y_data)

        if self.y_min > min(y_data):
            self.y_min = min(y_data)

        lines.set_xdata(x_data)
        lines.set_ydata(y_data)
        self.ax.set_ylim([self.y_min, self.y_max])
        locs = self.ax.get_xticks()
        if tracking:
            self.ax.set_xlim([0,len(x_data)])
            self.ax.set_xticklabels(np.array(np.flip(locs) / 10, dtype=int))
        else:
            self.ax.set_xlim([min(x_data),max(x_data)])
        self.canvas.draw()

    def resetPlot(self):
        self.y_max = 1
        self.y_min = -1
        self.ax.set_ylim([self.y_min, self.y_max])
        for line in self.lines:
            line.set_xdata([])
            line.set_ydata([])
        self.canvas.draw()

    def addLinesObject(self):
        self.lines.append(self.ax.plot([], [])[0])


class SlidingIndicator(tk.Frame):

    def __init__(self,parent, label="Speed",unit="RPM", *args,**kwargs):
        tk.Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.var = tk.StringVar()
        self.var.set(label)
        self.label = tk.Label(self,textvariable=self.var)
        self.slider = tk.Scale(self,from_=5,to=0.1,orient="vertical",
                               resolution=0.1,length=150,command=self.updateEntry,showvalue=0.1,width=45)
        self.slider.configure(cursor="dot",troughcolor="green")

        self.entry_frame = tk.Frame(self)
        self.var = tk.DoubleVar()
        self.var.set(0.1)
        self.entry = tk.Entry(self.entry_frame,textvariable=self.var)
        self.entry.config(width=3,state="disabled")
        self.entry.configure(disabledbackground="white",disabledforeground="black")
        self.unit_var = tk.StringVar()
        self.unit_var.set(unit)
        self.entry_label = tk.Label(self.entry_frame,textvariable=self.unit_var)
        self.entry.grid(row=0,column=0)
        self.entry_label.grid(row=0, column=1)

        self.label.grid(row=0,column=0)
        self.slider.grid(row=1,column=0)
        self.entry_frame.grid(row=2, column=0)

    def updateEntry(self,*args):
        self.var.set(args[0])

    def getValue(self):
        return self.var.get()

    def configureState(self,state):
        if state == "disabled":
            self.slider.configure(troughcolor="#f3f3f3")
        else:
            self.slider.configure(troughcolor="#c2ebc0")
        self.slider.configure(state=state)

    def reset(self):
        self.slider.set(0.1)
        self.var.set(0.1)


class Console(tk.scrolledtext.ScrolledText):

    def __init__(self,parent,**kwargs):
        tk.scrolledtext.ScrolledText.__init__(self,parent,**kwargs)
        self.tag_config("MESSAGE",foreground="green")
        self.tag_config("ERROR",foreground="red")
        self.tag_config("CCS", foreground="red")
        self.tag_config("DIRECTION", foreground="red")
        self.tag_config("CONTROLLER", foreground="magenta")
        self.tag_config("TCP",foreground="magenta")
        self.configure(state="disabled")

    def println(self,string,headline=None,msg_type="MESSAGE"):
        self.configure(state="normal")
        time = datetime.now()
        if headline is not None:
            headline = time.strftime("%Y/%m/%d %H:%M:%S ") + headline
        else:
            headline = time.strftime("%Y/%m/%d %H:%M:%S: ")

        self.insert("end",headline,msg_type)
        self.insert("end",string + '\n',"TEXT")
        self.configure(state="disabled")
        self.see("end")
        # todo: Add logging to text file.
