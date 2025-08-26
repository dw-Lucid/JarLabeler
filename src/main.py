import sys
import os
# Add src/ to sys.path for relative imports to work when running directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import tkinter as tk
from ui import JarLabelerApp  # Your absolute import now works with path fix

if __name__ == "__main__":
    root = tk.Tk()
    app = JarLabelerApp(root)
    root.mainloop()