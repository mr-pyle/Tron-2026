# main.py
from gui import TronApp

if __name__ == "__main__":
    print("Initializing Tron Tournament Engine...")
    
    # Instantiate the Tkinter application
    app = TronApp()
    
    # Start the main event loop
    app.root.mainloop()