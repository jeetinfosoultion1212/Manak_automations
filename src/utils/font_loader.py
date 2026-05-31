import os
import sys
import ctypes
from ctypes import wintypes

def load_font(font_path):
    """
    Loads a font file securely into the system memory for the current process.
    Allows using the font in Tkinter without administrator installation on Windows.
    
    Args:
        font_path (str): Absolute path to the .ttf or .otf file
        
    Returns:
        bool: True if loaded successfully, False otherwise
    """
    if not os.path.exists(font_path):
        print(f"Font file not found: {font_path}")
        return False
        
    try:
        # Check platform
        if sys.platform != 'win32':
            # For Linux/Mac, usually requires OS-level installation or complex path handling
            # This implementation focuses on Windows support via GDI32
            return False
            
        # Windows API constants
        FR_PRIVATE = 0x10
        FR_NOT_ENUM = 0x20
        
        # Load the font resource into the session's private font table
        # This makes it available to the process but not to other applications
        path_buf = ctypes.create_unicode_buffer(font_path)
        add_font_resource_ex = ctypes.windll.gdi32.AddFontResourceExW
        
        # Returns number of fonts added (should be > 0)
        num_fonts_added = add_font_resource_ex(path_buf, FR_PRIVATE, 0)
        
        if num_fonts_added > 0:
            print(f"Successfully loaded font: {os.path.basename(font_path)}")
            return True
        else:
            print(f"Failed to load font resource: {font_path}")
            return False
            
    except Exception as e:
        print(f"Error loading font {font_path}: {e}")
        return False

def load_fonts_from_directory(directory="fonts"):
    """
    Load all .ttf and .otf fonts from a specified directory.
    
    Args:
        directory (str): Relative or absolute path to fonts directory
        
    Returns:
        int: Number of fonts successfully loaded
    """
    count = 0
    
    # Resolve absolute path if relative
    if not os.path.isabs(directory):
        # Try relative to script execution or base path depending on context
        base_path = os.path.dirname(os.path.abspath(__file__))
        # Go up one level from utils to src, then to fonts if needed
        # Assuming directory is 'fonts' adjacent to src or inside src
        # Let's try finding it relative to main src directory
        src_path = os.path.dirname(base_path)
        possible_paths = [
            os.path.join(src_path, directory),
            os.path.join(os.path.dirname(src_path), directory)
        ]
        
        target_path = None
        for p in possible_paths:
            if os.path.exists(p):
                target_path = p
                break
                
        if not target_path:
            # Create if doesn't exist in src root
            target_path = os.path.join(src_path, directory)
            try:
                os.makedirs(target_path, exist_ok=True)
            except:
                pass
            return 0
    else:
        target_path = directory
        
    if not os.path.exists(target_path):
        try:
            os.makedirs(target_path, exist_ok=True)
        except:
            pass
        return 0
        
    # Iterate files
    for filename in os.listdir(target_path):
        if filename.lower().endswith(('.ttf', '.otf')):
            full_path = os.path.join(target_path, filename)
            if load_font(full_path):
                count += 1
                
    return count
