
# Entry point for the JarLabeler application
from ui import JarLabelerApp

if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    app = JarLabelerApp(root)
    root.mainloop()