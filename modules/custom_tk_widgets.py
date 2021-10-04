import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.scrolledtext
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
matplotlib.use('TkAgg')


class EmbeddedFigure(tk.Frame):

    def __init__(self, figsize=(1,1), maxrecords=100, spatial = False,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fig = plt.figure(figsize=figsize)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.spatial = spatial
        if self.spatial:
            self.ax = self.fig.add_subplot(projection="3d")
            self.y_max = 1
            self.y_min = -1
            self.x_max = 1
            self.x_min = -1
            self.z_max = 1
            self.z_min = -1
            self.ax.set_ylim([self.y_min, self.y_max])
            self.ax.set_xlim([self.x_min, self.x_max])
            self.ax.set_zlim([self.z_min, self.z_max])

        else:
            self.ax = self.fig.add_subplot()
            self.y_max = 1
            self.y_min = -1
            self.ax.set_ylim([self.y_min, self.y_max])

        self.ax.grid("minor")
        self.lines = [self.ax.plot([], [])[0]]
        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.canvas.draw()

    def draw(self):
        self.canvas.draw()

    def plot(self,lines, x_data, y_data,z_data = None,tracking=True):

        if self.spatial:
            self.ax.quiver(0,0,0,x_data/9.81,y_data/9.81,z_data/9.81,length=1,normalize=True)

        else:
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

    def legend(self, labels,**kwargs):
        self.ax.legend(self.lines, labels,**kwargs)

    def xlabel(self, label):
        self.ax.set_xlabel(label)

    def ylabel(self, label):
        self.ax.set_ylabel(label)


class SlidingIndicator(tk.Frame):

    def __init__(self,label="Speed",unit="RPM",orientation="vertical", from_=5,to=0.1,res=0.1,
                 length=180, width=45, entry_pos = "bot", opt=None, *args,**kwargs):
        super().__init__(*args, **kwargs)
        self.min = min((from_, to))
        self.var = tk.StringVar()
        self.var.set(label)
        self.label = tk.Label(self,textvariable=self.var)
        self.slider = tk.Scale(self,from_=from_,to=to,orient=orientation,
                               resolution=res,length=length,command=self.updateEntry,showvalue=0,width=width)
        self.slider.configure(cursor="dot")
        self.opt = opt

        self.entry_frame = tk.Frame(self)
        self.var = tk.DoubleVar()
        self.var.set(self.min)
        self.entry = tk.Entry(self.entry_frame,textvariable=self.var)
        self.entry.configure(width=3,state="disabled",disabledbackground="white",
                             disabledforeground="black",justify="center")
        self.unit_var = tk.StringVar()
        self.unit_var.set(unit)
        self.entry_label = tk.Label(self.entry_frame,textvariable=self.unit_var)
        self.entry.grid(row=0,column=0)

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

    def updateEntry(self, *args):
        if self.opt:
            self.opt()
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
        self.configureState(state="normal")
        self.slider.set(self.min)
        self.var.set(self.min)
        self.configureState(state="disabled")


class Console(tk.scrolledtext.ScrolledText):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.tag_config("MESSAGE",foreground="green")
        self.tag_config("ERROR",foreground="red")
        self.tag_config("CCS", foreground="red")
        self.tag_config("DIRECTION", foreground="red")
        self.tag_config("CONTROLLER", foreground="magenta")
        self.tag_config("TCP",foreground="magenta")
        self.configure(state="disabled")

    def println(self,string,headline=None,msg_type="MESSAGE"):
        time = datetime.now()
        self.configure(state="normal")
        if headline is not None:
            headline = time.strftime("%Y/%m/%d %H:%M:%S ") + headline
        else:
            headline = time.strftime("%Y/%m/%d %H:%M:%S: ")

        self.insert("end",headline,msg_type)
        self.insert("end",string + '\n',"TEXT")
        self.configure(state="disabled")
        self.see("end")

# Should reconsider this or at least postpone it. This is not very trivial to implement nor is it necessary.
# class TerminalEmulator(tk.scrolledtext.ScrolledText):
#     def __init__(self,**kwargs):
#         super().__init__(**kwargs)
#         self.bind("<Return>",self.getInput)
#
#     def getInput(self,event):
#         input = self.get("1.0","end-1c")
#
#         str_ = os.popen(input)
#         out = str_.read()
#         print(out)


if __name__ == "__main__":
    app = tk.Tk()
    app.title("widget test")

    # term = TerminalEmulator(master=app)
    # term.pack()
    app.mainloop()