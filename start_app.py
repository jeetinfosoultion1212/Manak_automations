#!/usr/bin/env python3
"""
User-Friendly Launcher for MANAK Automation
Provides clear options for starting the application
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

def create_launcher_gui():
    """Create a user-friendly launcher GUI"""
    root = tk.Tk()
    root.title("MANAK Automation - Launcher")
    root.geometry("500x400")
    root.configure(bg='#f0f2f5')
    root.resizable(False, False)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (500 // 2)
    y = (root.winfo_screenheight() // 2) - (400 // 2)
    root.geometry(f"500x400+{x}+{y}")
    
    # Main frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill='both', expand=True, padx=30, pady=30)
    
    # Header
    header_label = tk.Label(main_frame, text="🚀 MANAK Automation", 
                          font=('Segoe UI', 20, 'bold'), bg='#f0f2f5', fg='#2c3e50')
    header_label.pack(pady=(0, 10))
    
    subtitle_label = tk.Label(main_frame, text="Choose how you want to start the application", 
                            font=('Segoe UI', 12), bg='#f0f2f5', fg='#7f8c8d')
    subtitle_label.pack(pady=(0, 30))
    
    # Options frame
    options_frame = ttk.Frame(main_frame)
    options_frame.pack(fill='x', pady=(0, 30))
    
    def start_normal():
        """Start application with normal license verification"""
        root.destroy()
        try:
            result = subprocess.run([sys.executable, 'desktop_manak_app.py'], 
                                  cwd=os.path.dirname(os.path.abspath(__file__)))
            if result.returncode != 0:
                messagebox.showerror("Error", "Application exited with an error")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start application: {e}")
    
    def start_dev():
        """Start application in development mode"""
        root.destroy()
        try:
            env = os.environ.copy()
            env['MANAK_DEV_MODE'] = '1'
            result = subprocess.run([sys.executable, 'desktop_manak_app.py'], 
                                  env=env, cwd=os.path.dirname(os.path.abspath(__file__)))
            if result.returncode != 0:
                messagebox.showerror("Error", "Application exited with an error")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start application: {e}")
    
    def test_dialog():
        """Test the license dialog"""
        root.destroy()
        try:
            result = subprocess.run([sys.executable, 'test_dialog_standalone.py'], 
                                  cwd=os.path.dirname(os.path.abspath(__file__)))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start dialog test: {e}")
    
    def show_help():
        """Show help information"""
        help_text = """
🔐 MANAK Automation - Help

Normal Mode:
• Full license verification required
• All features available with valid license
• Best for production use

Development Mode:
• Bypasses license verification
• All features available for testing
• Good for development and testing

Test Dialog:
• Tests just the license dialog
• Use test credentials for verification
• Good for troubleshooting

Test Credentials:
• Device ID: fe80::a600:cd6b:c570:111d%17
• User ID: 9810359334

For support, contact your administrator.
        """
        messagebox.showinfo("Help", help_text)
    
    # Normal mode button
    normal_frame = ttk.Frame(options_frame)
    normal_frame.pack(fill='x', pady=(0, 15))
    
    normal_btn = ttk.Button(normal_frame, text="🔐 Start with License Verification", 
                           command=start_normal, style='Success.TButton')
    normal_btn.pack(fill='x')
    
    normal_desc = tk.Label(normal_frame, text="Full license verification required", 
                          font=('Segoe UI', 9), bg='#f0f2f5', fg='#7f8c8d')
    normal_desc.pack(pady=(5, 0))
    
    # Development mode button
    dev_frame = ttk.Frame(options_frame)
    dev_frame.pack(fill='x', pady=(0, 15))
    
    dev_btn = ttk.Button(dev_frame, text="🔧 Start in Development Mode", 
                         command=start_dev, style='Info.TButton')
    dev_btn.pack(fill='x')
    
    dev_desc = tk.Label(dev_frame, text="Bypasses license verification for testing", 
                       font=('Segoe UI', 9), bg='#f0f2f5', fg='#7f8c8d')
    dev_desc.pack(pady=(5, 0))
    
    # Test dialog button
    test_frame = ttk.Frame(options_frame)
    test_frame.pack(fill='x', pady=(0, 15))
    
    test_btn = ttk.Button(test_frame, text="🧪 Test License Dialog", 
                          command=test_dialog, style='Warning.TButton')
    test_btn.pack(fill='x')
    
    test_desc = tk.Label(test_frame, text="Test the license verification dialog", 
                        font=('Segoe UI', 9), bg='#f0f2f5', fg='#7f8c8d')
    test_desc.pack(pady=(5, 0))
    
    # Bottom buttons
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.pack(fill='x', pady=(20, 0))
    
    help_btn = ttk.Button(bottom_frame, text="❓ Help", command=show_help)
    help_btn.pack(side='left')
    
    exit_btn = ttk.Button(bottom_frame, text="❌ Exit", 
                          command=lambda: root.quit())
    exit_btn.pack(side='right')
    
    # Focus on normal button
    normal_btn.focus()
    
    # Bind Enter key to normal start
    root.bind('<Return>', lambda e: start_normal())
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting MANAK Automation Launcher...")
    create_launcher_gui() 