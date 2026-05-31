"""
Simple Embedded Browser - Opens portal pages inside the app
Use this for Save Cornet / Save Initial to prevent logout issues
"""

import tkinter as tk
from tkinter import ttk
import threading

try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False


def open_page_in_app(url, title="MANAK Portal"):
    """
    Opens a URL in an embedded browser window
    Simple function - just opens the page, that's it!
    """
    if not WEBVIEW_AVAILABLE:
        # Fallback: show message
        import webbrowser
        webbrowser.open(url)
        return
    
    def open_window():
        try:
            window = webview.create_window(
                title,
                url,
                width=1200,
                height=800,
                resizable=True
            )
            webview.start()
        except Exception as e:
            print(f"Error opening embedded browser: {e}")
            # Fallback to external browser
            import webbrowser
            webbrowser.open(url)
    
    # Open in background thread
    thread = threading.Thread(target=open_window, daemon=True)
    thread.start()


def show_not_available_message():
    """Show message if webview is not installed"""
    root = tk.Tk()
    root.withdraw()
    from tkinter import messagebox
    messagebox.showinfo(
        "Embedded Browser Not Available",
        "Embedded browser requires 'pywebview' package.\n\n"
        "Install it with: pip install pywebview\n\n"
        "For now, the page will open in your default browser."
    )
    root.destroy()
