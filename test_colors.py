#!/usr/bin/env python3
"""
Simple color test to verify visibility
"""

import tkinter as tk
from tkinter import ttk

class ColorTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Color Test - Professional Theme")
        self.root.geometry("800x600")
        
        # Professional color scheme
        self.colors = {
            'primary': '#2563eb',      # Professional Blue
            'secondary': '#7c3aed',    # Elegant Purple
            'success': '#059669',      # Rich Green
            'warning': '#d97706',      # Warm Orange
            'danger': '#dc2626',       # Bold Red
            'dark': '#0f172a',         # Deep Navy Blue
            'surface': '#1e293b',      # Card Surface
            'light': '#f8fafc',        # Pure White
            'text_primary': '#1e293b', # Primary Text
        }
        
        # Configure root background
        self.root.configure(bg=self.colors['dark'])
        
        # Create main frame
        main_frame = tk.Frame(self.root, bg=self.colors['dark'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main_frame, 
                        text="Professional Color Scheme Test",
                        font=('Segoe UI', 16, 'bold'),
                        bg=self.colors['dark'],
                        fg=self.colors['light'])
        title.pack(pady=(0, 20))
        
        # Color test section
        self.create_color_test(main_frame)
        
        # Button test section
        self.create_button_test(main_frame)
        
    def create_color_test(self, parent):
        # Color test frame
        color_frame = tk.LabelFrame(parent, 
                                  text="Color Visibility Test",
                                  font=('Segoe UI', 12, 'bold'),
                                  bg=self.colors['surface'],
                                  fg=self.colors['light'],
                                  relief='solid',
                                  bd=1)
        color_frame.pack(fill='x', pady=(0, 20))
        
        # Test different background colors
        colors_to_test = [
            ('Primary Blue', self.colors['primary']),
            ('Secondary Purple', self.colors['secondary']),
            ('Success Green', self.colors['success']),
            ('Warning Orange', self.colors['warning']),
            ('Danger Red', self.colors['danger']),
            ('Surface Gray', self.colors['surface']),
        ]
        
        for name, color in colors_to_test:
            frame = tk.Frame(color_frame, bg=color, height=40)
            frame.pack(fill='x', padx=10, pady=5)
            frame.pack_propagate(False)
            
            label = tk.Label(frame, 
                           text=f"{name}: {color}",
                           bg=color,
                           fg=self.colors['light'],
                           font=('Segoe UI', 10, 'bold'))
            label.pack(expand=True)
    
    def create_button_test(self, parent):
        # Button test frame
        button_frame = tk.LabelFrame(parent,
                                   text="Button Test",
                                   font=('Segoe UI', 12, 'bold'),
                                   bg=self.colors['surface'],
                                   fg=self.colors['light'],
                                   relief='solid',
                                   bd=1)
        button_frame.pack(fill='x')
        
        # Button container
        btn_container = tk.Frame(button_frame, bg=self.colors['surface'])
        btn_container.pack(padx=20, pady=20)
        
        # Test buttons
        buttons = [
            ('Primary', self.colors['primary']),
            ('Secondary', self.colors['secondary']),
            ('Success', self.colors['success']),
            ('Warning', self.colors['warning']),
            ('Danger', self.colors['danger']),
        ]
        
        for i, (text, color) in enumerate(buttons):
            btn = tk.Button(btn_container,
                          text=text,
                          bg=color,
                          fg=self.colors['light'],
                          font=('Segoe UI', 10, 'bold'),
                          relief='flat',
                          padx=20,
                          pady=10,
                          command=lambda t=text: print(f"Clicked {t}"))
            btn.grid(row=0, column=i, padx=5)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ColorTest()
    app.run()
