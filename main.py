from tkinter import PhotoImage
from app.app import App

if __name__ == "__main__":
    root = App()
    root.resizable(False, False)
    root.title("Clinostat control system")
    root.iconphoto(True, PhotoImage(file="icon/favicon.gif"))
    root.after(1, root.program_loop)
    root.mainloop()
