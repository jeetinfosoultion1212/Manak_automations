import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

class TagManager:
    """Manages mapping between Jeweller Names and Tag Prefixes"""
    
    def __init__(self, mapping_file="jeweller_tags.json"):
        # Store in the same directory as the executable or script context
        self.mapping_file = os.path.abspath(mapping_file)
        self.mappings = {}
        self.load_mappings()

    def load_mappings(self):
        """Load mappings from JSON file"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                         self.mappings = json.loads(content)
                    else:
                         self.mappings = {}
            except Exception as e:
                print(f"Error loading tag mappings: {e}")
                self.mappings = {}
        else:
            self.mappings = {}

    def save_mappings(self):
        """Save mappings to JSON file"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving tag mappings: {e}")

    def get_prefix(self, jeweller_name):
        """Get tag prefix for a jeweller name (case-insensitive lookup preferred)"""
        # Try exact match first
        if jeweller_name in self.mappings:
            return self.mappings[jeweller_name]
        
        # Try case-insensitive
        name_lower = jeweller_name.lower()
        for name, prefix in self.mappings.items():
            if name.lower() == name_lower:
                return prefix
                
        return None

    def show_editor(self, parent):
        """Show the editor dialog"""
        editor = tk.Toplevel(parent)
        editor.title("Manage Jeweller Tag Prefixes")
        editor.geometry("600x450")
        
        # Modal
        editor.transient(parent)
        editor.grab_set()
        
        # Styles
        style = ttk.Style()
        style.configure("TagManager.TButton", padding=5)

        # Header
        header_frame = ttk.Frame(editor, padding="10")
        header_frame.pack(fill='x')
        ttk.Label(header_frame, text="Map Jeweller Names to Tag Prefixes", font=('Segoe UI', 10, 'bold')).pack(side='left')
        
        # Content Frame
        content_frame = ttk.Frame(editor, padding="10")
        content_frame.pack(fill='both', expand=True)

        # Treeview Scrollbar
        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('Jeweller Name', 'Tag Prefix')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        
        yscroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        
        tree.heading('Jeweller Name', text='Jeweller Name')
        tree.heading('Tag Prefix', text='Tag Prefix')
        tree.column('Jeweller Name', width=350)
        tree.column('Tag Prefix', width=150)
        
        tree.pack(side='left', fill='both', expand=True)
        yscroll.pack(side='right', fill='y')

        # Fill Tree
        for name in sorted(self.mappings.keys()):
            tree.insert('', 'end', values=(name, self.mappings[name]))

        # Helper functions
        def refresh_tree():
            for item in tree.get_children():
                tree.delete(item)
            for name in sorted(self.mappings.keys()):
                tree.insert('', 'end', values=(name, self.mappings[name]))

        def add_mapping():
            name = simpledialog.askstring("Add Mapping", "Enter Jeweller Name:", parent=editor)
            if name:
                name = name.strip()
                if name in self.mappings:
                    if not messagebox.askyesno("Warning", f"Mapping for '{name}' already exists. Overwrite?", parent=editor):
                        return
                        
                prefix = simpledialog.askstring("Add Mapping", f"Enter Tag Prefix for {name}:", parent=editor)
                if prefix is not None:
                    self.mappings[name] = prefix.strip()
                    self.save_mappings()
                    refresh_tree()

        def edit_mapping():
            selected = tree.selection()
            if selected:
                item = selected[0]
                values = tree.item(item, 'values')
                name = values[0]
                current_prefix = self.mappings.get(name, "")
                
                new_prefix = simpledialog.askstring("Edit Mapping", f"Enter Tag Prefix for {name}:", initialvalue=current_prefix, parent=editor)
                if new_prefix is not None:
                     self.mappings[name] = new_prefix.strip()
                     self.save_mappings()
                     refresh_tree()
            else:
                messagebox.showinfo("Select Item", "Please select a mapping to edit", parent=editor)

        def delete_mapping():
            selected = tree.selection()
            if selected:
                item = selected[0]
                name = tree.item(item, 'values')[0]
                if messagebox.askyesno("Delete", f"Remove mapping for {name}?", parent=editor):
                    del self.mappings[name]
                    self.save_mappings()
                    refresh_tree()
            else:
                 messagebox.showinfo("Select Item", "Please select a mapping to delete", parent=editor)

        # Buttons Frame
        btn_frame = ttk.Frame(content_frame, padding="0 10 0 0")
        btn_frame.pack(fill='x')
        
        ttk.Button(btn_frame, text="➕ Add Tag", style="TagManager.TButton", command=add_mapping).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="✏️ Edit", style="TagManager.TButton", command=edit_mapping).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🗑️ Delete", style="TagManager.TButton", command=delete_mapping).pack(side='left', padx=2)
        
        ttk.Button(btn_frame, text="Close", command=editor.destroy).pack(side='right', padx=2)
        
        # Initial focus
        editor.focus_set()
