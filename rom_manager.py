#!/usr/bin/env python3
"""
ROM Librarian - Retro Gaming Collection Organizer
A tool for managing, renaming, and organizing ROM files
"""

import os
import re
import time
import gc
import json
import shutil
import threading
import hashlib
import glob as glob_module
import ctypes
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import List, Tuple, Dict
from datetime import datetime
import xml.etree.ElementTree as ET
import zlib

# Try to import ttkbootstrap for theming
try:
    import ttkbootstrap as ttk_boot
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    TTKBOOTSTRAP_AVAILABLE = False

# App version
VERSION = "1.1.2"

# Config file for storing user preferences
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian_config.json")
HASH_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian_hash_cache.json")
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cartridge.ico")

def set_window_icon(window):
    """Set the app icon on a window"""
    try:
        if os.path.exists(ICON_PATH):
            window.iconbitmap(ICON_PATH)
    except:
        pass

def load_config():
    """Load configuration from file"""
    defaults = {"theme": "light"}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**defaults, **config}
    except:
        pass
    return defaults

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except:
        pass

def load_hash_cache():
    """Load hash cache from file"""
    try:
        if os.path.exists(HASH_CACHE_FILE):
            with open(HASH_CACHE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_hash_cache(cache):
    """Save hash cache to file"""
    try:
        with open(HASH_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass

# Windows API constants for sleep prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# ROM file filtering constants
ROM_EXTENSIONS_WHITELIST = {
    # Cartridge-based systems
    '.nds', '.gba', '.gbc', '.gb', '.sfc', '.smc', '.nes', '.n64', '.z64', '.v64',
    '.md', '.smd', '.gen', '.gg', '.sms', '.pce', '.ngp', '.ngc', '.ws', '.wsc',
    # Disc-based systems
    '.bin', '.iso', '.cue', '.chd', '.cso', '.gcm', '.rvz', '.wbfs', '.wad',
    # Modern systems
    '.dol', '.elf', '.nsp', '.xci', '.nca',
    # Archives
    '.zip', '.7z', '.rar', '.gz'
}

FILE_EXTENSIONS_BLACKLIST = {
    # Images
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.ico',
    # Documents
    '.pdf', '.txt', '.doc', '.docx', '.rtf', '.md',
    # Executables
    '.exe', '.dll', '.bat', '.sh', '.msi',
    # Media
    '.mp4', '.avi', '.mkv', '.mp3', '.wav', '.flac',
    # Metadata
    '.xml', '.json', '.dat', '.ini', '.cfg',
    # Other
    '.db', '.tmp', '.log', '.bak'
}

EXCLUDED_FOLDER_NAMES = {
    'media', 'screenshots', 'manuals', 'boxart', 'box art', 'images',
    'saves', 'savedata', 'docs', 'documentation', 'videos'
}


class CenteredDialog:
    """Base class for centered dialogs"""
    def __init__(self, parent, title, message, dialog_type="info", width=450, height=200):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        set_window_icon(self.dialog)

        # Main container
        container = tk.Frame(self.dialog, padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Check if message is long (needs scrolling)
        line_count = message.count('\n') + 1
        if line_count > 15 or len(message) > 500:
            # Use scrollable text widget for long messages
            self.dialog.resizable(True, True)
            text_frame = tk.Frame(container)
            text_frame.pack(pady=(0, 20), fill=tk.BOTH, expand=True)

            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                                 height=20, width=60, font=("TkDefaultFont", 9))
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            text_widget.insert("1.0", message)
            text_widget.config(state=tk.DISABLED)
            scrollbar.config(command=text_widget.yview)
        else:
            # Use simple label for short messages
            self.dialog.resizable(False, False)
            msg_label = tk.Label(container, text=message, wraplength=width-60,
                                justify=tk.CENTER, anchor=tk.CENTER)
            msg_label.pack(pady=(0, 20), fill=tk.BOTH, expand=True)

        # Button container
        btn_container = tk.Frame(container)
        btn_container.pack()

        # Add buttons based on type
        if dialog_type in ["info", "error", "warning"]:
            ok_btn = tk.Button(btn_container, text="OK", command=self._on_ok,
                             width=12, height=1)
            ok_btn.pack()
            ok_btn.focus_set()
            self.dialog.bind('<Return>', lambda e: self._on_ok())

        elif dialog_type == "yesno":
            yes_btn = tk.Button(btn_container, text="Yes", command=self._on_yes,
                              width=12, height=1)
            yes_btn.pack(side=tk.LEFT, padx=5)

            no_btn = tk.Button(btn_container, text="No", command=self._on_no,
                             width=12, height=1)
            no_btn.pack(side=tk.LEFT, padx=5)

            yes_btn.focus_set()
            self.dialog.bind('<Return>', lambda e: self._on_yes())
            self.dialog.bind('<Escape>', lambda e: self._on_no())

        # Center the dialog
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)

        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.grab_set()

    def _on_ok(self):
        self.result = True
        self.dialog.destroy()

    def _on_yes(self):
        self.result = True
        self.dialog.destroy()

    def _on_no(self):
        self.result = False
        self.dialog.destroy()

    def show(self):
        """Show dialog and wait for response"""
        self.dialog.wait_window()
        return self.result


def show_info(parent, title, message):
    """Show an info dialog centered on parent"""
    dialog = CenteredDialog(parent, title, message, dialog_type="info")
    return dialog.show()


def show_error(parent, title, message):
    """Show an error dialog centered on parent"""
    dialog = CenteredDialog(parent, title, message, dialog_type="error")
    return dialog.show()


def show_warning(parent, title, message):
    """Show a warning dialog centered on parent"""
    dialog = CenteredDialog(parent, title, message, dialog_type="warning")
    return dialog.show()


def ask_yesno(parent, title, message):
    """Show a yes/no dialog centered on parent"""
    dialog = CenteredDialog(parent, title, message, dialog_type="yesno")
    return dialog.show()


class ProgressDialog:
    """Progress dialog for long-running operations"""
    def __init__(self, parent, title, total_items):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        set_window_icon(self.dialog)

        # Set size
        dialog_width = 400
        dialog_height = 120

        self.total_items = total_items
        self.current_item = 0

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status label (centered)
        self.status_label = ttk.Label(main_frame, text="Preparing...", anchor="center")
        self.status_label.pack(pady=(0, 10), fill=tk.X)

        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate',
                                           maximum=total_items, variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Counter label (centered)
        self.counter_label = ttk.Label(main_frame, text="0 / 0", anchor="center")
        self.counter_label.pack(fill=tk.X)

        # Center the dialog relative to parent window
        self.dialog.update_idletasks()

        # Get parent window position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Calculate center position
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self.dialog.grab_set()

    def update(self, current, filename):
        """Update progress - safe to call from any thread"""
        self.current_item = current
        self.dialog.after(0, self._update_ui, current, filename)

    def _update_ui(self, current, filename):
        """Update UI elements - must run in main thread"""
        self.progress_var.set(current)
        self.counter_label.config(text=f"{current} / {self.total_items}")

        # Truncate long filenames
        if len(filename) > 45:
            display_name = filename[:42] + "..."
        else:
            display_name = filename
        self.status_label.config(text=f"Processing: {display_name}")

    def close(self):
        """Close the dialog - safe to call from any thread"""
        self.dialog.after(0, self._close_ui)

    def _close_ui(self):
        """Close UI - must run in main thread"""
        self.dialog.grab_release()
        self.dialog.destroy()


class ToolTip:
    """Create a tooltip for a widget with delayed display"""
    def __init__(self, widget, text, delay=2000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.schedule_id = None

        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        """Schedule tooltip to appear after delay"""
        self.schedule_id = self.widget.after(self.delay, self.show_tooltip)

    def on_leave(self, event=None):
        """Cancel scheduled tooltip and hide if visible"""
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None
        self.hide_tooltip()

    def show_tooltip(self):
        """Display the tooltip"""
        if self.tooltip_window:
            return

        # Position tooltip near the widget
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("tahoma", "8", "normal"), padx=5, pady=3)
        label.pack()

    def hide_tooltip(self):
        """Hide the tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def parse_dat_file(dat_path):
    """
    Parse a DAT file (No-Intro XML format) and return a dictionary of game entries.
    Returns: {crc32: game_name, md5: game_name, sha1: game_name}
    """
    hash_to_name = {}

    try:
        tree = ET.parse(dat_path)
        root = tree.getroot()

        # Iterate through all <game> elements
        for game in root.findall('game'):
            game_name = game.get('name', '')
            if not game_name:
                continue

            # Get all <rom> entries for this game
            for rom in game.findall('rom'):
                # Get hash values
                crc = rom.get('crc', '').lower()
                md5 = rom.get('md5', '').lower()
                sha1 = rom.get('sha1', '').lower()

                # Store mappings for each available hash
                if crc:
                    hash_to_name[crc] = game_name
                if md5:
                    hash_to_name[md5] = game_name
                if sha1:
                    hash_to_name[sha1] = game_name

        return hash_to_name

    except Exception as e:
        raise Exception(f"Failed to parse DAT file: {str(e)}")


def update_gamelist_xml(folder_path, rename_map):
    """
    Update gamelist.xml file with renamed paths.
    rename_map is a dict of {old_path: new_path}
    Only updates <path> tags, leaves everything else (images, metadata) unchanged.
    """
    gamelist_path = os.path.join(folder_path, "gamelist.xml")

    if not os.path.exists(gamelist_path):
        return 0  # No gamelist.xml found, nothing to update

    try:
        # Parse the XML file
        tree = ET.parse(gamelist_path)
        root = tree.getroot()

        updates_made = 0

        # Find all <game> elements
        for game in root.findall('game'):
            path_element = game.find('path')
            if path_element is not None and path_element.text:
                current_path = path_element.text

                # Check if this path needs updating
                # Path in XML is relative like "./filename.zip"
                # We need to match just the filename part
                for old_path, new_path in rename_map.items():
                    old_filename = os.path.basename(old_path)
                    new_filename = os.path.basename(new_path)

                    # Check if the XML path ends with the old filename
                    if current_path.endswith(old_filename):
                        # Replace just the filename part, keeping the ./ prefix
                        new_xml_path = current_path.replace(old_filename, new_filename)
                        path_element.text = new_xml_path
                        updates_made += 1
                        break

        if updates_made > 0:
            # Backup the original file
            backup_path = gamelist_path + ".backup"
            shutil.copy2(gamelist_path, backup_path)

            # Write the updated XML
            tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)

        return updates_made

    except Exception as e:
        raise Exception(f"Failed to update gamelist.xml: {str(e)}")


def calculate_file_hashes(file_path):
    """
    Calculate CRC32, MD5, and SHA1 hashes for a file.
    For zip files, hashes the first ROM file found inside.
    Returns: (crc32_hex, md5_hex, sha1_hex)
    """
    import zipfile

    crc32_hash = 0
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()

    try:
        # Check if this is a zip file
        if file_path.lower().endswith('.zip') and zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zipf:
                # Get list of files in the zip
                file_list = zipf.namelist()

                # Find the first ROM file (skip directories and non-ROM files)
                rom_file = None
                for fname in file_list:
                    if not fname.endswith('/'):  # Skip directories
                        # Check if it has a ROM extension
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in ROM_EXTENSIONS_WHITELIST:
                            rom_file = fname
                            break

                if not rom_file:
                    raise Exception(f"No ROM file found in zip: {file_path}")

                # Hash the ROM file contents
                with zipf.open(rom_file) as f:
                    while True:
                        chunk = f.read(1024 * 1024)  # Read 1MB at a time
                        if not chunk:
                            break
                        crc32_hash = zlib.crc32(chunk, crc32_hash)
                        md5_hash.update(chunk)
                        sha1_hash.update(chunk)
        else:
            # Regular file - hash directly
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(1024 * 1024)  # Read 1MB at a time
                    if not chunk:
                        break
                    crc32_hash = zlib.crc32(chunk, crc32_hash)
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)

        # Format CRC32 as 8-character hex string
        crc32_hex = format(crc32_hash & 0xFFFFFFFF, '08x')
        md5_hex = md5_hash.hexdigest()
        sha1_hex = sha1_hash.hexdigest()

        return (crc32_hex, md5_hex, sha1_hex)

    except Exception as e:
        raise Exception(f"Failed to hash file {file_path}: {str(e)}")


class ROMManager:
    def __init__(self, root, theme="light"):
        self.root = root
        self.root.title("ROM Librarian")
        self.root.geometry("1200x950")
        self.root.minsize(1100, 900)  # Minimum window size
        self.current_theme = theme

        # Set application icon
        self._set_app_icon()

        # Load config
        self.config = load_config()

        self.current_folder = None
        self.files_data = []  # List of (filename, size, full_path)
        self.undo_history = []  # List of (old_path, new_path) tuples from last rename
        self.sort_reverse = {}  # Track sort direction for each treeview column
        self.last_sort = {}  # Track last sort column and direction for each tree
        self.last_filtered_count = 0  # Track filtered files count for display

        self.setup_ui()

        # Check for updates on startup if enabled (after UI is ready)
        if self.config.get("check_updates_on_startup", True):
            self.root.after(1000, lambda: self.check_for_updates(manual=False))

    def setup_ui(self):
        """Create the main UI layout"""
        # Menu bar
        self.setup_menubar()

        # Top frame - Folder selection (shared across all tabs)
        top_frame = ttk.Frame(self.root, padding="5")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="ROM Folder:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(top_frame, text="Browse...", command=self.browse_folder).pack(side=tk.LEFT)

        # Create tabbed notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Create tabs
        self.setup_rename_tab()
        self.setup_dat_rename_tab()
        self.setup_compression_tab()
        self.setup_m3u_tab()
        self.setup_duplicates_tab()
        self.setup_compare_tab()

        # Bottom status bar (shared across all tabs)
        bottom_frame = ttk.Frame(self.root, padding="5")
        bottom_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Select a folder to begin")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side=tk.LEFT)

    def _set_app_icon(self):
        """Set the application icon"""
        # Delay icon setting to ensure window is fully initialized
        self.root.after(100, lambda: set_window_icon(self.root))

    def setup_menubar(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        self.theme_var = tk.StringVar(value=getattr(self, 'current_theme', 'light'))
        view_menu.add_radiobutton(label="Light Mode", variable=self.theme_var,
                                  value="light", command=lambda: self.change_theme("light"))
        view_menu.add_radiobutton(label="Dark Mode", variable=self.theme_var,
                                  value="dark", command=lambda: self.change_theme("dark"))

        # About menu
        about_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="About", menu=about_menu)
        about_menu.add_command(label="About ROM Librarian", command=self.show_about)

        # Updates menu
        updates_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Updates", menu=updates_menu)
        updates_menu.add_command(label="Check for Updates", command=self.check_for_updates_manual)

        # Check on Startup toggle
        self.check_updates_on_startup_var = tk.BooleanVar(value=self.config.get("check_updates_on_startup", True))
        updates_menu.add_checkbutton(label="Check on Startup",
                                     variable=self.check_updates_on_startup_var,
                                     command=self.toggle_check_on_startup)

    def show_about(self):
        """Show the About dialog with attributions"""
        import webbrowser

        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About ROM Librarian")
        about_dialog.resizable(False, False)
        about_dialog.transient(self.root)
        set_window_icon(about_dialog)

        # Main container
        container = tk.Frame(about_dialog, padx=30, pady=20)
        container.pack(fill=tk.BOTH, expand=True)

        # App name and version
        title_label = tk.Label(container, text="ROM Librarian", font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 5))

        subtitle_label = tk.Label(container, text="Retro Gaming Collection Organizer",
                                  font=("TkDefaultFont", 10, "italic"), foreground="#666666")
        subtitle_label.pack(pady=(0, 2))

        author_label = tk.Label(container, text="by RobotWizard",
                                font=("TkDefaultFont", 9), foreground="#666666")
        author_label.pack(pady=(0, 15))

        # Credits section
        credits_frame = tk.Frame(container)
        credits_frame.pack(fill=tk.X, pady=(0, 15))

        # Claude attribution
        tk.Label(credits_frame, text="Developed with Claude Code",
                font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
        tk.Label(credits_frame, text="by Anthropic",
                font=("TkDefaultFont", 9), foreground="#666666").pack(anchor=tk.W, pady=(0, 10))

        # Icon attribution
        tk.Label(credits_frame, text="App Icon",
                font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

        icon_link = tk.Label(credits_frame,
                            text="Game cartridge icons created by Creatype - Flaticon",
                            font=("TkDefaultFont", 9), foreground="#0066cc", cursor="hand2")
        icon_link.pack(anchor=tk.W)
        icon_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.flaticon.com/free-icons/game-cartridge"))
        icon_link.bind("<Enter>", lambda e: icon_link.config(font=("TkDefaultFont", 9, "underline")))
        icon_link.bind("<Leave>", lambda e: icon_link.config(font=("TkDefaultFont", 9)))

        # Version number
        version_label = tk.Label(container, text=f"Version {VERSION}",
                                 font=("TkDefaultFont", 8), foreground="#999999")
        version_label.pack(pady=(10, 0))

        # OK button
        ok_btn = tk.Button(container, text="OK", command=about_dialog.destroy, width=10)
        ok_btn.pack(pady=(10, 0))
        ok_btn.focus_set()
        about_dialog.bind('<Return>', lambda e: about_dialog.destroy())
        about_dialog.bind('<Escape>', lambda e: about_dialog.destroy())

        # Center the dialog
        about_dialog.update_idletasks()
        width = about_dialog.winfo_reqwidth()
        height = about_dialog.winfo_reqheight()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        about_dialog.geometry(f"+{x}+{y}")
        about_dialog.grab_set()

    def check_for_updates_manual(self):
        """Check for updates manually (from menu)"""
        self.check_for_updates(manual=True)

    def toggle_check_on_startup(self):
        """Toggle the check for updates on startup setting"""
        enabled = self.check_updates_on_startup_var.get()
        self.config["check_updates_on_startup"] = enabled
        save_config(self.config)

    def check_for_updates(self, manual=False):
        """Check for updates from GitHub releases"""
        import urllib.request
        import json

        def check_updates_worker():
            try:
                url = "https://api.github.com/repos/Roboall93/ROM-Librarian/releases/latest"
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'ROM-Librarian')

                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data.get("tag_name", "").lstrip("v")
                    release_url = data.get("html_url", "")
                    release_notes = data.get("body", "")

                    # Compare versions
                    if self.is_newer_version(latest_version, VERSION):
                        self.root.after(0, lambda: self.show_update_dialog(latest_version, release_url, release_notes))
                    elif manual:
                        self.root.after(0, lambda: show_info(self.root, "No Updates",
                                                             f"You're running the latest version ({VERSION})!"))
            except Exception as e:
                if manual:
                    self.root.after(0, lambda: show_error(self.root, "Update Check Failed",
                                                          f"Could not check for updates:\n\n{str(e)}"))

        # Run in background thread
        thread = threading.Thread(target=check_updates_worker, daemon=True)
        thread.start()

    def is_newer_version(self, latest, current):
        """Compare version strings (e.g., '1.2.0' vs '1.1.0')"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]

            # Pad to same length
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)

            return latest_parts > current_parts
        except:
            return False

    def show_update_dialog(self, version, url, notes):
        """Show dialog when update is available"""
        import webbrowser

        dialog = tk.Toplevel(self.root)
        dialog.title("Update Available")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        set_window_icon(dialog)

        container = ttk.Frame(dialog, padding=30)
        container.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(container, text="Update Available!",
                               font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 15))

        # Version info
        info_text = f"A new version of ROM Librarian is available!\n\n"
        info_text += f"Current version: {VERSION}\n"
        info_text += f"Latest version: {version}"

        info_label = ttk.Label(container, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 15))

        # Release notes preview
        if notes:
            # Show first 5 lines or first 200 chars, whichever is shorter
            notes_lines = notes.split('\n')
            preview_lines = []
            char_count = 0

            for line in notes_lines[:7]:
                if char_count + len(line) > 250:
                    break
                preview_lines.append(line)
                char_count += len(line)

            notes_preview = '\n'.join(preview_lines)
            if len(notes_lines) > len(preview_lines):
                notes_preview += "\n..."

            notes_header = ttk.Label(container, text="New Features",
                                    font=("TkDefaultFont", 10, "bold"))
            notes_header.pack(anchor=tk.W, pady=(0, 5))

            notes_frame = ttk.Frame(container, relief=tk.SUNKEN, borderwidth=1)
            notes_frame.pack(fill=tk.BOTH, pady=(0, 20))

            # Create text widget for better formatting
            notes_text = tk.Text(notes_frame, height=8, width=50,
                                font=("TkDefaultFont", 9),
                                wrap=tk.WORD, padx=10, pady=10,
                                relief=tk.FLAT, state=tk.NORMAL)
            notes_text.insert(1.0, notes_preview)
            notes_text.config(state=tk.DISABLED)
            notes_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(container)
        button_frame.pack()

        download_btn = ttk.Button(button_frame, text="Download Update",
                                 command=lambda: [webbrowser.open(url), dialog.destroy()],
                                 width=18)
        download_btn.pack(side=tk.LEFT, padx=(0, 10))

        later_btn = ttk.Button(button_frame, text="Later",
                              command=dialog.destroy, width=12)
        later_btn.pack(side=tk.LEFT)

        dialog.bind('<Escape>', lambda e: dialog.destroy())

        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()

    def change_theme(self, theme):
        """Change the application theme"""
        if not TTKBOOTSTRAP_AVAILABLE:
            show_info(self.root, "Theme Change",
                     "Theme switching requires ttkbootstrap.\n\nInstall with: pip install ttkbootstrap\n\nRestart the app after installing.")
            return

        # Save theme preference
        config = load_config()
        config["theme"] = theme
        save_config(config)

        # Map theme names to ttkbootstrap themes
        theme_map = {
            "light": "litera",
            "dark": "darkly"
        }

        try:
            # Change theme using ttkbootstrap
            self.root.style.theme_use(theme_map.get(theme, "litera"))
            self.current_theme = theme
        except Exception as e:
            show_info(self.root, "Theme Change",
                     f"Theme will be applied on next restart.\n\nError: {e}")

    def setup_rename_tab(self):
        """Setup the rename tab"""
        rename_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(rename_tab, text="Rename")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(rename_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Preview filename changes before applying. Use presets or custom regex patterns.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Regex rename controls
        rename_frame = ttk.LabelFrame(rename_tab, text="Regex Rename", padding="10")
        rename_frame.pack(fill=tk.X, pady=(0, 10))

        # Pattern input
        pattern_frame = ttk.Frame(rename_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(pattern_frame, text="Pattern:").pack(side=tk.LEFT, padx=(0, 5))
        self.pattern_var = tk.StringVar()
        self.pattern_entry = ttk.Entry(pattern_frame, textvariable=self.pattern_var, width=40)
        self.pattern_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Replacement input
        ttk.Label(pattern_frame, text="Replace with:").pack(side=tk.LEFT, padx=(10, 5))
        self.replacement_var = tk.StringVar()
        self.replacement_entry = ttk.Entry(pattern_frame, textvariable=self.replacement_var, width=20)
        self.replacement_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(pattern_frame, text="Preview", command=self.preview_rename).pack(side=tk.LEFT, padx=(10, 0))

        # Collision handling options
        collision_frame = ttk.Frame(rename_frame)
        collision_frame.pack(fill=tk.X, pady=(5, 5))
        ttk.Label(collision_frame, text="If duplicates occur:").pack(side=tk.LEFT, padx=(0, 5))

        self.collision_strategy = tk.StringVar(value="skip")
        strategies = [
            ("Skip duplicates", "skip"),
            ("Add suffix (_1, _2, etc.)", "suffix"),
            ("Keep first only", "keep_first")
        ]

        for text, value in strategies:
            ttk.Radiobutton(collision_frame, text=text, variable=self.collision_strategy,
                          value=value).pack(side=tk.LEFT, padx=5)

        # Gamelist.xml auto-update option
        gamelist_frame = ttk.Frame(rename_frame)
        gamelist_frame.pack(fill=tk.X, pady=(5, 5))
        self.update_gamelist_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gamelist_frame, text="Auto-Update gamelist.xml (EmulationStation/RetroPie)",
                       variable=self.update_gamelist_var).pack(side=tk.LEFT)

        # Preset patterns
        preset_frame = ttk.Frame(rename_frame)
        preset_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(preset_frame, text="Presets:").pack(side=tk.LEFT, padx=(0, 5))

        presets = [
            ("Remove Region Tags",
             r' \((?!Disc [0-9])[^)]*\)',
             '',
             "Removes (USA), (Japan), (Europe) but keeps (Disc 1)\nExample: 'Game (USA).zip' → 'Game.zip'\nMay need multiple runs"),
            ("Remove ALL Parentheses",
             r' \([^)]*\)',
             '',
             "Nuclear option - removes ALL parentheses content\nExample: 'Game (USA) (Disc 1).zip' → 'Game.zip'"),
            ("Clean Translation Tags",
             r'\[T-En [^\]]*\]',
             '[T-En]',
             "Simplifies translation tags\nExample: 'Game [T-En by HTI v1.00].zip' → 'Game [T-En].zip'"),
            ("Remove Good Dump Tags",
             r' \[[^\]]*[!bt][^\]]*\]',
             '',
             "Removes GoodTools tags like [!] [b] [t]\nExample: 'Game [!].zip' → 'Game.zip'"),
            ("Remove Underscores",
             r'_',
             ' ',
             "Converts underscores to spaces\nExample: 'Game_Name.zip' → 'Game Name.zip'"),
            ("Clean Spaces",
             r'\s+',
             ' ',
             "Collapses multiple spaces into one\nExample: 'Game  Name.zip' → 'Game Name.zip'")
        ]

        for name, pattern, replacement, tooltip_text in presets:
            btn = ttk.Button(preset_frame, text=name,
                           command=lambda p=pattern, r=replacement: self.load_preset(p, r))
            btn.pack(side=tk.LEFT, padx=2)
            # Add tooltip with 1-second delay
            ToolTip(btn, tooltip_text, delay=1000)

        # File list with treeview
        list_frame = ttk.Frame(rename_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree = self.create_scrolled_treeview(list_frame, ("original", "preview", "size"))
        self.tree.heading("original", text="Original Filename",
                         command=lambda: self.sort_treeview(self.tree, "original", False))
        self.tree.heading("preview", text="Preview (after rename)",
                         command=lambda: self.sort_treeview(self.tree, "preview", False))
        self.tree.heading("size", text="Size",
                         command=lambda: self.sort_treeview(self.tree, "size", False))
        self.tree.column("original", width=400)
        self.tree.column("preview", width=400)
        self.tree.column("size", width=100)

        # Configure selection colors (blue for user selection)
        style = ttk.Style()
        style.map('Treeview',
                  background=[('selected', '#0078d7')],  # Blue background for selection
                  foreground=[('selected', 'white')])     # White text for selection

        self.setup_custom_selection(self.tree)

        # Bottom frame - Action buttons
        button_frame = ttk.Frame(rename_tab)
        button_frame.pack(fill=tk.X)

        # Left-aligned selection buttons
        ttk.Button(button_frame, text="Select All", command=self.rename_select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Deselect All", command=self.rename_deselect_all).pack(side=tk.LEFT)

        # Right-aligned action buttons
        self.rename_button = ttk.Button(button_frame, text="Execute Rename",
                                       command=self.execute_rename, state="disabled")
        self.rename_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.rename_selected_button = ttk.Button(button_frame, text="Rename Selected",
                                                command=self.rename_selected, state="disabled")
        self.rename_selected_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.undo_button = ttk.Button(button_frame, text="Undo Last Rename",
                                     command=self.undo_rename, state="disabled")
        self.undo_button.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(button_frame, text="Refresh", command=self.reload_files).pack(side=tk.RIGHT)

    def setup_dat_rename_tab(self):
        """Setup the DAT rename tab for bulk renaming using DAT files"""
        dat_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(dat_tab, text="DAT Rename")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(dat_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Bulk rename ROMs based on No-Intro DAT files. ROMs are matched by hash and renamed automatically.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # === DAT FILE SELECTION ===
        dat_frame = ttk.LabelFrame(dat_tab, text="DAT File", padding="10")
        dat_frame.pack(fill=tk.X, pady=(0, 10))

        dat_select_frame = ttk.Frame(dat_frame)
        dat_select_frame.pack(fill=tk.X)

        ttk.Label(dat_select_frame, text="Selected DAT:").pack(side=tk.LEFT, padx=(0, 5))
        self.dat_file_var = tk.StringVar(value="No DAT file selected")
        ttk.Entry(dat_select_frame, textvariable=self.dat_file_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dat_select_frame, text="Browse DAT...", command=self.browse_dat_file).pack(side=tk.LEFT)

        # === SCAN CONTROLS ===
        scan_frame = ttk.LabelFrame(dat_tab, text="Scan & Match", padding="10")
        scan_frame.pack(fill=tk.X, pady=(0, 10))

        # Scan buttons
        scan_button_frame = ttk.Frame(scan_frame)
        scan_button_frame.pack(fill=tk.X, pady=(0, 10))

        self.dat_start_scan_button = ttk.Button(scan_button_frame, text="Start Scan & Match", command=self.start_dat_scan)
        self.dat_start_scan_button.pack(side=tk.LEFT, padx=(0, 5))

        self.dat_stop_scan_button = ttk.Button(scan_button_frame, text="Stop Scan", command=self.stop_dat_scan, state="disabled")
        self.dat_stop_scan_button.pack(side=tk.LEFT)

        # Status label (below buttons)
        status_frame = ttk.Frame(scan_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        self.dat_scan_status_var = tk.StringVar(value="Select a folder and DAT file, then click 'Start Scan & Match'")
        ttk.Label(status_frame, textvariable=self.dat_scan_status_var).pack(anchor=tk.W)

        # Progress bar
        progress_frame = ttk.Frame(scan_frame)
        progress_frame.pack(fill=tk.X)

        self.dat_progress_var = tk.IntVar(value=0)
        self.dat_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', variable=self.dat_progress_var)
        self.dat_progress_bar.pack(fill=tk.X)

        # Gamelist.xml auto-update option
        dat_gamelist_frame = ttk.Frame(scan_frame)
        dat_gamelist_frame.pack(fill=tk.X, pady=(10, 0))
        self.dat_update_gamelist_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dat_gamelist_frame, text="Auto-Update gamelist.xml (EmulationStation/RetroPie)",
                       variable=self.dat_update_gamelist_var).pack(side=tk.LEFT)

        # === RESULTS TREE ===
        results_frame = ttk.LabelFrame(dat_tab, text="Matched Files", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Tree with scrollbar
        tree_container = ttk.Frame(results_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_container)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.dat_results_tree = ttk.Treeview(tree_container,
                                             columns=('current', 'new', 'status'),
                                             show='headings',
                                             yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.dat_results_tree.yview)

        self.dat_results_tree.heading('current', text='Current Name',
                                      command=lambda: self.sort_treeview(self.dat_results_tree, "current", False))
        self.dat_results_tree.heading('new', text='New Name (from DAT)',
                                      command=lambda: self.sort_treeview(self.dat_results_tree, "new", False))
        self.dat_results_tree.heading('status', text='Status',
                                      command=lambda: self.sort_treeview(self.dat_results_tree, "status", False))

        self.dat_results_tree.column('current', width=300)
        self.dat_results_tree.column('new', width=300)
        self.dat_results_tree.column('status', width=100)

        self.dat_results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure tag colors for matches (darker grey for visibility)
        # Dark mode friendly colors
        self.dat_results_tree.tag_configure("match", background="#505050")  # Darker grey for matches
        self.dat_results_tree.tag_configure("already_correct", background="#2d5016")  # Dark green
        self.dat_results_tree.tag_configure("unmatched", background="#3d3d00")  # Dark yellow/brown
        self.dat_results_tree.tag_configure("error", background="#5c1a1a")  # Dark red

        # Configure selection colors (blue for user selection)
        style = ttk.Style()
        style.map('Treeview',
                  background=[('selected', '#0078d7')],  # Blue background for selection
                  foreground=[('selected', 'white')])     # White text for selection

        # Setup custom selection behavior (click and drag)
        self.setup_custom_selection(self.dat_results_tree)

        # Summary label
        self.dat_summary_var = tk.StringVar(value="")
        ttk.Label(results_frame, textvariable=self.dat_summary_var, font=("TkDefaultFont", 9)).pack(anchor=tk.W, pady=(5, 0))

        # === ACTION BUTTONS ===
        action_frame = ttk.Frame(dat_tab)
        action_frame.pack(fill=tk.X)

        # Left-aligned selection buttons
        ttk.Button(action_frame, text="Select All", command=self.dat_select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Deselect All", command=self.dat_deselect_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Refresh", command=self.dat_refresh_scan).pack(side=tk.LEFT)

        # Right-aligned buttons (matching Rename tab layout)
        self.dat_execute_button = ttk.Button(action_frame, text="Execute Rename", command=self.execute_dat_rename, state="disabled")
        self.dat_execute_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.dat_rename_selected_button = ttk.Button(action_frame, text="Rename Selected", command=self.rename_selected_dat, state="disabled")
        self.dat_rename_selected_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.dat_undo_button = ttk.Button(action_frame, text="Undo Last Rename", command=self.undo_dat_rename, state="disabled")
        self.dat_undo_button.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(action_frame, text="Clear Results", command=self.clear_dat_results).pack(side=tk.RIGHT)

        # Initialize state variables
        self.dat_file_path = None
        self.dat_hash_map = {}
        self.dat_scan_running = False
        self.dat_scan_cancelled = False
        self.dat_matched_files = []  # List of (current_path, new_name, status)
        self.dat_undo_history = []  # List of (new_path, original_path) tuples

    def setup_compression_tab(self):
        """Setup the compression tab with dual-pane layout"""
        compression_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(compression_tab, text="Compression")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(compression_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Compress ROMs to save space. Extract archives when needed.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Top control frame - File extension selector
        control_frame = ttk.Frame(compression_tab)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="File Extension:").pack(side=tk.LEFT, padx=(0, 5))
        self.compress_ext_var = tk.StringVar(value="*.gba")
        ext_entry = ttk.Entry(control_frame, textvariable=self.compress_ext_var, width=15)
        ext_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Common extension quick buttons
        ttk.Label(control_frame, text="Quick:").pack(side=tk.LEFT, padx=(10, 5))
        common_exts = ["*.gba", "*.gbc", "*.gb", "*.smc", "*.sfc", "*.nes", "*.md", "*.n64"]
        for ext in common_exts:
            btn = ttk.Button(control_frame, text=ext.replace("*.", "").upper(), width=5,
                           command=lambda e=ext: self.set_compression_extension(e))
            btn.pack(side=tk.LEFT, padx=2)

        # Dual-pane container
        panes_frame = ttk.Frame(compression_tab)
        panes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        panes_frame.grid_columnconfigure(0, weight=1)
        panes_frame.grid_columnconfigure(1, weight=1)
        panes_frame.grid_rowconfigure(0, weight=1)

        # === LEFT PANE: Uncompressed Files ===
        left_pane = ttk.LabelFrame(panes_frame, text="Uncompressed Files", padding="10")
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Left pane list
        left_list_frame = ttk.Frame(left_pane)
        left_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.uncompressed_tree = self.create_scrolled_treeview(left_list_frame, ("filename", "size", "status"))
        self.uncompressed_tree.heading("filename", text="Filename",
                                       command=lambda: self.sort_treeview(self.uncompressed_tree, "filename", False))
        self.uncompressed_tree.heading("size", text="Size",
                                       command=lambda: self.sort_treeview(self.uncompressed_tree, "size", False))
        self.uncompressed_tree.heading("status", text="Status",
                                       command=lambda: self.sort_treeview(self.uncompressed_tree, "status", False))
        self.uncompressed_tree.column("filename", width=250)
        self.uncompressed_tree.column("size", width=80)
        self.uncompressed_tree.column("status", width=70)
        self.setup_custom_selection(self.uncompressed_tree)

        # Left pane buttons
        left_btn_frame = ttk.Frame(left_pane)
        left_btn_frame.pack(fill=tk.X)

        self.delete_originals_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left_btn_frame, text="Delete originals after compression",
                       variable=self.delete_originals_var).pack(anchor=tk.W, pady=(0, 5))

        left_btns = ttk.Frame(left_btn_frame)
        left_btns.pack(fill=tk.X)
        ttk.Button(left_btns, text="Compress Selected",
                  command=self.compress_selected_roms).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="Compress All",
                  command=self.compress_all_roms).pack(side=tk.LEFT, padx=(0, 5))
        self.delete_archived_btn = ttk.Button(left_btns, text="Delete Archived Only",
                  command=self.delete_archived_roms, state="disabled")
        self.delete_archived_btn.pack(side=tk.LEFT)

        # === RIGHT PANE: Compressed Archives ===
        right_pane = ttk.LabelFrame(panes_frame, text="Compressed Archives", padding="10")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Right pane list
        right_list_frame = ttk.Frame(right_pane)
        right_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.compressed_tree = self.create_scrolled_treeview(right_list_frame, ("filename", "size"))
        self.compressed_tree.heading("filename", text="Filename",
                                     command=lambda: self.sort_treeview(self.compressed_tree, "filename", False))
        self.compressed_tree.heading("size", text="Size",
                                     command=lambda: self.sort_treeview(self.compressed_tree, "size", False))
        self.compressed_tree.column("filename", width=300)
        self.compressed_tree.column("size", width=100)
        self.setup_custom_selection(self.compressed_tree)

        # Right pane buttons
        right_btn_frame = ttk.Frame(right_pane)
        right_btn_frame.pack(fill=tk.X)

        self.delete_archives_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(right_btn_frame, text="Delete archives after extraction",
                       variable=self.delete_archives_var).pack(anchor=tk.W, pady=(0, 5))

        right_btns = ttk.Frame(right_btn_frame)
        right_btns.pack(fill=tk.X)
        ttk.Button(right_btns, text="Extract Selected",
                  command=self.extract_selected_zips).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_btns, text="Extract All",
                  command=self.extract_all_zips).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_btns, text="Delete Selected",
                  command=self.delete_selected_zips).pack(side=tk.LEFT)

        # Status bar for compression tab
        self.compression_status_var = tk.StringVar(value="")
        ttk.Label(compression_tab, textvariable=self.compression_status_var).pack(fill=tk.X)

    def setup_m3u_tab(self):
        """Setup the M3U playlist creation tab"""
        m3u_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(m3u_tab, text="M3U Creation")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(m3u_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))

        guidance_text = (
            "M3U files are playlist files used by emulators to handle multi-disc games. "
            "Instead of showing each disc separately, the emulator sees one game entry and can swap discs automatically.\n\n"
            "This tool scans for multi-disc ROMs (files with 'Disc 1', 'Disc 2', etc.), creates an M3U playlist file "
            "for each game, and moves the disc files into a '.hidden' folder to keep your game list clean."
        )
        guidance_label = ttk.Label(guidance_frame, text=guidance_text,
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666", wraplength=900, justify=tk.LEFT)
        guidance_label.pack(anchor=tk.W)

        # === SCAN SETTINGS ===
        settings_frame = ttk.LabelFrame(m3u_tab, text="Scan Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Scan mode
        scan_mode_frame = ttk.Frame(settings_frame)
        scan_mode_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scan_mode_frame, text="Scan Mode:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

        self.m3u_scan_mode = tk.StringVar(value="folder_only")

        rb1 = ttk.Radiobutton(scan_mode_frame, text="This folder only",
                              variable=self.m3u_scan_mode, value="folder_only")
        rb1.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb1, "Scan only the selected ROM folder")

        rb2 = ttk.Radiobutton(scan_mode_frame, text="Include subfolders",
                              variable=self.m3u_scan_mode, value="with_subfolders")
        rb2.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb2, "Scan the selected folder and all subdirectories")

        # Scan button
        scan_btn_frame = ttk.Frame(settings_frame)
        scan_btn_frame.pack(fill=tk.X)

        self.m3u_scan_btn = ttk.Button(scan_btn_frame, text="Scan for Multi-Disc Games",
                                       command=self.scan_for_multi_disc)
        self.m3u_scan_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.m3u_scan_status_var = tk.StringVar(value="Select a ROM folder and click scan")
        ttk.Label(scan_btn_frame, textvariable=self.m3u_scan_status_var).pack(side=tk.LEFT)

        # === RESULTS DISPLAY ===
        results_frame = ttk.LabelFrame(m3u_tab, text="Multi-Disc Games Found", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Summary
        self.m3u_summary_var = tk.StringVar(value="No scan performed yet")
        ttk.Label(results_frame, textvariable=self.m3u_summary_var,
                  font=("TkDefaultFont", 9)).pack(anchor=tk.W, pady=(0, 5))

        # Results tree
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.m3u_tree = self.create_scrolled_treeview(
            tree_frame,
            ("select", "game_name", "disc_count", "location", "status"),
            show="headings"
        )
        self.m3u_tree.heading("select", text="☑")
        self.m3u_tree.heading("game_name", text="Game Name",
                              command=lambda: self.sort_treeview(self.m3u_tree, "game_name", False))
        self.m3u_tree.heading("disc_count", text="Discs",
                              command=lambda: self.sort_treeview(self.m3u_tree, "disc_count", False))
        self.m3u_tree.heading("location", text="Location",
                              command=lambda: self.sort_treeview(self.m3u_tree, "location", False))
        self.m3u_tree.heading("status", text="Status",
                              command=lambda: self.sort_treeview(self.m3u_tree, "status", False))
        self.m3u_tree.column("select", width=30, anchor="center")
        self.m3u_tree.column("game_name", width=350)
        self.m3u_tree.column("disc_count", width=60, anchor="center")
        self.m3u_tree.column("location", width=300)
        self.m3u_tree.column("status", width=120)

        # Configure tag colors - only highlight done/error, ready uses default background
        if TTKBOOTSTRAP_AVAILABLE and hasattr(self.root, 'style'):
            colors = self.root.style.colors
            self.m3u_tree.tag_configure("done", background=colors.success)
            self.m3u_tree.tag_configure("error", background=colors.danger, foreground="white")
        else:
            self.m3u_tree.tag_configure("done", background="#d4edda")
            self.m3u_tree.tag_configure("error", background="#f8d7da")

        # Bind click for checkbox toggle
        self.m3u_tree.bind("<Button-1>", self._on_m3u_tree_click)

        # Initialize selection tracking
        self.m3u_selection = {}  # item_id -> True/False
        self.m3u_disc_data = {}  # item_id -> {'game_name': str, 'discs': [(disc_num, filepath)], 'folder': str}

        # === ACTIONS ===
        actions_frame = ttk.Frame(m3u_tab)
        actions_frame.pack(fill=tk.X)

        # Selection buttons
        select_frame = ttk.Frame(actions_frame)
        select_frame.pack(fill=tk.X, pady=(0, 10))

        self.m3u_select_all_btn = ttk.Button(select_frame, text="Select All",
                                             command=self.m3u_select_all)
        self.m3u_select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.m3u_deselect_all_btn = ttk.Button(select_frame, text="Deselect All",
                                               command=self.m3u_deselect_all)
        self.m3u_deselect_all_btn.pack(side=tk.LEFT, padx=(0, 20))

        # Create M3U button
        self.m3u_create_btn = ttk.Button(select_frame, text="Create M3U Files for Selected",
                                         command=self.create_m3u_files, state="disabled")
        self.m3u_create_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.m3u_create_btn,
                "Creates .m3u playlist files and moves disc files to .hidden folder")

        # Info label
        info_label = ttk.Label(select_frame,
                               text="Creates .m3u files and moves discs to .hidden/ folder",
                               font=("TkDefaultFont", 8), foreground="#666666")
        info_label.pack(side=tk.LEFT)

    def _on_m3u_tree_click(self, event):
        """Handle click on M3U tree to toggle checkbox"""
        item = self.m3u_tree.identify_row(event.y)
        if not item:
            return

        column = self.m3u_tree.identify_column(event.x)

        # Only handle checkbox column clicks
        if column == "#1":
            current_state = self.m3u_selection.get(item, True)
            self.m3u_selection[item] = not current_state

            # Update checkbox display
            new_checkbox = "☐" if current_state else "☑"
            self.m3u_tree.set(item, "select", new_checkbox)

            self._update_m3u_create_button()
            return "break"

    def _update_m3u_create_button(self):
        """Update the create button based on selection"""
        selected_count = sum(1 for v in self.m3u_selection.values() if v)
        if selected_count > 0:
            self.m3u_create_btn.config(state="normal",
                                       text=f"Create M3U Files for Selected ({selected_count})")
        else:
            self.m3u_create_btn.config(state="disabled",
                                       text="Create M3U Files for Selected")

    def m3u_select_all(self):
        """Select all items in M3U tree"""
        for item in self.m3u_tree.get_children():
            # Only select items that aren't already done
            status = self.m3u_tree.set(item, "status")
            if status != "Done":
                self.m3u_selection[item] = True
                self.m3u_tree.set(item, "select", "☑")
        self._update_m3u_create_button()

    def m3u_deselect_all(self):
        """Deselect all items in M3U tree"""
        for item in self.m3u_tree.get_children():
            self.m3u_selection[item] = False
            self.m3u_tree.set(item, "select", "☐")
        self._update_m3u_create_button()

    def scan_for_multi_disc(self):
        """Scan for multi-disc games"""
        if not self.current_folder or not os.path.exists(self.current_folder):
            show_warning(self.root, "No Folder",
                        "Please select a ROM folder first using the Browse button at the top")
            return

        # Clear previous results
        for item in self.m3u_tree.get_children():
            self.m3u_tree.delete(item)
        self.m3u_selection.clear()
        self.m3u_disc_data.clear()

        self.m3u_scan_status_var.set("Scanning...")
        self.m3u_scan_btn.config(state="disabled")
        self.root.update()

        # Run scan in background
        thread = threading.Thread(target=self._scan_multi_disc_worker, daemon=True)
        thread.start()

    def _scan_multi_disc_worker(self):
        """Background worker for scanning multi-disc games"""
        try:
            scan_mode = self.m3u_scan_mode.get()
            scan_folder = self.current_folder

            # Regex to match disc numbering patterns
            # Matches: (Disc 1), (Disc 2), (Disk 1), (CD 1), (CD1), etc.
            disc_pattern = re.compile(
                r'\s*\((?:Disc|Disk|CD)\s*(\d+)\)',
                re.IGNORECASE
            )

            # Dictionary to group files by base game name and folder
            # Key: (folder_path, base_name) -> [(disc_num, full_path, filename)]
            games_by_folder = {}

            # Scan files
            if scan_mode == "folder_only":
                folders_to_scan = [scan_folder]
            else:
                # Get all folders, explicitly skipping .hidden folders
                folders_to_scan = [scan_folder]
                for root, dirs, _ in os.walk(scan_folder):
                    # Modify dirs in-place to prevent os.walk from descending into .hidden
                    dirs[:] = [d for d in dirs if d != '.hidden']
                    for d in dirs:
                        folders_to_scan.append(os.path.join(root, d))

            for folder in folders_to_scan:
                if not os.path.exists(folder):
                    continue

                try:
                    for item in os.listdir(folder):
                        full_path = os.path.join(folder, item)
                        if not os.path.isfile(full_path):
                            continue

                        # Check if this file has a disc number
                        match = disc_pattern.search(item)
                        if match:
                            disc_num = int(match.group(1))
                            # Get base name (game name without disc number)
                            base_name = disc_pattern.sub('', item).strip()

                            key = (folder, base_name)
                            if key not in games_by_folder:
                                games_by_folder[key] = []
                            games_by_folder[key].append((disc_num, full_path, item))
                except PermissionError:
                    continue

            # Filter to only games with multiple discs
            multi_disc_games = {k: v for k, v in games_by_folder.items() if len(v) >= 2}

            # Update UI in main thread
            self.root.after(0, lambda: self._display_multi_disc_results(multi_disc_games))

        except Exception as e:
            self.root.after(0, lambda: show_error(self.root, "Scan Error", str(e)))
            self.root.after(0, lambda: self.m3u_scan_btn.config(state="normal"))
            self.root.after(0, lambda: self.m3u_scan_status_var.set("Scan failed"))

    def _display_multi_disc_results(self, multi_disc_games):
        """Display multi-disc scan results"""
        self.m3u_scan_btn.config(state="normal")

        if not multi_disc_games:
            self.m3u_summary_var.set("No multi-disc games found")
            self.m3u_scan_status_var.set("Scan complete - no multi-disc games found")
            self.m3u_create_btn.config(state="disabled")
            return

        # Clear and populate tree
        for item in self.m3u_tree.get_children():
            self.m3u_tree.delete(item)

        total_games = 0
        total_discs = 0

        for (folder, base_name), disc_list in sorted(multi_disc_games.items()):
            # Sort discs by disc number
            disc_list.sort(key=lambda x: x[0])

            # Check if M3U already exists
            m3u_path = os.path.join(folder, base_name + ".m3u")
            if os.path.exists(m3u_path):
                status = "Done"
                tag = "done"
                checkbox = "☐"
                selected = False
            else:
                status = "Ready"
                tag = "ready"
                checkbox = "☑"
                selected = True

            # Get game name (strip extension from base_name for display)
            game_display_name = os.path.splitext(base_name)[0]

            # Get relative folder path for display
            if folder == self.current_folder:
                display_folder = "(root)"
            else:
                display_folder = os.path.relpath(folder, self.current_folder)

            item_id = self.m3u_tree.insert("", tk.END, values=(
                checkbox,
                game_display_name,
                str(len(disc_list)),
                display_folder,
                status
            ), tags=(tag,))

            self.m3u_selection[item_id] = selected
            self.m3u_disc_data[item_id] = {
                'game_name': base_name,  # Keep extension for M3U filename
                'discs': disc_list,
                'folder': folder
            }

            total_games += 1
            total_discs += len(disc_list)

        self.m3u_summary_var.set(f"Found {total_games} multi-disc games ({total_discs} total disc files)")
        self.m3u_scan_status_var.set("Scan complete")
        self._update_m3u_create_button()

    def create_m3u_files(self):
        """Create M3U files for selected games"""
        # Get selected items
        items_to_process = []
        for item_id, is_selected in self.m3u_selection.items():
            if is_selected and item_id in self.m3u_disc_data:
                status = self.m3u_tree.set(item_id, "status")
                if status != "Done":
                    items_to_process.append(item_id)

        if not items_to_process:
            show_info(self.root, "No Selection", "No games selected for M3U creation")
            return

        # Confirm
        message = (f"Create M3U files for {len(items_to_process)} game(s)?\n\n"
                   "This will:\n"
                   "• Create a .hidden folder in each game's directory\n"
                   "• Move disc files into the .hidden folder\n"
                   "• Create .m3u playlist files pointing to the discs")

        if not ask_yesno(self.root, "Confirm M3U Creation", message):
            return

        # Create progress dialog
        progress = ProgressDialog(self.root, "Creating M3U Files", len(items_to_process))

        def create_worker():
            created = 0
            failed = 0
            errors = []

            for idx, item_id in enumerate(items_to_process):
                data = self.m3u_disc_data[item_id]
                game_name = data['game_name']
                discs = data['discs']
                folder = data['folder']

                progress.update(idx + 1, os.path.splitext(game_name)[0])

                try:
                    # Create .hidden folder
                    hidden_folder = os.path.join(folder, ".hidden")
                    os.makedirs(hidden_folder, exist_ok=True)

                    # Move disc files and build M3U content
                    m3u_lines = []
                    move_success = True

                    for disc_num, full_path, filename in sorted(discs, key=lambda x: x[0]):
                        # Destination path in .hidden
                        dest_path = os.path.join(hidden_folder, filename)

                        # Move the file
                        try:
                            if os.path.exists(full_path) and not os.path.exists(dest_path):
                                shutil.move(full_path, dest_path)
                            elif os.path.exists(dest_path):
                                # File already in .hidden, that's fine
                                pass
                            else:
                                raise FileNotFoundError(f"Source file not found: {filename}")

                            # Add relative path to M3U
                            m3u_lines.append(f".hidden/{filename}")

                        except Exception as e:
                            errors.append(f"{game_name} - {filename}: {str(e)}")
                            move_success = False
                            break

                    if move_success and m3u_lines:
                        # Create M3U file
                        m3u_filename = os.path.splitext(game_name)[0] + ".m3u"
                        m3u_path = os.path.join(folder, m3u_filename)

                        with open(m3u_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(m3u_lines))
                            f.write('\n')  # Trailing newline

                        created += 1

                        # Update tree item in main thread
                        self.root.after(0, lambda iid=item_id: self._mark_m3u_done(iid))
                    else:
                        failed += 1

                except Exception as e:
                    errors.append(f"{game_name}: {str(e)}")
                    failed += 1
                    # Update tree item as error
                    self.root.after(0, lambda iid=item_id: self._mark_m3u_error(iid))

            progress.close()

            # Show results
            result_msg = f"Created: {created} M3U files"
            if failed > 0:
                result_msg += f"\nFailed: {failed}"
            if errors:
                result_msg += "\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    result_msg += f"\n... and {len(errors) - 10} more"

            self.root.after(0, lambda: show_info(self.root, "M3U Creation Complete", result_msg))
            self.root.after(0, self._update_m3u_create_button)

        # Run in background
        thread = threading.Thread(target=create_worker, daemon=True)
        thread.start()

    def _mark_m3u_done(self, item_id):
        """Mark an M3U tree item as done"""
        self.m3u_tree.set(item_id, "status", "Done")
        self.m3u_tree.set(item_id, "select", "☐")
        self.m3u_tree.item(item_id, tags=("done",))
        self.m3u_selection[item_id] = False

    def _mark_m3u_error(self, item_id):
        """Mark an M3U tree item as error"""
        self.m3u_tree.set(item_id, "status", "Error")
        self.m3u_tree.item(item_id, tags=("error",))

    def setup_duplicates_tab(self):
        """Setup the duplicates detection tab"""
        duplicates_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(duplicates_tab, text="Duplicates")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(duplicates_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Find duplicate files by content (not filename). Keep one copy, delete the rest.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # === TOP SECTION: Scan Settings ===
        scan_settings_frame = ttk.LabelFrame(duplicates_tab, text="Scan Settings", padding="10")
        scan_settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Scan mode and Hash method side by side
        options_frame = ttk.Frame(scan_settings_frame)
        options_frame.pack(fill=tk.X, pady=(5, 5))

        # Left: Scan Mode
        scan_mode_frame = ttk.Frame(options_frame)
        scan_mode_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        ttk.Label(scan_mode_frame, text="Scan Mode:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
        self.scan_mode = tk.StringVar(value="folder_only")

        rb1 = ttk.Radiobutton(scan_mode_frame, text="This folder only",
                       variable=self.scan_mode, value="folder_only")
        rb1.pack(anchor=tk.W)
        ToolTip(rb1, "Scan only files in the selected folder (no subdirectories)")

        rb2 = ttk.Radiobutton(scan_mode_frame, text="This folder + subfolders",
                       variable=self.scan_mode, value="with_subfolders")
        rb2.pack(anchor=tk.W)
        ToolTip(rb2, "Scan the selected folder and all its subdirectories")

        rb3 = ttk.Radiobutton(scan_mode_frame, text="All ROM folders (scans parent directory)",
                       variable=self.scan_mode, value="all_rom_folders")
        rb3.pack(anchor=tk.W)
        ToolTip(rb3, "Scan all folders in the parent directory (useful for multiple ROM collections)")

        # Middle: Hash Method
        hash_method_frame = ttk.Frame(options_frame)
        hash_method_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        ttk.Label(hash_method_frame, text="Hash Method:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
        self.hash_method = tk.StringVar(value="sha1")

        rb_sha1 = ttk.Radiobutton(hash_method_frame, text="SHA1 (recommended)",
                       variable=self.hash_method, value="sha1")
        rb_sha1.pack(anchor=tk.W)
        ToolTip(rb_sha1, "Fast (hardware accelerated) and reliable")

        rb_md5 = ttk.Radiobutton(hash_method_frame, text="MD5 (legacy)",
                       variable=self.hash_method, value="md5")
        rb_md5.pack(anchor=tk.W)
        ToolTip(rb_md5, "For compatibility with older hash databases")

        # Right: File Filter
        filter_frame = ttk.Frame(options_frame)
        filter_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(filter_frame, text="File Filter:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
        self.dup_filter_mode = tk.StringVar(value="rom_only")

        rb_rom = ttk.Radiobutton(filter_frame, text="ROM files only",
                                 variable=self.dup_filter_mode, value="rom_only")
        rb_rom.pack(anchor=tk.W)
        ToolTip(rb_rom, "Only scan ROM and archive files\nIgnores images, documents, saves, etc.")

        rb_all = ttk.Radiobutton(filter_frame, text="All files",
                                 variable=self.dup_filter_mode, value="all_files")
        rb_all.pack(anchor=tk.W)
        ToolTip(rb_all, "Scan all file types without filtering")

        # Scan buttons
        scan_buttons_frame = ttk.Frame(scan_settings_frame)
        scan_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        self.start_scan_btn = ttk.Button(scan_buttons_frame, text="Start Scan", command=self.start_duplicate_scan)
        self.start_scan_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_scan_btn = ttk.Button(scan_buttons_frame, text="Stop Scan", command=self.stop_duplicate_scan, state="disabled")
        self.stop_scan_btn.pack(side=tk.LEFT)

        # Progress section
        progress_frame = ttk.Frame(scan_settings_frame)
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        self.dup_progress_var = tk.IntVar(value=0)
        self.dup_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', variable=self.dup_progress_var, maximum=100)
        self.dup_progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.dup_scan_status_var = tk.StringVar(value="Ready to scan")
        ttk.Label(progress_frame, textvariable=self.dup_scan_status_var).pack(anchor=tk.W)

        # === MIDDLE SECTION: Results Display ===
        results_frame = ttk.LabelFrame(duplicates_tab, text="Duplicate Groups", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Summary header with empty state message
        self.dup_summary_var = tk.StringVar(value="📁 Select a ROM folder above, then click 'Start Scan' to find duplicates")
        summary_label = ttk.Label(results_frame, textvariable=self.dup_summary_var,
                                 font=("TkDefaultFont", 9))
        summary_label.pack(anchor=tk.W, pady=(0, 5))

        # Results tree
        results_tree_frame = ttk.Frame(results_frame)
        results_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.dup_tree = self.create_scrolled_treeview(
            results_tree_frame,
            ("select", "filename", "date", "size", "action", "path"),
            show="tree headings",
            selectmode="none"  # Disable selection highlighting - uses tag colors instead
        )
        self.dup_tree.heading("#0", text="Group")
        self.dup_tree.heading("select", text="☐")
        self.dup_tree.heading("filename", text="Filename")
        self.dup_tree.heading("date", text="Date Modified")
        self.dup_tree.heading("size", text="Size")
        self.dup_tree.heading("action", text="Action")
        self.dup_tree.heading("path", text="Path")
        self.dup_tree.column("#0", width=300)
        self.dup_tree.column("select", width=30, anchor="center")
        self.dup_tree.column("filename", width=250)
        self.dup_tree.column("date", width=120)
        self.dup_tree.column("size", width=80)
        self.dup_tree.column("action", width=60)
        self.dup_tree.column("path", width=300)

        # Configure tag colors (theme-aware if ttkbootstrap available)
        if TTKBOOTSTRAP_AVAILABLE and hasattr(self.root, 'style'):
            colors = self.root.style.colors
            self.dup_tree.tag_configure("keep", background=colors.success)
            self.dup_tree.tag_configure("delete", foreground=colors.danger)
        else:
            self.dup_tree.tag_configure("keep", background="#d4edda")
            self.dup_tree.tag_configure("delete", foreground="#dc3545")

        # Bind click event for toggling Keep/Delete and group selection
        self.dup_tree.bind("<Button-1>", self._on_dup_tree_click)

        # === BOTTOM SECTION: Actions ===
        actions_frame = ttk.Frame(duplicates_tab)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        # Auto-selection strategy section
        auto_select_section = ttk.LabelFrame(actions_frame, text="Auto-Selection Strategy", padding="10")
        auto_select_section.pack(fill=tk.X, pady=(0, 10))

        auto_select_inner = ttk.Frame(auto_select_section)
        auto_select_inner.pack(fill=tk.X)

        self.auto_select_strategy = tk.StringVar(value="Manual selection only")
        strategies = [
            "Manual selection only",
            "Keep by filename pattern (USA > Europe > Japan)",
            "Keep largest file",
            "Keep smallest file",
            "Keep oldest (by date)",
            "Keep newest (by date)"
        ]

        strategy_menu = ttk.Combobox(auto_select_inner, textvariable=self.auto_select_strategy,
                                     values=strategies, state="readonly", width=45)
        strategy_menu.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(strategy_menu, "Choose which file to keep in each duplicate group.\nPattern: Prefers (USA) > (Europe) > (Japan)\nLargest/Smallest: Based on file size\nOldest/Newest: Based on modification date")

        apply_btn = ttk.Button(auto_select_inner, text="Apply Auto-Selection",
                  command=self.apply_auto_selection)
        apply_btn.pack(side=tk.LEFT)
        ToolTip(apply_btn, "Automatically mark files to keep/delete based on selected strategy")

        # View Controls section
        view_section = ttk.LabelFrame(actions_frame, text="View Controls", padding="10")
        view_section.pack(fill=tk.X, pady=(0, 10))

        view_buttons = ttk.Frame(view_section)
        view_buttons.pack(fill=tk.X)

        expand_btn = ttk.Button(view_buttons, text="Expand All Groups",
                  command=self.expand_all_groups, width=20)
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(expand_btn, "Expand all duplicate groups to show individual files")

        collapse_btn = ttk.Button(view_buttons, text="Collapse All Groups",
                  command=self.collapse_all_groups, width=20)
        collapse_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(collapse_btn, "Collapse all groups to show only group summaries")

        select_all_btn = ttk.Button(view_buttons, text="Select All Groups",
                  command=self.select_all_groups, width=20)
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(select_all_btn, "Check all group checkboxes for deletion")

        deselect_all_btn = ttk.Button(view_buttons, text="Deselect All Groups",
                  command=self.deselect_all_groups, width=20)
        deselect_all_btn.pack(side=tk.LEFT)
        ToolTip(deselect_all_btn, "Uncheck all group checkboxes")

        # Actions section
        actions_section = ttk.LabelFrame(actions_frame, text="Actions", padding="10")
        actions_section.pack(fill=tk.X)

        action_buttons = ttk.Frame(actions_section)
        action_buttons.pack(fill=tk.X)

        export_btn = ttk.Button(action_buttons, text="Export Duplicate List",
                  command=self.export_duplicates_list, width=20)
        export_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(export_btn, "Save duplicate file list to a text file for review")

        self.delete_duplicates_btn = tk.Button(action_buttons, text="Delete Selected (0 groups)",
                                               command=self.delete_duplicates, state="disabled",
                                               bg="#dc3545", fg="white", font=("TkDefaultFont", 9, "bold"),
                                               height=1, relief=tk.RAISED, cursor="hand2", padx=15, pady=5)
        self.delete_duplicates_btn.pack(side=tk.LEFT)
        ToolTip(self.delete_duplicates_btn, "Permanently delete files marked in red from checked groups\n⚠️ This action cannot be undone!")

        # Initialize scan state
        self.scan_running = False
        self.scan_cancelled = False
        self.duplicate_groups = {}  # hash -> [file_paths]
        self.file_hashes = {}  # file_path -> hash
        self.group_selection = {}  # group_id -> True/False (selected or not)
        self.hash_cache = load_hash_cache()  # Persistent cache: "path|size|mtime|method" -> hash
        self.cache_hits = 0  # Track cache performance

    def setup_compare_tab(self):
        """Setup the compare collections tab"""
        compare_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(compare_tab, text="Compare Collections")

        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(compare_tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Compare two ROM collections to find missing files and sync between devices.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # === TOP SECTION: Comparison Setup ===
        setup_frame = ttk.LabelFrame(compare_tab, text="Comparison Setup", padding="10")
        setup_frame.pack(fill=tk.X, pady=(0, 10))

        # Collection A
        coll_a_frame = ttk.Frame(setup_frame)
        coll_a_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(coll_a_frame, text="Collection A:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        self.compare_path_a_var = tk.StringVar()
        ttk.Entry(coll_a_frame, textvariable=self.compare_path_a_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(coll_a_frame, text="Browse...", command=self.browse_collection_a).pack(side=tk.LEFT)

        # Collection B
        coll_b_frame = ttk.Frame(setup_frame)
        coll_b_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(coll_b_frame, text="Collection B:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        self.compare_path_b_var = tk.StringVar()
        ttk.Entry(coll_b_frame, textvariable=self.compare_path_b_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(coll_b_frame, text="Browse...", command=self.browse_collection_b).pack(side=tk.LEFT)

        # File filtering options
        filter_frame = ttk.Frame(setup_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="File Filter:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.compare_filter_mode = tk.StringVar(value="rom_only")

        rb_rom_only = ttk.Radiobutton(filter_frame, text="ROM files only (recommended)",
                                       variable=self.compare_filter_mode, value="rom_only")
        rb_rom_only.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb_rom_only, "Only scan ROM and archive files\nIgnores images, documents, saves, etc.")

        rb_all_files = ttk.Radiobutton(filter_frame, text="All files (advanced)",
                                        variable=self.compare_filter_mode, value="all_files")
        rb_all_files.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb_all_files, "Scan all file types without filtering")

        # Compare Method
        method_frame = ttk.Frame(setup_frame)
        method_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(method_frame, text="Compare Method:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.compare_method = tk.StringVar(value="quick")

        rb_quick = ttk.Radiobutton(method_frame, text="Quick Compare (by filename)",
                                   variable=self.compare_method, value="quick",
                                   command=self.on_compare_method_change)
        rb_quick.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb_quick, "Fast comparison by filename only.\nBest for syncing between devices.")

        rb_deep = ttk.Radiobutton(method_frame, text="Deep Compare (by content hash)",
                                  variable=self.compare_method, value="deep",
                                  command=self.on_compare_method_change)
        rb_deep.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb_deep, "Slower but thorough.\nFinds renamed files and verifies integrity.")

        # Verify integrity checkbox (only for Quick Compare)
        verify_frame = ttk.Frame(method_frame)
        verify_frame.pack(anchor=tk.W, padx=(40, 0), pady=(5, 0))
        self.verify_integrity = tk.BooleanVar(value=True)
        self.verify_integrity_cb = ttk.Checkbutton(verify_frame, text="Verify integrity of matching files",
                                                    variable=self.verify_integrity)
        self.verify_integrity_cb.pack(side=tk.LEFT)
        ToolTip(self.verify_integrity_cb, "Hash files with matching names to detect corruption")

        # Compare button
        compare_btn_frame = ttk.Frame(setup_frame)
        compare_btn_frame.pack(fill=tk.X, pady=(5, 0))
        self.start_compare_btn = ttk.Button(compare_btn_frame, text="Start Compare",
                                           command=self.start_compare)
        self.start_compare_btn.pack(side=tk.LEFT)

        # Progress section
        self.compare_progress_var = tk.IntVar(value=0)
        self.compare_progress_bar = ttk.Progressbar(compare_btn_frame, mode='determinate',
                                                    variable=self.compare_progress_var, maximum=100, length=300)
        self.compare_progress_bar.pack(side=tk.LEFT, padx=(10, 0))

        self.compare_status_var = tk.StringVar(value="")
        ttk.Label(compare_btn_frame, textvariable=self.compare_status_var).pack(side=tk.LEFT, padx=(10, 0))

        # === MIDDLE SECTION: Results Display ===
        results_frame = ttk.LabelFrame(compare_tab, text="Comparison Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Center info summary
        self.compare_summary_var = tk.StringVar(value="📊 Select two collections and click 'Start Compare'")
        summary_label = ttk.Label(results_frame, textvariable=self.compare_summary_var,
                                 font=("TkDefaultFont", 9))
        summary_label.pack(anchor=tk.W, pady=(0, 5))

        # Dual pane container
        panes_container = ttk.Frame(results_frame)
        panes_container.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for equal distribution
        panes_container.grid_columnconfigure(0, weight=1)
        panes_container.grid_columnconfigure(1, weight=1)
        panes_container.grid_rowconfigure(0, weight=1)

        # Left Pane: Only in Collection A
        left_pane = ttk.LabelFrame(panes_container, text="Only in Collection A (0 files)", padding="5")
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        left_tree_frame = ttk.Frame(left_pane)
        left_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.compare_tree_a = self.create_scrolled_treeview(left_tree_frame, ("select", "filename", "size", "date"))
        self.compare_tree_a.heading("select", text="☐")
        self.compare_tree_a.heading("filename", text="Filename",
                                    command=lambda: self.sort_treeview(self.compare_tree_a, "filename", False))
        self.compare_tree_a.heading("size", text="Size",
                                    command=lambda: self.sort_treeview(self.compare_tree_a, "size", False))
        self.compare_tree_a.heading("date", text="Date Modified",
                                    command=lambda: self.sort_treeview(self.compare_tree_a, "date", False))
        self.compare_tree_a.column("select", width=30, anchor="center")
        self.compare_tree_a.column("filename", width=250)
        self.compare_tree_a.column("size", width=80)
        self.compare_tree_a.column("date", width=120)

        # Right Pane: Only in Collection B
        right_pane = ttk.LabelFrame(panes_container, text="Only in Collection B (0 files)", padding="5")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        right_tree_frame = ttk.Frame(right_pane)
        right_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.compare_tree_b = self.create_scrolled_treeview(right_tree_frame, ("select", "filename", "size", "date"))
        self.compare_tree_b.heading("select", text="☐")
        self.compare_tree_b.heading("filename", text="Filename",
                                    command=lambda: self.sort_treeview(self.compare_tree_b, "filename", False))
        self.compare_tree_b.heading("size", text="Size",
                                    command=lambda: self.sort_treeview(self.compare_tree_b, "size", False))
        self.compare_tree_b.heading("date", text="Date Modified",
                                    command=lambda: self.sort_treeview(self.compare_tree_b, "date", False))
        self.compare_tree_b.column("select", width=30, anchor="center")
        self.compare_tree_b.column("filename", width=250)
        self.compare_tree_b.column("size", width=80)
        self.compare_tree_b.column("date", width=120)

        # Bind click events for checkbox toggling
        self.compare_tree_a.bind("<Button-1>", lambda e: self.on_compare_tree_click(e, self.compare_tree_a, "a"))
        self.compare_tree_b.bind("<Button-1>", lambda e: self.on_compare_tree_click(e, self.compare_tree_b, "b"))

        # Keyboard shortcuts for selection
        self.compare_tree_a.bind("<Control-a>", lambda e: self.select_all_compare("a"))
        self.compare_tree_a.bind("<Control-A>", lambda e: self.deselect_all_compare("a"))
        self.compare_tree_b.bind("<Control-a>", lambda e: self.select_all_compare("b"))
        self.compare_tree_b.bind("<Control-A>", lambda e: self.deselect_all_compare("b"))

        # Store pane labels for updating
        self.compare_left_pane = left_pane
        self.compare_right_pane = right_pane

        # === BOTTOM SECTION: Actions ===
        actions_frame = ttk.Frame(compare_tab)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        # Configure grid for left/right alignment
        actions_frame.grid_columnconfigure(0, weight=1)
        actions_frame.grid_columnconfigure(1, weight=1)

        # Left side actions (Collection A)
        left_actions = ttk.LabelFrame(actions_frame, text="Collection A Actions", padding="10")
        left_actions.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # Selection buttons for Collection A
        select_buttons_a = ttk.Frame(left_actions)
        select_buttons_a.pack(fill=tk.X, pady=(0, 10))

        self.select_all_a_btn = ttk.Button(select_buttons_a, text="Select All (0)",
                                          command=lambda: self.select_all_compare("a"))
        self.select_all_a_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ToolTip(self.select_all_a_btn, "Check all checkboxes in Collection A pane")

        self.deselect_all_a_btn = ttk.Button(select_buttons_a, text="Deselect All",
                                            command=lambda: self.deselect_all_compare("a"))
        self.deselect_all_a_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        ToolTip(self.deselect_all_a_btn, "Uncheck all checkboxes in Collection A pane")

        copy_to_b_btn = ttk.Button(left_actions, text="Copy Selected to B →",
                                   command=lambda: self.copy_files_between_collections("a_to_b"), width=25)
        copy_to_b_btn.pack(fill=tk.X, pady=(0, 5))
        ToolTip(copy_to_b_btn, "Copy selected files from Collection A to Collection B")

        export_a_btn = ttk.Button(left_actions, text="Generate Missing List",
                                 command=lambda: self.export_compare_list("a"), width=25)
        export_a_btn.pack(fill=tk.X)
        ToolTip(export_a_btn, "Export list of files only in Collection A")

        # Right side actions (Collection B)
        right_actions = ttk.LabelFrame(actions_frame, text="Collection B Actions", padding="10")
        right_actions.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # Selection buttons for Collection B
        select_buttons_b = ttk.Frame(right_actions)
        select_buttons_b.pack(fill=tk.X, pady=(0, 10))

        self.select_all_b_btn = ttk.Button(select_buttons_b, text="Select All (0)",
                                          command=lambda: self.select_all_compare("b"))
        self.select_all_b_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ToolTip(self.select_all_b_btn, "Check all checkboxes in Collection B pane")

        self.deselect_all_b_btn = ttk.Button(select_buttons_b, text="Deselect All",
                                            command=lambda: self.deselect_all_compare("b"))
        self.deselect_all_b_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        ToolTip(self.deselect_all_b_btn, "Uncheck all checkboxes in Collection B pane")

        copy_to_a_btn = ttk.Button(right_actions, text="← Copy Selected to A",
                                   command=lambda: self.copy_files_between_collections("b_to_a"), width=25)
        copy_to_a_btn.pack(fill=tk.X, pady=(0, 5))
        ToolTip(copy_to_a_btn, "Copy selected files from Collection B to Collection A")

        export_b_btn = ttk.Button(right_actions, text="Generate Missing List",
                                 command=lambda: self.export_compare_list("b"), width=25)
        export_b_btn.pack(fill=tk.X)
        ToolTip(export_b_btn, "Export list of files only in Collection B")

        # Initialize compare state
        self.compare_results = {"only_a": [], "only_b": [], "both": [], "corrupted": []}
        self.compare_selection_a = {}  # item_id -> True/False
        self.compare_selection_b = {}  # item_id -> True/False

    def should_include_file(self, file_path, filter_mode="rom_only"):
        """Check if a file should be included based on filter mode"""
        if filter_mode == "all_files":
            return True

        # Get file extension (case-insensitive)
        _, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()

        # Check if file is in excluded folder
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part.lower() in EXCLUDED_FOLDER_NAMES:
                return False

        # Check whitelist for ROM files FIRST (before blacklist)
        # This is important for extensions like .md (Mega Drive) that conflict with blacklist (Markdown)
        if ext_lower in ROM_EXTENSIONS_WHITELIST:
            return True

        # Also include .zip files in ROM-only mode (for DAT Rename and other features)
        if ext_lower == '.zip':
            return True

        # Check blacklist after whitelist
        if ext_lower in FILE_EXTENSIONS_BLACKLIST:
            return False

        # If not in whitelist and not in blacklist, exclude it in ROM-only mode
        return False

    def setup_custom_selection(self, tree):
        """Setup custom selection behavior for a treeview"""
        # Store drag state
        tree.drag_start_item = None
        tree.is_dragging = False
        tree.selection_before_drag = []

        def on_click(event):
            """Handle single click to toggle selection"""
            item = tree.identify_row(event.y)
            if not item:
                return

            tree.drag_start_item = item
            tree.is_dragging = False

            # With Ctrl: toggle individual item
            if event.state & 0x0004:  # Ctrl
                if item in tree.selection():
                    tree.selection_remove(item)
                else:
                    tree.selection_add(item)
                tree.selection_before_drag = list(tree.selection())
                return "break"

            # With Shift: extend selection
            if event.state & 0x0001:  # Shift
                return  # Let default behavior handle it

            # Normal click: toggle selection
            if item in tree.selection():
                tree.selection_remove(item)
            else:
                tree.selection_set(item)
            tree.selection_before_drag = list(tree.selection())
            return "break"

        def on_drag(event):
            """Handle drag to select multiple"""
            if tree.drag_start_item is None:
                return

            current_item = tree.identify_row(event.y)
            if not current_item:
                return

            if current_item != tree.drag_start_item:
                tree.is_dragging = True

            # Get all items
            all_items = tree.get_children()
            if tree.drag_start_item not in all_items or current_item not in all_items:
                return

            start_idx = all_items.index(tree.drag_start_item)
            end_idx = all_items.index(current_item)

            # Select range
            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            drag_range = all_items[start_idx:end_idx + 1]

            # With Ctrl: add drag range to previous selection
            if event.state & 0x0004:  # Ctrl
                combined = set(tree.selection_before_drag) | set(drag_range)
                tree.selection_set(list(combined))
            else:
                tree.selection_set(drag_range)

        def on_release(event):
            """End drag selection"""
            tree.selection_before_drag = list(tree.selection())
            tree.drag_start_item = None
            tree.is_dragging = False

        # Bind events
        tree.bind("<Button-1>", on_click)
        tree.bind("<B1-Motion>", on_drag)
        tree.bind("<ButtonRelease-1>", on_release)

    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(title="Select ROM Folder")
        if folder:
            self.current_folder = folder
            self.folder_var.set(folder)
            self.load_files()

            # Auto-detect file extensions in the folder
            self.auto_detect_extension()

            # Update DAT rename status if DAT file is already loaded
            if hasattr(self, 'dat_hash_map') and self.dat_hash_map:
                self._update_dat_status_with_file_count()

    def load_files(self):
        """Load files from the selected folder"""
        if not self.current_folder:
            return

        self.files_data = []
        try:
            for item in os.listdir(self.current_folder):
                full_path = os.path.join(self.current_folder, item)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    self.files_data.append((item, size, full_path))

            self.files_data.sort(key=lambda x: x[0].lower())
            self.refresh_file_list()
            self.refresh_compression_lists()
            self.status_var.set(f"Loaded {len(self.files_data)} files")

        except Exception as e:
            show_error(self.root, "Error", f"Failed to load files: {str(e)}")

    def format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def parse_size(self, size_str):
        """Parse formatted size string back to bytes for sorting"""
        try:
            parts = size_str.split()
            if len(parts) != 2:
                return 0
            value = float(parts[0])
            unit = parts[1]

            multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
            return value * multipliers.get(unit, 1)
        except:
            return 0

    # ==================== HELPER METHODS ====================

    def create_scrolled_treeview(self, parent, columns, show="headings", selectmode="extended"):
        """Create a treeview with scrollbars and grid configuration.
        Returns the treeview widget. Scrollbars are attached automatically."""
        vsb = ttk.Scrollbar(parent, orient="vertical")
        hsb = ttk.Scrollbar(parent, orient="horizontal")
        tree = ttk.Treeview(parent, columns=columns, show=show, selectmode=selectmode,
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        return tree

    def run_worker_thread(self, work_func, args=(), progress=None, on_complete=None):
        """Run a function in a background thread with optional progress and completion callback."""
        def worker():
            work_func(*args)
            if progress:
                progress.close()
            if on_complete:
                self.root.after(0, on_complete)
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def get_files_from_tree(self, tree, folder, selected_only=True, filename_col=0):
        """Extract file paths from treeview items.
        Returns list of (full_path, item_id) tuples for existing files."""
        items = tree.selection() if selected_only else tree.get_children()
        files = []
        for item in items:
            values = tree.item(item, "values")
            filename = values[filename_col]
            full_path = os.path.join(folder, filename)
            if os.path.exists(full_path):
                files.append((full_path, item))
        return files

    def confirm_and_start_operation(self, action_name, file_count, warning_msg=None, title=None):
        """Show confirmation dialog and create progress dialog.
        Returns (ProgressDialog, results_dict) or (None, None) if cancelled."""
        msg = f"{action_name} {file_count} file(s)?"
        if warning_msg:
            msg += f"\n\n{warning_msg}"
        if not ask_yesno(self.root, title or f"Confirm {action_name}", msg):
            return None, None
        progress = ProgressDialog(self.root, f"{action_name}...", file_count)
        results = {'success': 0, 'failed': 0, 'skipped': 0, 'errors': []}
        return progress, results

    def format_operation_results(self, counts, errors=None, max_errors=10):
        """Format operation results into a display message.
        counts: dict like {'Compressed': 5, 'Failed': 2}
        errors: list of error strings"""
        lines = [f"{k}: {v}" for k, v in counts.items() if v > 0 or k in ('Success', 'Failed')]
        msg = "\n".join(lines)
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors[:max_errors])
            if len(errors) > max_errors:
                msg += f"\n... and {len(errors) - max_errors} more"
        return msg

    def scan_directory(self, path, filter_mode="rom_only", recursive=True):
        """Generator that yields file paths from a directory, applying filters.
        Handles excluded folders and file type filtering."""
        if recursive:
            for root, dirs, files in os.walk(path):
                if filter_mode == "rom_only":
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                for file in files:
                    full_path = os.path.join(root, file)
                    if self.should_include_file(full_path, filter_mode):
                        yield full_path
        else:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isfile(full_path) and self.should_include_file(full_path, filter_mode):
                    yield full_path

    def get_file_metadata(self, file_path):
        """Get file size and formatted modification date.
        Returns (size_bytes, date_string)."""
        size = os.path.getsize(file_path)
        mod_time = os.path.getmtime(file_path)
        date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
        return size, date_str

    # ==================== END HELPER METHODS ====================

    def sort_treeview(self, tree, col, reverse):
        """Sort treeview contents by column"""
        # Get all items
        items = [(tree.set(item, col), item) for item in tree.get_children('')]

        # Determine sort key based on column
        if col == "size":
            # Sort by actual file size (parse formatted size back to bytes)
            items.sort(key=lambda x: self.parse_size(x[0]), reverse=reverse)
        elif col == "date":
            # Sort by date (chronologically)
            items.sort(key=lambda x: x[0], reverse=reverse)
        else:
            # Sort alphabetically for text columns (filename, select checkbox, etc.)
            items.sort(key=lambda x: x[0].lower() if x[0] else "", reverse=reverse)

        # Rearrange items in sorted order
        for index, (val, item) in enumerate(items):
            tree.move(item, '', index)

        # Update column heading to toggle sort direction next time
        sort_key = f"{id(tree)}_{col}"
        new_reverse = not reverse
        self.sort_reverse[sort_key] = new_reverse

        # Save the current sort state for this tree
        tree_id = id(tree)
        self.last_sort[tree_id] = (col, reverse)

        # Update column headings with sort arrows
        # Define base column names
        col_names = {
            "filename": "Filename",
            "size": "Size",
            "status": "Status",
            "original": "Original Filename",
            "preview": "Preview (after rename)",
            "date": "Date Modified",
            "select": "☐",
            "current": "Current Name",
            "new": "New Name (from DAT)",
            "game_name": "Game Name",
            "disc_count": "Discs",
            "location": "Location"
        }

        # Clear arrows from all columns and add arrow to sorted column
        for column in tree["columns"]:
            base_name = col_names.get(column, column.title())
            if column == col:
                # Add arrow to sorted column
                arrow = " ▼" if reverse else " ▲"
                tree.heading(column, text=base_name + arrow,
                           command=lambda c=column: self.sort_treeview(tree, c, new_reverse))
            else:
                # Remove arrow from other columns
                tree.heading(column, text=base_name,
                           command=lambda c=column: self.sort_treeview(tree, c, False))

    def refresh_file_list(self):
        """Refresh the treeview with current files_data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add files from cached data
        for filename, size, full_path in self.files_data:
            self.tree.insert("", tk.END, values=(
                filename,
                "",  # Preview will be filled when user clicks Preview
                self.format_size(size)
            ))

    def reload_files(self):
        """Reload files from disk (called by Refresh button)"""
        if self.current_folder:
            self.load_files()
        self.status_var.set(f"Refreshed: {len(self.files_data)} files")

    def load_preset(self, pattern, replacement):
        """Load a preset pattern into the input fields"""
        self.pattern_var.set(pattern)
        self.replacement_var.set(replacement)
        # Auto-update preview when preset is selected
        if self.files_data:  # Only preview if files are loaded
            self.preview_rename()

    def preview_rename(self):
        """Preview the rename operation"""
        pattern = self.pattern_var.get()
        replacement = self.replacement_var.get()

        if not pattern:
            show_warning(self.root, "Warning", "Please enter a regex pattern")
            return

        try:
            # Test the regex pattern
            re.compile(pattern)
        except re.error as e:
            show_error(self.root, "Regex Error", f"Invalid regex pattern: {str(e)}")
            return

        # Clear and repopulate tree with previews
        for item in self.tree.get_children():
            self.tree.delete(item)

        # First pass: calculate all new names and detect collisions
        rename_map = {}  # new_name -> list of (original_filename, size, full_path)
        new_names_map = {}  # original_filename -> new_name

        for filename, size, full_path in self.files_data:
            new_name = re.sub(pattern, replacement, filename)
            # Clean up any double spaces or spaces before extension
            new_name = re.sub(r'\s+', ' ', new_name)
            new_name = re.sub(r'\s+\.', '.', new_name)
            new_name = new_name.strip()

            new_names_map[filename] = new_name

            if new_name != filename:
                if new_name not in rename_map:
                    rename_map[new_name] = []
                rename_map[new_name].append((filename, size, full_path))

        # Detect collisions
        collisions = {name: files for name, files in rename_map.items() if len(files) > 1}
        collision_count = sum(len(files) for files in collisions.values())

        # Also check for collisions with existing files that aren't being renamed
        existing_collisions = []
        for new_name in rename_map.keys():
            new_path = os.path.join(self.current_folder, new_name)
            # Check if a file with this name exists and is NOT in our files being renamed
            if os.path.exists(new_path) and new_name not in new_names_map:
                existing_collisions.append(new_name)

        # Second pass: display in tree with collision warnings
        changes_count = 0
        for filename, size, full_path in self.files_data:
            new_name = new_names_map[filename]

            if new_name != filename:
                changes_count += 1

            # Determine status message
            preview_text = new_name if new_name != filename else "(no change)"
            tags = []

            # Check if this file is part of a collision
            if new_name in collisions:
                preview_text = f"{new_name} ⚠ COLLISION"
                tags.append("collision")
            elif new_name in existing_collisions:
                preview_text = f"{new_name} ⚠ EXISTS"
                tags.append("collision")
            elif new_name != filename:
                tags.append("changed")

            # Add to tree
            item_id = self.tree.insert("", tk.END, values=(
                filename,
                preview_text,
                self.format_size(size)
            ))

            if tags:
                self.tree.item(item_id, tags=tuple(tags))

        # Configure tag colors (dark mode friendly)
        if TTKBOOTSTRAP_AVAILABLE and hasattr(self.root, 'style'):
            # Check if using dark theme
            theme = self.root.style.theme.name if hasattr(self.root.style, 'theme') else 'light'
            if 'dark' in theme.lower():
                self.tree.tag_configure("changed", background="#505050")  # Dark grey
                self.tree.tag_configure("collision", background="#5c1a1a", foreground="white")  # Dark red
            else:
                colors = self.root.style.colors
                self.tree.tag_configure("changed", background=colors.info)
                self.tree.tag_configure("collision", background=colors.danger, foreground="white")
        else:
            # Check current theme setting
            if hasattr(self, 'current_theme') and self.current_theme == 'dark':
                self.tree.tag_configure("changed", background="#505050")  # Dark grey
                self.tree.tag_configure("collision", background="#5c1a1a", foreground="white")  # Dark red
            else:
                self.tree.tag_configure("changed", background="#e8f4f8")  # Light blue
                self.tree.tag_configure("collision", background="#ffcccc")  # Light red

        # Update status message
        status_msg = f"Preview: {changes_count} files will be renamed"
        if collisions or existing_collisions:
            total_collision_files = collision_count + len(existing_collisions)
            status_msg += f" ⚠ {len(collisions) + len(existing_collisions)} collisions detected affecting {total_collision_files} files!"
            self.status_var.set(status_msg)
        else:
            self.status_var.set(status_msg)

        self.rename_button.config(state="normal" if changes_count > 0 else "disabled")

        # Enable "Rename Selected" if there are changes and selections
        selected = self.tree.selection()
        self.rename_selected_button.config(state="normal" if changes_count > 0 and selected else "disabled")

    def rename_selected(self):
        """Rename only the selected files"""
        pattern = self.pattern_var.get()
        replacement = self.replacement_var.get()

        if not pattern:
            return

        # Get selected items
        selected = self.tree.selection()
        if not selected:
            show_info(self.root, "Rename Selected", "No files selected")
            return

        # Build a set of selected filenames
        selected_filenames = set()
        for item in selected:
            values = self.tree.item(item, "values")
            original_filename = values[0]
            selected_filenames.add(original_filename)

        # First, build rename plan for selected files only
        rename_plan = []
        new_name_counts = {}
        existing_files_map = {}

        for filename, size, full_path in self.files_data:
            existing_files_map[filename.lower()] = filename

        # Only process selected files
        for filename, size, full_path in self.files_data:
            if filename not in selected_filenames:
                continue

            new_name = re.sub(pattern, replacement, filename)
            new_name = re.sub(r'\s+', ' ', new_name)
            new_name = re.sub(r'\s+\.', '.', new_name)
            new_name = new_name.strip()

            if new_name != filename:
                # Track collisions
                new_name_lower = new_name.lower()
                if new_name_lower not in new_name_counts:
                    new_name_counts[new_name_lower] = 0
                new_name_counts[new_name_lower] += 1

                new_path = os.path.join(self.current_folder, new_name)
                rename_plan.append((full_path, new_path, filename, new_name))

        if not rename_plan:
            show_info(self.root, "Rename Selected", "No changes to apply for selected files")
            return

        # Apply collision strategy (same as execute_rename)
        strategy = self.collision_strategy.get()
        final_rename_plan = []
        skipped_count = 0

        collision_groups = {}
        for old_path, new_path, old_name, new_name in rename_plan:
            new_name_lower = new_name.lower()
            if new_name_lower not in collision_groups:
                collision_groups[new_name_lower] = []
            collision_groups[new_name_lower].append((old_path, new_path, old_name, new_name))

        for new_name_lower, group in collision_groups.items():
            if len(group) == 1:
                final_rename_plan.append(group[0])
            else:
                if strategy == "skip":
                    skipped_count += len(group)
                elif strategy == "keep_first":
                    final_rename_plan.append(group[0])
                    skipped_count += len(group) - 1
                elif strategy == "suffix":
                    for idx, (old_path, new_path, old_name, new_name) in enumerate(group):
                        name_parts = os.path.splitext(new_name)
                        suffixed_name = f"{name_parts[0]}_{idx + 1}{name_parts[1]}"
                        suffixed_path = os.path.join(self.current_folder, suffixed_name)
                        final_rename_plan.append((old_path, suffixed_path, old_name, suffixed_name))

        # Show confirmation
        confirm_msg = f"Ready to rename {len(final_rename_plan)} selected file(s)"
        if skipped_count > 0:
            confirm_msg += f"\n{skipped_count} files will be skipped due to collisions"
        confirm_msg += "\n\nProceed with rename?"

        response = ask_yesno(self.root, "Confirm Rename", confirm_msg)
        if not response:
            return

        # Show progress dialog and run rename in thread
        progress = ProgressDialog(self.root, "Renaming Selected Files", len(final_rename_plan))

        # Store results for thread
        self.rename_results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'skipped_count': skipped_count,
            'undo_history': []
        }

        def rename_worker():
            """Worker thread for renaming files"""
            self._perform_renames(final_rename_plan, progress, self.rename_results)
            # Close progress and show results in main thread
            progress.close()
            self.root.after(0, self._show_rename_results)

        # Start rename thread
        thread = threading.Thread(target=rename_worker, daemon=True)
        thread.start()

    def execute_rename(self):
        """Execute the rename operation - respects selection if items are selected"""
        pattern = self.pattern_var.get()
        replacement = self.replacement_var.get()

        if not pattern:
            return

        # Check if user has selected specific items
        selected = self.tree.selection()
        selected_filenames = set()

        if selected:
            # Build set of selected filenames
            for item in selected:
                values = self.tree.item(item, "values")
                original_filename = values[0]
                selected_filenames.add(original_filename)

        # First, build rename plan and detect collisions
        rename_plan = []  # List of (old_path, new_path, original_filename, new_filename)
        new_name_counts = {}  # Track how many files want each new name
        existing_files_map = {}  # Map of current filenames in lowercase

        for filename, size, full_path in self.files_data:
            existing_files_map[filename.lower()] = filename

        for filename, size, full_path in self.files_data:
            # If selection exists, only process selected files
            if selected and filename not in selected_filenames:
                continue
            new_name = re.sub(pattern, replacement, filename)
            new_name = re.sub(r'\s+', ' ', new_name)
            new_name = re.sub(r'\s+\.', '.', new_name)
            new_name = new_name.strip()

            if new_name != filename:
                # Track collisions
                new_name_lower = new_name.lower()
                if new_name_lower not in new_name_counts:
                    new_name_counts[new_name_lower] = 0
                new_name_counts[new_name_lower] += 1

                new_path = os.path.join(self.current_folder, new_name)
                rename_plan.append((full_path, new_path, filename, new_name))

        # Apply collision strategy
        strategy = self.collision_strategy.get()
        final_rename_plan = []
        skipped_count = 0

        collision_groups = {}  # Group files by target name
        for old_path, new_path, old_name, new_name in rename_plan:
            new_name_lower = new_name.lower()
            if new_name_lower not in collision_groups:
                collision_groups[new_name_lower] = []
            collision_groups[new_name_lower].append((old_path, new_path, old_name, new_name))

        for new_name_lower, group in collision_groups.items():
            if len(group) == 1:
                # No collision, add as-is
                final_rename_plan.append(group[0])
            else:
                # Collision detected - apply strategy
                if strategy == "skip":
                    # Skip all files in this collision
                    skipped_count += len(group)
                elif strategy == "keep_first":
                    # Keep only the first file, skip the rest
                    final_rename_plan.append(group[0])
                    skipped_count += len(group) - 1
                elif strategy == "suffix":
                    # Add suffix to each file
                    for idx, (old_path, new_path, old_name, new_name) in enumerate(group):
                        # Split filename and extension
                        name_parts = os.path.splitext(new_name)
                        suffixed_name = f"{name_parts[0]}_{idx + 1}{name_parts[1]}"
                        suffixed_path = os.path.join(self.current_folder, suffixed_name)
                        final_rename_plan.append((old_path, suffixed_path, old_name, suffixed_name))

        # Show confirmation with collision info
        if selected:
            confirm_msg = f"Ready to rename {len(final_rename_plan)} selected file"
            if len(final_rename_plan) != 1:
                confirm_msg += "s"
        else:
            confirm_msg = f"Ready to rename {len(final_rename_plan)} file"
            if len(final_rename_plan) != 1:
                confirm_msg += "s"

        if skipped_count > 0:
            confirm_msg += f"\n{skipped_count} file"
            if skipped_count != 1:
                confirm_msg += "s"
            confirm_msg += " will be skipped due to collisions"
        confirm_msg += "\n\nProceed with rename?"

        response = ask_yesno(self.root, "Confirm Rename", confirm_msg)
        if not response:
            return

        # Show progress dialog and run rename in thread
        progress = ProgressDialog(self.root, "Renaming Files", len(final_rename_plan))

        # Store results for thread
        self.rename_results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'skipped_count': skipped_count,
            'undo_history': []
        }

        def rename_worker():
            """Worker thread for renaming files"""
            self._perform_renames(final_rename_plan, progress, self.rename_results)
            # Close progress and show results in main thread
            progress.close()
            self.root.after(0, self._show_rename_results)

        # Start rename thread
        thread = threading.Thread(target=rename_worker, daemon=True)
        thread.start()

    def _perform_renames(self, final_rename_plan, progress, results):
        """Perform the actual rename operations (runs in worker thread)"""
        undo_history = []

        for idx, (old_path, new_path, old_name, new_name) in enumerate(final_rename_plan, 1):
            # Update progress
            progress.update(idx, old_name)

            try:
                # Final check if destination exists
                if os.path.exists(new_path):
                    results['errors'].append(f"{old_name} -> {new_name}: Destination already exists")
                    results['error_count'] += 1
                    continue

                # Attempt rename with retry for file locking/volume issues
                max_retries = 5
                renamed_successfully = False

                for attempt in range(max_retries):
                    try:
                        # Force garbage collection to release file handles
                        if attempt > 0:
                            gc.collect()

                        # Try os.rename first (faster)
                        os.rename(old_path, new_path)
                        undo_history.append((new_path, old_path))
                        results['success_count'] += 1
                        renamed_successfully = True
                        break

                    except PermissionError as e:
                        if attempt < max_retries - 1:
                            # Exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s
                            time.sleep(0.2 * (2 ** attempt))
                        else:
                            results['errors'].append(f"{old_name}: Permission denied")
                            results['error_count'] += 1
                            break

                    except OSError as e:
                        # Check for specific Windows errors
                        winerror_code = getattr(e, 'winerror', None)

                        # WinError 32: File in use by another process
                        # WinError 1006: Volume externally altered
                        # WinError 5: Access denied
                        if winerror_code in [32, 1006, 5]:
                            if attempt < max_retries - 1:
                                # Force GC and wait with exponential backoff
                                gc.collect()
                                wait_time = 0.3 * (2 ** attempt)  # 0.3s, 0.6s, 1.2s, 2.4s
                                time.sleep(wait_time)

                                # On last retry, try alternative method
                                if attempt == max_retries - 2:
                                    try:
                                        shutil.move(old_path, new_path)
                                        undo_history.append((new_path, old_path))
                                        results['success_count'] += 1
                                        renamed_successfully = True
                                        break
                                    except:
                                        pass  # Will retry with os.rename
                            else:
                                if winerror_code == 1006:
                                    results['errors'].append(f"{old_name}: Volume access error (try closing antivirus/indexing)")
                                elif winerror_code == 32:
                                    results['errors'].append(f"{old_name}: File is locked by another process")
                                else:
                                    results['errors'].append(f"{old_name}: Access denied")
                                results['error_count'] += 1
                                break
                        else:
                            # Unknown OSError, raise it
                            raise

            except Exception as e:
                if not renamed_successfully:
                    error_msg = str(e)
                    # Make error messages more user-friendly
                    if "WinError 1006" in error_msg:
                        error_msg = "Volume access error (external drive or antivirus interference)"
                    results['errors'].append(f"{old_name}: {error_msg}")
                    results['error_count'] += 1

        # Store undo history
        results['undo_history'] = undo_history

    def _show_rename_results(self):
        """Show rename results and update UI (runs in main thread)"""
        results = self.rename_results

        # Update undo history
        self.undo_history = results['undo_history']

        # Update gamelist.xml if checkbox is enabled
        gamelist_updates = self._update_gamelist_if_enabled(
            self.update_gamelist_var,
            results['undo_history'],
            results['success_count']
        )

        # Show results
        result_msg = f"Successfully renamed {results['success_count']} files"
        if gamelist_updates > 0:
            result_msg += f"\nUpdated {gamelist_updates} path(s) in gamelist.xml"
        if results['skipped_count'] > 0:
            result_msg += f"\n{results['skipped_count']} files skipped (collisions)"
        if results['error_count'] > 0:
            result_msg += f"\n{results['error_count']} errors occurred"
            if results['errors']:
                result_msg += "\n\nErrors:\n" + "\n".join(results['errors'][:10])
                if len(results['errors']) > 10:
                    result_msg += f"\n... and {len(results['errors']) - 10} more"

        show_info(self.root, "Rename Complete", result_msg)

        # Enable undo button if any renames were successful
        if self.undo_history:
            self.undo_button.config(state="normal")

        # Reload files and reset preview
        self.load_files()
        self.rename_button.config(state="disabled")
        self.rename_selected_button.config(state="disabled")

    def _update_gamelist_if_enabled(self, checkbox_var, undo_history, success_count):
        """
        Helper to update gamelist.xml if checkbox is enabled.
        Returns number of paths updated.
        """
        if not checkbox_var.get() or success_count == 0:
            return 0

        try:
            # Create rename map from undo history: {old_path: new_path}
            rename_map = {old_path: new_path for new_path, old_path in undo_history}
            return update_gamelist_xml(self.current_folder, rename_map)
        except Exception:
            # Don't fail the whole operation if gamelist update fails
            return 0

    def _restore_gamelist_backup(self):
        """
        Helper to restore gamelist.xml from backup.
        Returns True if backup was restored, False otherwise.
        """
        if not self.current_folder:
            return False

        gamelist_path = os.path.join(self.current_folder, "gamelist.xml")
        backup_path = gamelist_path + ".backup"

        if not os.path.exists(backup_path):
            return False

        try:
            shutil.copy2(backup_path, gamelist_path)
            os.remove(backup_path)
            return True
        except Exception:
            return False

    def undo_rename(self):
        """Undo the last rename operation"""
        if not self.undo_history:
            show_info(self.root, "Undo", "No rename operation to undo")
            return

        # Confirm with user
        response = ask_yesno(
            self.root,
            "Confirm Undo",
            f"Are you sure you want to undo the last rename?\n{len(self.undo_history)} files will be reverted."
        )

        if not response:
            return

        success_count = 0
        error_count = 0
        errors = []

        # Reverse the rename operations
        for current_path, original_path in self.undo_history:
            try:
                # Check if the renamed file still exists
                if not os.path.exists(current_path):
                    errors.append(f"{os.path.basename(current_path)}: File not found")
                    error_count += 1
                # Check if original name is now occupied
                elif os.path.exists(original_path):
                    errors.append(f"{os.path.basename(original_path)}: Original filename already exists")
                    error_count += 1
                else:
                    os.rename(current_path, original_path)
                    success_count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(current_path)}: {str(e)}")
                error_count += 1

        # Restore gamelist.xml from backup if it exists
        gamelist_restored = self._restore_gamelist_backup()

        # Show results
        result_msg = f"Successfully reverted {success_count} files"
        if gamelist_restored:
            result_msg += "\nRestored gamelist.xml from backup"
        if error_count > 0:
            result_msg += f"\n{error_count} errors occurred"
            if errors:
                result_msg += "\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    result_msg += f"\n... and {len(errors) - 10} more"

        show_info(self.root, "Undo Complete", result_msg)

        # Clear undo history and disable undo button
        self.undo_history = []
        self.undo_button.config(state="disabled")

        # Reload files
        self.load_files()


    def auto_detect_extension(self):
        """Auto-detect ROM file extensions in the current folder"""
        if not self.current_folder:
            return

        # Common ROM extensions to look for
        rom_extensions = [
            '.gba', '.gbc', '.gb', '.smc', '.sfc', '.nes',
            '.md', '.gen', '.n64', '.z64', '.v64', '.nds',
            '.cia', '.3ds', '.iso', '.chd', '.cue', '.bin',
            '.gcm', '.cso', '.wbfs', '.wad', '.u8'
        ]

        # Count files by extension
        extension_counts = {}
        try:
            for item in os.listdir(self.current_folder):
                full_path = os.path.join(self.current_folder, item)
                if os.path.isfile(full_path):
                    _, ext = os.path.splitext(item)
                    ext_lower = ext.lower()
                    if ext_lower in rom_extensions:
                        extension_counts[ext_lower] = extension_counts.get(ext_lower, 0) + 1

            # If we found ROM files, set to the most common extension
            if extension_counts:
                most_common_ext = max(extension_counts, key=extension_counts.get)
                most_common_count = extension_counts[most_common_ext]

                # Set the compression extension filter
                self.compress_ext_var.set(f"*{most_common_ext}")
                self.refresh_compression_lists()

                # Update status to show what was detected
                if len(extension_counts) > 1:
                    other_exts = [f"{ext.upper()}: {count}" for ext, count in extension_counts.items() if ext != most_common_ext]
                    detection_msg = f"Auto-detected: {most_common_count} {most_common_ext.upper()} files"
                    if other_exts:
                        detection_msg += f" (also found: {', '.join(other_exts[:3])})"
                    self.status_var.set(detection_msg)
                else:
                    self.status_var.set(f"Auto-detected: {most_common_count} {most_common_ext.upper()} files")
            else:
                # Check if we have zip files
                zip_count = sum(1 for _, _, path in self.files_data if path.lower().endswith('.zip'))
                if zip_count > 0:
                    self.status_var.set(f"Loaded {len(self.files_data)} files ({zip_count} zipped)")
                else:
                    self.status_var.set(f"Loaded {len(self.files_data)} files")

        except Exception as e:
            # Silently fail auto-detection
            pass

    def set_compression_extension(self, extension):
        """Set the compression extension and refresh lists"""
        self.compress_ext_var.set(extension)
        self.refresh_compression_lists()

    def refresh_compression_lists(self):
        """Refresh both compression panes"""
        if not self.current_folder:
            return

        # Clear both trees
        for item in self.uncompressed_tree.get_children():
            self.uncompressed_tree.delete(item)
        for item in self.compressed_tree.get_children():
            self.compressed_tree.delete(item)

        extension = self.compress_ext_var.get()

        try:
            import glob

            # Get ROM files (left pane)
            rom_pattern = os.path.join(self.current_folder, extension)
            rom_files = glob.glob(rom_pattern)

            # Get ZIP files (right pane)
            zip_pattern = os.path.join(self.current_folder, "*.zip")
            zip_files = glob.glob(zip_pattern)

            rom_count = 0
            archived_count = 0
            # Process ROM files for left pane
            for file_path in rom_files:
                if os.path.isfile(file_path):
                    filename = os.path.basename(file_path)
                    size = os.path.getsize(file_path)

                    if size > 0:  # Skip empty files
                        # Check if corresponding ZIP exists
                        base_name = os.path.splitext(filename)[0]
                        zip_path = os.path.join(self.current_folder, base_name + ".zip")
                        has_zip = os.path.exists(zip_path)

                        status = "Archived" if has_zip else "Unarchived"
                        tags = ("archived",) if has_zip else ()

                        item_id = self.uncompressed_tree.insert("", tk.END, values=(
                            filename,
                            self.format_size(size),
                            status
                        ))

                        if tags:
                            self.uncompressed_tree.item(item_id, tags=tags)
                            archived_count += 1

                        rom_count += 1

            # Configure tag colors for archived files (theme-aware if ttkbootstrap available)
            if TTKBOOTSTRAP_AVAILABLE and hasattr(self.root, 'style'):
                colors = self.root.style.colors
                self.uncompressed_tree.tag_configure("archived", background=colors.success)
            else:
                self.uncompressed_tree.tag_configure("archived", background="#d4edda")

            # Update "Delete Archived Only" button
            if archived_count > 0:
                self.delete_archived_btn.config(
                    text=f"Delete Archived ({archived_count})",
                    state="normal"
                )
            else:
                self.delete_archived_btn.config(
                    text="Delete Archived Only",
                    state="disabled"
                )

            zip_count = 0
            # Process ZIP files for right pane
            for zip_path in zip_files:
                if os.path.isfile(zip_path):
                    zip_filename = os.path.basename(zip_path)
                    size = os.path.getsize(zip_path)

                    self.compressed_tree.insert("", tk.END, values=(
                        zip_filename,
                        self.format_size(size)
                    ))
                    zip_count += 1

            # Update status
            self.compression_status_var.set(f"Left: {rom_count} files | Right: {zip_count} archives")

            # Reapply sorting if it was previously set
            uncompressed_tree_id = id(self.uncompressed_tree)
            if uncompressed_tree_id in self.last_sort:
                sort_col, sort_reverse = self.last_sort[uncompressed_tree_id]
                self.sort_treeview(self.uncompressed_tree, sort_col, sort_reverse)

            compressed_tree_id = id(self.compressed_tree)
            if compressed_tree_id in self.last_sort:
                sort_col, sort_reverse = self.last_sort[compressed_tree_id]
                self.sort_treeview(self.compressed_tree, sort_col, sort_reverse)

        except Exception as e:
            show_error(self.root, "Error", f"Failed to load files: {str(e)}")

    def compress_selected_roms(self):
        """Compress selected ROM files from the left pane"""
        self._compress_roms(selected_only=True)

    def compress_all_roms(self):
        """Compress all ROM files from the left pane"""
        self._compress_roms(selected_only=False)

    def _compress_roms(self, selected_only=True):
        """Compress ROM files from the left pane"""
        if not self.current_folder:
            return

        # Get files from tree
        files = self.get_files_from_tree(self.uncompressed_tree, self.current_folder, selected_only)
        if not files:
            msg = "Please select files to compress" if selected_only else "No files to compress"
            show_info(self.root, "Compress", msg)
            return

        compress_list = [f[0] for f in files]

        # Confirm and start
        delete_originals = self.delete_originals_var.get()
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: Original files will be DELETED after compression!" if delete_originals else None
        progress, _ = self.confirm_and_start_operation(
            f"Compress {len(compress_list)} {label} file(s)", 1,
            warning_msg=warning, title="Confirm Compression"
        )
        if not progress:
            return

        # Reset progress for actual file count
        progress.total_items = len(compress_list)
        progress.progress_bar.config(maximum=len(compress_list))

        self.compression_results = {
            'compressed': 0, 'skipped': 0, 'failed': 0, 'total_savings': 0, 'errors': []
        }

        self.run_worker_thread(
            self._perform_compression,
            args=(compress_list, progress, delete_originals, self.compression_results),
            progress=progress,
            on_complete=self._show_compression_results
        )

    def extract_selected_zips(self):
        """Extract selected ZIP files from the right pane"""
        self._extract_zips(selected_only=True)

    def extract_all_zips(self):
        """Extract all ZIP files from the right pane"""
        self._extract_zips(selected_only=False)

    def _extract_zips(self, selected_only=True):
        """Extract ZIP files from the right pane"""
        if not self.current_folder:
            return

        # Get files from tree
        files = self.get_files_from_tree(self.compressed_tree, self.current_folder, selected_only)
        if not files:
            msg = "Please select ZIP files to extract" if selected_only else "No ZIP files to extract"
            show_info(self.root, "Extract", msg)
            return

        zip_list = [f[0] for f in files]

        # Confirm and start
        delete_archives = self.delete_archives_var.get()
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: ZIP files will be DELETED after extraction!" if delete_archives else None
        progress, _ = self.confirm_and_start_operation(
            f"Extract {len(zip_list)} {label} ZIP file(s)", 1,
            warning_msg=warning, title="Confirm Extraction"
        )
        if not progress:
            return

        # Reset progress for actual file count
        progress.total_items = len(zip_list)
        progress.progress_bar.config(maximum=len(zip_list))

        self.uncompression_results = {
            'extracted': 0, 'skipped': 0, 'failed': 0, 'errors': []
        }

        self.run_worker_thread(
            self._perform_uncompression,
            args=(zip_list, progress, delete_archives, self.uncompression_results),
            progress=progress,
            on_complete=self._show_uncompression_results
        )

    def delete_selected_zips(self):
        """Delete selected ZIP files from the right pane"""
        if not self.current_folder:
            return

        files = self.get_files_from_tree(self.compressed_tree, self.current_folder, selected_only=True)
        if not files:
            show_info(self.root, "Delete", "Please select ZIP files to delete")
            return

        if not ask_yesno(self.root, "Confirm Delete",
                        f"Delete {len(files)} selected ZIP file(s)?\n\nThis cannot be undone!"):
            return

        deleted, failed, errors = 0, 0, []
        for file_path, _ in files:
            try:
                os.chmod(file_path, 0o777)
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
                failed += 1

        result_msg = self.format_operation_results({'Deleted': deleted, 'Failed': failed}, errors)
        show_info(self.root, "Delete Complete", result_msg)
        self.refresh_compression_lists()

    def delete_archived_roms(self):
        """Delete ONLY ROM files that have corresponding ZIP archives (safe cleanup)"""
        if not self.current_folder:
            return

        # Get files with "Archived" status
        files_to_delete = []
        for item in self.uncompressed_tree.get_children():
            values = self.uncompressed_tree.item(item, "values")
            if len(values) > 2 and values[2] == "Archived":
                full_path = os.path.join(self.current_folder, values[0])
                if os.path.exists(full_path):
                    files_to_delete.append((values[0], full_path))

        if not files_to_delete:
            show_info(self.root, "Delete Archived", "No archived ROM files found to delete")
            return

        confirm_msg = (f"Delete {len(files_to_delete)} archived ROM file(s)?\n\n"
                      "These files all have corresponding ZIP archives.\n"
                      "The ZIP files will NOT be deleted.\n\n"
                      "This cannot be undone. Continue?")
        if not ask_yesno(self.root, "Confirm Delete Archived Files", confirm_msg):
            return

        progress = ProgressDialog(self.root, "Deleting Archived Files", len(files_to_delete))
        self.delete_results = {'deleted': 0, 'failed': 0, 'errors': []}

        def do_delete():
            for idx, (filename, file_path) in enumerate(files_to_delete, 1):
                progress.update(idx, filename)
                try:
                    os.chmod(file_path, 0o777)
                    os.remove(file_path)
                    self.delete_results['deleted'] += 1
                except Exception as e:
                    self.delete_results['errors'].append(f"{filename}: {str(e)}")
                    self.delete_results['failed'] += 1

        def show_results():
            msg = self.format_operation_results(
                {'Deleted': self.delete_results['deleted'], 'Failed': self.delete_results['failed']},
                self.delete_results['errors']
            )
            show_info(self.root, "Delete Complete", msg)
            self.refresh_compression_lists()

        self.run_worker_thread(do_delete, progress=progress, on_complete=show_results)

    def _perform_compression(self, compress_list, progress, delete_originals, results):
        """Perform the actual compression operations (runs in worker thread)"""
        import zipfile

        for idx, file_path in enumerate(compress_list, 1):
            filename = os.path.basename(file_path)
            progress.update(idx, filename)

            try:
                original_size = os.path.getsize(file_path)

                # Skip empty files
                if original_size == 0:
                    results['errors'].append(f"{filename}: Empty file")
                    results['skipped'] += 1
                    continue

                zip_name = os.path.splitext(filename)[0] + ".zip"
                zip_path = os.path.join(self.current_folder, zip_name)

                # Skip if ZIP already exists
                if os.path.exists(zip_path):
                    results['errors'].append(f"{filename}: ZIP already exists")
                    results['skipped'] += 1
                    continue

                # Create ZIP file (level 6 for good balance of speed and compression)
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    zipf.write(file_path, filename)

                # Verify ZIP was created
                if not os.path.exists(zip_path):
                    results['errors'].append(f"{filename}: Failed to create ZIP")
                    results['failed'] += 1
                    continue

                compressed_size = os.path.getsize(zip_path)
                savings = original_size - compressed_size
                results['total_savings'] += savings

                results['compressed'] += 1

                # Delete original if requested
                if delete_originals:
                    try:
                        # Remove read-only attribute if present
                        if os.path.exists(file_path):
                            os.chmod(file_path, 0o777)
                            os.remove(file_path)
                    except Exception as e:
                        results['errors'].append(f"{filename}: Compressed but failed to delete original - {str(e)}")

            except Exception as e:
                results['errors'].append(f"{filename}: {str(e)}")
                results['failed'] += 1

    def _show_compression_results(self):
        """Show compression results and update UI (runs in main thread)"""
        results = self.compression_results

        # Calculate total savings
        total_savings_mb = results['total_savings'] / (1024 * 1024)

        # Show results
        result_msg = f"Files compressed: {results['compressed']}\n"
        result_msg += f"Files skipped: {results['skipped']}\n"
        result_msg += f"Files failed: {results['failed']}\n"
        result_msg += f"Space saved: {total_savings_mb:.2f} MB"

        if results['errors']:
            result_msg += f"\n\nIssues ({len(results['errors'])}):\n" + "\n".join(results['errors'][:10])
            if len(results['errors']) > 10:
                result_msg += f"\n... and {len(results['errors']) - 10} more"

        show_info(self.root, "Compression Complete", result_msg)

        # Refresh the compression lists
        self.refresh_compression_lists()

    def _perform_uncompression(self, zip_files, progress, delete_zips, results):
        """Perform the actual uncompression operations (runs in worker thread)"""
        import zipfile

        for idx, zip_path in enumerate(zip_files, 1):
            zip_filename = os.path.basename(zip_path)
            progress.update(idx, zip_filename)

            try:
                # Verify it's a valid ZIP file
                if not zipfile.is_zipfile(zip_path):
                    results['errors'].append(f"{zip_filename}: Not a valid ZIP file")
                    results['skipped'] += 1
                    continue

                # Extract ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    # Get list of files in the ZIP
                    file_list = zipf.namelist()

                    # Check if any files would be overwritten
                    existing_files = []
                    for filename in file_list:
                        target_path = os.path.join(self.current_folder, filename)
                        if os.path.exists(target_path):
                            existing_files.append(filename)

                    # Skip if files would be overwritten
                    if existing_files:
                        results['errors'].append(f"{zip_filename}: Would overwrite {len(existing_files)} file(s)")
                        results['skipped'] += 1
                        continue

                    # Extract all files
                    zipf.extractall(self.current_folder)

                results['extracted'] += 1

                # Delete ZIP if requested
                if delete_zips:
                    try:
                        os.remove(zip_path)
                    except Exception as e:
                        results['errors'].append(f"{zip_filename}: Extracted but failed to delete ZIP - {str(e)}")

            except Exception as e:
                results['errors'].append(f"{zip_filename}: {str(e)}")
                results['failed'] += 1

    def _show_uncompression_results(self):
        """Show uncompression results and update UI (runs in main thread)"""
        results = self.uncompression_results

        # Show results
        result_msg = f"ZIP files extracted: {results['extracted']}\n"
        result_msg += f"ZIP files skipped: {results['skipped']}\n"
        result_msg += f"ZIP files failed: {results['failed']}"

        if results['errors']:
            result_msg += f"\n\nIssues ({len(results['errors'])}):\n" + "\n".join(results['errors'][:10])
            if len(results['errors']) > 10:
                result_msg += f"\n... and {len(results['errors']) - 10} more"

        show_info(self.root, "Extraction Complete", result_msg)

        # Refresh the compression lists
        self.refresh_compression_lists()

    # ========== DUPLICATES TAB METHODS ==========

    def start_duplicate_scan(self):
        """Start scanning for duplicate files"""
        if not self.current_folder or not os.path.exists(self.current_folder):
            show_warning(self.root, "No Folder", "Please select a ROM folder first using the Browse button at the top")
            return
        scan_folder = self.current_folder

        # Clear previous results
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)
        self.duplicate_groups = {}
        self.file_hashes = {}

        # Update UI state
        self.scan_running = True
        self.scan_cancelled = False
        self.start_scan_btn.config(state="disabled")
        self.stop_scan_btn.config(state="normal")
        self.dup_progress_var.set(0)
        self.dup_scan_status_var.set("Preparing scan...")
        self.dup_summary_var.set("Scanning...")

        # Start scan in background thread
        scan_thread = threading.Thread(target=self._scan_files_worker, args=(scan_folder,), daemon=True)
        scan_thread.start()

    def stop_duplicate_scan(self):
        """Stop the currently running scan"""
        self.scan_cancelled = True
        self.dup_scan_status_var.set("Cancelling...")
        self.stop_scan_btn.config(state="disabled")

    def _scan_files_worker(self, scan_folder):
        """Background worker thread for scanning and hashing files"""
        try:
            # Reset cache hit counter for this scan
            self.cache_hits = 0

            # Get list of files to scan based on mode
            scan_mode = self.scan_mode.get()
            filter_mode = self.dup_filter_mode.get()
            files_to_scan = []
            filtered_count = 0

            if scan_mode == "folder_only":
                # Only files in the selected folder
                for item in os.listdir(scan_folder):
                    full_path = os.path.join(scan_folder, item)
                    if os.path.isfile(full_path):
                        if self.should_include_file(full_path, filter_mode):
                            files_to_scan.append(full_path)
                        else:
                            filtered_count += 1

            elif scan_mode == "with_subfolders":
                # All files in folder and subfolders
                for root, dirs, files in os.walk(scan_folder):
                    if self.scan_cancelled:
                        break
                    # Skip excluded folders
                    if filter_mode == "rom_only":
                        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                    for filename in files:
                        full_path = os.path.join(root, filename)
                        if self.should_include_file(full_path, filter_mode):
                            files_to_scan.append(full_path)
                        else:
                            filtered_count += 1

            elif scan_mode == "all_rom_folders":
                # Scan parent directory
                parent_dir = os.path.dirname(scan_folder)
                if parent_dir:
                    for root, dirs, files in os.walk(parent_dir):
                        if self.scan_cancelled:
                            break
                        # Skip excluded folders
                        if filter_mode == "rom_only":
                            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                        for filename in files:
                            full_path = os.path.join(root, filename)
                            if self.should_include_file(full_path, filter_mode):
                                files_to_scan.append(full_path)
                            else:
                                filtered_count += 1
                else:
                    # No parent, just scan current
                    for root, dirs, files_list in os.walk(scan_folder):
                        if self.scan_cancelled:
                            break
                        # Skip excluded folders
                        if filter_mode == "rom_only":
                            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                        for filename in files_list:
                            full_path = os.path.join(root, filename)
                            if self.should_include_file(full_path, filter_mode):
                                files_to_scan.append(full_path)
                            else:
                                filtered_count += 1

            if self.scan_cancelled:
                self.root.after(0, self._scan_cancelled)
                return

            total_files = len(files_to_scan)
            if total_files == 0:
                self.root.after(0, lambda: show_info(self.root, "No Files", "No files found to scan"))
                self.root.after(0, self._scan_complete)
                return

            # Hash all files
            hash_method = self.hash_method.get()
            hashed_count = 0
            hash_dict = {}  # hash -> [file_paths]

            for file_path in files_to_scan:
                if self.scan_cancelled:
                    self.root.after(0, self._scan_cancelled)
                    return

                hashed_count += 1
                filename = os.path.basename(file_path)

                # Update progress
                progress = int((hashed_count / total_files) * 100)
                duplicate_count = sum(1 for files in hash_dict.values() if len(files) > 1)
                total_dup_files = sum(len(files) for files in hash_dict.values() if len(files) > 1)

                status_text = f"Scanning: {hashed_count}/{total_files} files | Hashing: {filename[:40]}"
                if duplicate_count > 0:
                    status_text += f" | Found: {duplicate_count} groups ({total_dup_files} files)"

                self.root.after(0, lambda p=progress, s=status_text: self._update_scan_progress(p, s))

                # Calculate hash
                try:
                    file_hash = self._hash_file(file_path, hash_method)
                    if file_hash:
                        self.file_hashes[file_path] = file_hash
                        if file_hash not in hash_dict:
                            hash_dict[file_hash] = []
                        hash_dict[file_hash].append(file_path)
                except Exception as e:
                    # Skip files that can't be hashed
                    continue

            # Filter to only actual duplicates (2+ files with same hash)
            self.duplicate_groups = {h: files for h, files in hash_dict.items() if len(files) > 1}

            # Store filtered count for display
            self.last_filtered_count = filtered_count

            # Save hash cache to disk
            save_hash_cache(self.hash_cache)

            # Display results
            self.root.after(0, lambda: self._display_duplicate_groups())
            self.root.after(0, self._scan_complete)

        except Exception as e:
            error_msg = f"Scan error: {str(e)}"
            self.root.after(0, lambda: show_error(self.root, "Scan Error", error_msg))
            self.root.after(0, self._scan_complete)

    def _hash_file(self, file_path, method='sha1'):
        """Calculate hash of a file (with caching based on file size and mtime)"""
        try:
            # Get file metadata for cache key
            stat = os.stat(file_path)
            file_size = stat.st_size
            file_mtime = stat.st_mtime

            # Create cache key: path|size|mtime|method
            cache_key = f"{file_path}|{file_size}|{file_mtime}|{method}"

            # Check cache first
            if cache_key in self.hash_cache:
                self.cache_hits += 1
                return self.hash_cache[cache_key]

            # Cache miss - calculate hash
            if method == 'md5':
                hasher = hashlib.md5()
            else:  # sha1
                hasher = hashlib.sha1()

            # Read file in large chunks for performance (1MB)
            with open(file_path, 'rb') as f:
                while chunk := f.read(1048576):
                    hasher.update(chunk)

            file_hash = hasher.hexdigest()

            # Store in cache
            self.hash_cache[cache_key] = file_hash

            return file_hash
        except:
            return None

    def _update_scan_progress(self, progress, status_text):
        """Update scan progress (called from main thread)"""
        self.dup_progress_var.set(progress)
        self.dup_scan_status_var.set(status_text)

    def _scan_complete(self):
        """Called when scan completes"""
        self.scan_running = False
        self.start_scan_btn.config(state="normal")
        self.stop_scan_btn.config(state="disabled")

    def _scan_cancelled(self):
        """Called when scan is cancelled"""
        self.scan_running = False
        self.start_scan_btn.config(state="normal")
        self.stop_scan_btn.config(state="disabled")
        self.dup_scan_status_var.set("Scan cancelled")
        self.dup_summary_var.set("Scan cancelled - click 'Start Scan' to try again")

    def _display_duplicate_groups(self):
        """Display duplicate groups in the tree view"""
        # Clear existing items
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)

        # Filter out deleted files from duplicate_groups
        cleaned_groups = {}
        for file_hash, file_paths in self.duplicate_groups.items():
            existing_files = [f for f in file_paths if os.path.exists(f)]
            # Only keep groups with 2+ files (still duplicates)
            if len(existing_files) >= 2:
                cleaned_groups[file_hash] = existing_files
        self.duplicate_groups = cleaned_groups

        if not self.duplicate_groups:
            self.dup_summary_var.set("✨ No duplicates detected - your collection is clean!")
            self.dup_scan_status_var.set("Scan complete")
            self.delete_duplicates_btn.config(state="disabled")
            return

        # Calculate statistics
        total_groups = len(self.duplicate_groups)
        total_dup_files = sum(len(files) for files in self.duplicate_groups.values())
        total_wasted_space = 0

        # Sort groups by wasted space (largest first)
        sorted_groups = []
        for file_hash, file_paths in self.duplicate_groups.items():
            # Calculate wasted space (all but one file)
            if file_paths:
                try:
                    file_size = os.path.getsize(file_paths[0])
                    wasted = file_size * (len(file_paths) - 1)
                    total_wasted_space += wasted
                    sorted_groups.append((wasted, file_hash, file_paths))
                except OSError:
                    continue  # Skip if file is inaccessible

        sorted_groups.sort(reverse=True)

        # Display groups
        for idx, (wasted, file_hash, file_paths) in enumerate(sorted_groups, 1):
            if not file_paths:
                continue

            # Group header
            first_file = os.path.basename(file_paths[0])
            num_copies = len(file_paths)
            wasted_mb = wasted / (1024 * 1024)

            group_text = f"Group {idx}: {first_file} ({num_copies} copies, {wasted_mb:.1f} MB wasted)"

            # Insert group (selected by default with checkbox, expanded by default)
            group_id = self.dup_tree.insert("", tk.END, text=group_text,
                                          values=("☑", "", "", "", "", ""), open=True)

            # Mark group as selected by default
            self.group_selection[group_id] = True

            # Add files to group
            for file_idx, file_path in enumerate(file_paths):
                try:
                    filename = os.path.basename(file_path)
                    dir_path = os.path.dirname(file_path)
                    file_size = os.path.getsize(file_path)

                    # Get file modification date
                    try:
                        mod_time = os.path.getmtime(file_path)
                        mod_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                    except:
                        mod_date = "Unknown"

                    # First file is marked as "Keep" by default
                    action = "Keep" if file_idx == 0 else "Delete"
                    tag = "keep" if file_idx == 0 else "delete"

                    self.dup_tree.insert(group_id, tk.END,
                                        values=("", filename, mod_date, self.format_size(file_size), action, dir_path),
                                        tags=(tag, file_hash, file_path))
                except OSError:
                    continue  # Skip files that no longer exist or are inaccessible

        # Update summary
        wasted_gb = total_wasted_space / (1024 * 1024 * 1024)
        summary = f"Duplicate Groups: {total_groups} groups found | {total_dup_files} duplicate files | {wasted_gb:.2f} GB wasted space"

        # Add filtering statistics if files were filtered
        filtered_count = getattr(self, 'last_filtered_count', 0)
        if filtered_count > 0:
            summary += f" | Ignored {filtered_count} non-ROM files"

        # Add cache hit statistics
        if self.cache_hits > 0:
            summary += f" | Cache: {self.cache_hits} hits"

        self.dup_summary_var.set(summary)
        self.dup_scan_status_var.set("Scan complete")
        self.delete_duplicates_btn.config(state="normal")

        # Update delete button text with initial counts
        self._update_delete_button_text()

    def apply_auto_selection(self):
        """Apply auto-selection strategy to all groups"""
        strategy_text = self.auto_select_strategy.get()

        if strategy_text == "Manual selection only":
            return

        if not self.duplicate_groups:
            show_info(self.root, "No Data", "No duplicates found. Please run a scan first.")
            return

        # Map strategy text to strategy key
        strategy_map = {
            "Keep by filename pattern (USA > Europe > Japan)": "pattern",
            "Keep largest file": "largest",
            "Keep smallest file": "smallest",
            "Keep oldest (by date)": "oldest",
            "Keep newest (by date)": "newest"
        }

        strategy = strategy_map.get(strategy_text, "manual")
        if strategy == "manual":
            return

        # Apply strategy to each group
        changed_count = 0
        for group in self.dup_tree.get_children():
            children = self.dup_tree.get_children(group)
            if not children:
                continue

            # Get file information for all children
            file_info = []
            for child in children:
                tags = self.dup_tree.item(child, "tags")
                file_path = tags[-1] if tags else None
                if not file_path or not os.path.exists(file_path):
                    continue

                filename = self.dup_tree.set(child, "filename")
                size_str = self.dup_tree.set(child, "size")
                date_str = self.dup_tree.set(child, "date")

                file_info.append({
                    'child': child,
                    'path': file_path,
                    'filename': filename,
                    'size': self.parse_size(size_str),
                    'date_str': date_str,
                    'tags': tags
                })

            if not file_info:
                continue

            # Select file to keep based on strategy
            keep_file = None

            if strategy == "pattern":
                # Prefer: (USA) > (U) > (World) > (Europe) > (E) > (Japan) > (J)
                # Also prefer (Rev 1) and cleaner names
                region_priority = {
                    'usa': 100,
                    '(usa)': 100,
                    '(u)': 90,
                    '(world)': 80,
                    'europe': 70,
                    '(europe)': 70,
                    '(e)': 60,
                    'japan': 50,
                    '(japan)': 50,
                    '(j)': 40
                }

                best_score = -1
                for info in file_info:
                    filename_lower = info['filename'].lower()
                    score = 0

                    # Check region tags
                    for region, priority in region_priority.items():
                        if region in filename_lower:
                            score = max(score, priority)

                    # Prefer Rev 1 over base
                    if 'rev 1' in filename_lower or 'rev1' in filename_lower:
                        score += 10

                    # Prefer cleaner names (fewer brackets)
                    bracket_count = filename_lower.count('(') + filename_lower.count('[')
                    score -= bracket_count

                    if score > best_score:
                        best_score = score
                        keep_file = info

                # If no pattern matched, keep first file
                if not keep_file:
                    keep_file = file_info[0]

            elif strategy == "largest":
                keep_file = max(file_info, key=lambda x: x['size'])

            elif strategy == "smallest":
                keep_file = min(file_info, key=lambda x: x['size'])

            elif strategy == "oldest" or strategy == "newest":
                # Parse dates and sort
                dated_files = []
                for info in file_info:
                    try:
                        mod_time = os.path.getmtime(info['path'])
                        dated_files.append((mod_time, info))
                    except:
                        pass

                if dated_files:
                    dated_files.sort(key=lambda x: x[0])
                    if strategy == "oldest":
                        keep_file = dated_files[0][1]
                    else:  # newest
                        keep_file = dated_files[-1][1]
                else:
                    keep_file = file_info[0]

            # Apply selection
            if keep_file:
                # Mark all as Delete first
                for info in file_info:
                    self.dup_tree.set(info['child'], "action", "Delete")
                    new_tags = [t for t in info['tags'] if t not in ["keep", "delete"]]
                    new_tags.append("delete")
                    self.dup_tree.item(info['child'], tags=tuple(new_tags))

                # Mark selected file as Keep
                self.dup_tree.set(keep_file['child'], "action", "Keep")
                new_tags = [t for t in keep_file['tags'] if t not in ["keep", "delete"]]
                new_tags.append("keep")
                self.dup_tree.item(keep_file['child'], tags=tuple(new_tags))
                changed_count += 1

        # Update delete button
        self._update_delete_button_text()

        show_info(self.root, "Auto-Selection Complete",
                 f"Applied '{strategy_text}' strategy to {changed_count} groups")

    def select_all_groups(self):
        """Select all duplicate groups"""
        for group in self.dup_tree.get_children():
            self.group_selection[group] = True
            self.dup_tree.set(group, "select", "☑")
        self._update_delete_button_text()

    def deselect_all_groups(self):
        """Deselect all duplicate groups"""
        for group in self.dup_tree.get_children():
            self.group_selection[group] = False
            self.dup_tree.set(group, "select", "☐")
        self._update_delete_button_text()

    def expand_all_groups(self):
        """Expand all duplicate groups"""
        for item in self.dup_tree.get_children():
            self.dup_tree.item(item, open=True)

    def collapse_all_groups(self):
        """Collapse all duplicate groups"""
        for item in self.dup_tree.get_children():
            self.dup_tree.item(item, open=False)

    def _on_dup_tree_click(self, event):
        """Handle click on duplicate tree to toggle Keep/Delete or group selection"""
        try:
            item = self.dup_tree.identify_row(event.y)
            if not item:
                return

            # Check which region was clicked
            region = self.dup_tree.identify_region(event.x, event.y)

            # If clicked on tree indicator (+/- button), let default behavior happen
            if region == "tree":
                return

            # Get which column was clicked
            column = self.dup_tree.identify_column(event.x)

            # Check if this is a child item (not a group header)
            parent = self.dup_tree.parent(item)

            # Handle group checkbox click
            if not parent and column == "#1":  # Group header, select column
                # Toggle group selection
                current_state = self.group_selection.get(item, True)
                self.group_selection[item] = not current_state

                # Update checkbox
                new_checkbox = "☐" if current_state else "☑"
                self.dup_tree.set(item, "select", new_checkbox)

                # Update delete button
                self._update_delete_button_text()
                return "break"

            if not parent:
                # Clicked on group but not on checkbox column, don't do anything
                return

            # Get current tags
            tags = self.dup_tree.item(item, "tags")
            if not tags:
                return

            # Find the file hash (stored in tags)
            file_hash = None
            file_path = None
            for tag in tags:
                if tag not in ["keep", "delete"]:
                    # Assume first non-action tag is the hash or path
                    if os.path.exists(tag):
                        file_path = tag
                    else:
                        file_hash = tag

            if not file_path:
                # Try to get file_path from tags (it's the last tag)
                if len(tags) > 2:
                    file_path = tags[-1]

            # Get all siblings (files in the same group)
            siblings = self.dup_tree.get_children(parent)

            # Determine new action
            current_action = self.dup_tree.set(item, "action")
            if current_action == "Keep":
                # Trying to unmark Keep - need to mark another file as Keep
                # Find the first Delete file and make it Keep instead
                for sibling in siblings:
                    if sibling != item:
                        sibling_action = self.dup_tree.set(sibling, "action")
                        if sibling_action == "Delete":
                            # Make this sibling Keep instead
                            self.dup_tree.set(sibling, "action", "Keep")
                            sibling_tags = list(self.dup_tree.item(sibling, "tags"))
                            sibling_tags = [t for t in sibling_tags if t not in ["keep", "delete"]]
                            sibling_tags.append("keep")
                            self.dup_tree.item(sibling, tags=tuple(sibling_tags))
                            break

                # Mark this item as Delete
                self.dup_tree.set(item, "action", "Delete")
                new_tags = [t for t in tags if t not in ["keep", "delete"]]
                new_tags.append("delete")
                self.dup_tree.item(item, tags=tuple(new_tags))
            else:
                # Currently Delete, change to Keep
                # First, unmark all siblings as Keep
                for sibling in siblings:
                    sibling_tags = list(self.dup_tree.item(sibling, "tags"))
                    if "keep" in sibling_tags:
                        self.dup_tree.set(sibling, "action", "Delete")
                        sibling_tags = [t for t in sibling_tags if t not in ["keep", "delete"]]
                        sibling_tags.append("delete")
                        self.dup_tree.item(sibling, tags=tuple(sibling_tags))

                # Mark this item as Keep
                self.dup_tree.set(item, "action", "Keep")
                new_tags = [t for t in tags if t not in ["keep", "delete"]]
                new_tags.append("keep")
                self.dup_tree.item(item, tags=tuple(new_tags))

            # Update delete button text with count
            self._update_delete_button_text()
        except Exception:
            pass  # Silently ignore click handling errors

    def _update_delete_button_text(self):
        """Update the delete button to show count of files to delete (only from checked groups)"""
        delete_count = 0
        total_size = 0
        checked_groups = 0

        # Count files marked for deletion in CHECKED groups only
        for group in self.dup_tree.get_children():
            # Check if group is selected
            if not self.group_selection.get(group, True):
                continue  # Skip unchecked groups

            checked_groups += 1
            for child in self.dup_tree.get_children(group):
                action = self.dup_tree.set(child, "action")
                if action == "Delete":
                    delete_count += 1
                    # Parse size
                    size_str = self.dup_tree.set(child, "size")
                    size_bytes = self.parse_size(size_str)
                    total_size += size_bytes

        if delete_count > 0:
            size_gb = total_size / (1024 * 1024 * 1024)
            if size_gb >= 0.1:
                self.delete_duplicates_btn.config(
                    text=f"Delete Selected ({checked_groups} groups, {delete_count} files, {size_gb:.1f} GB)",
                    state="normal")
            else:
                size_mb = total_size / (1024 * 1024)
                self.delete_duplicates_btn.config(
                    text=f"Delete Selected ({checked_groups} groups, {delete_count} files, {size_mb:.1f} MB)",
                    state="normal")
        else:
            self.delete_duplicates_btn.config(text="Delete Selected (0 groups)", state="disabled")

    def delete_duplicates(self):
        """Delete files marked for deletion from selected groups"""
        if not self.duplicate_groups:
            show_info(self.root, "No Data", "No duplicates found. Please run a scan first.")
            return

        # Count files to delete from selected groups
        files_to_delete = []
        total_size = 0
        selected_groups = 0

        for group in self.dup_tree.get_children():
            # Only process selected groups
            if not self.group_selection.get(group, True):
                continue

            selected_groups += 1
            for child in self.dup_tree.get_children(group):
                action = self.dup_tree.set(child, "action")
                if action == "Delete":
                    # Get file path from tags
                    tags = self.dup_tree.item(child, "tags")
                    file_path = None
                    for tag in tags:
                        if os.path.exists(tag):
                            file_path = tag
                            break

                    if file_path:
                        size_str = self.dup_tree.set(child, "size")
                        size_bytes = self.parse_size(size_str)
                        files_to_delete.append((file_path, size_bytes))
                        total_size += size_bytes

        if not files_to_delete:
            show_info(self.root, "No Files to Delete",
                     "No files are marked for deletion in the selected groups.")
            return

        # Confirm deletion
        size_mb = total_size / (1024 * 1024)
        size_gb = total_size / (1024 * 1024 * 1024)

        if size_gb >= 0.1:
            size_text = f"{size_gb:.2f} GB"
        else:
            size_text = f"{size_mb:.2f} MB"

        message = (f"Are you sure you want to delete {len(files_to_delete)} duplicate files "
                  f"from {selected_groups} selected group(s)?\n\n"
                  f"Total space to recover: {size_text}\n\n"
                  f"This action cannot be undone!")

        if not ask_yesno(self.root, "Confirm Deletion", message):
            return

        # Create progress dialog
        progress = ProgressDialog(self.root, "Deleting Duplicates", len(files_to_delete))

        def delete_worker():
            deleted_count = 0
            failed_files = []

            for i, (file_path, size) in enumerate(files_to_delete):
                try:
                    # Update progress
                    progress.update(i + 1, os.path.basename(file_path))

                    # Delete the file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1

                except Exception as e:
                    failed_files.append((file_path, str(e)))

            progress.close()

            # Show results
            if failed_files:
                error_msg = f"Deleted {deleted_count} of {len(files_to_delete)} files.\n\n"
                error_msg += "Failed to delete:\n"
                for path, error in failed_files[:5]:  # Show first 5 errors
                    error_msg += f"  • {os.path.basename(path)}: {error}\n"
                if len(failed_files) > 5:
                    error_msg += f"  ... and {len(failed_files) - 5} more"
                show_error(self.root, "Deletion Incomplete", error_msg)
            else:
                show_info(self.root, "Deletion Complete",
                         f"Successfully deleted {deleted_count} duplicate files!")

            # Update the display without rescanning
            self.root.after(100, lambda: self._display_duplicate_groups())

        # Start deletion in background thread
        thread = threading.Thread(target=delete_worker, daemon=True)
        thread.start()

    def export_duplicates_list(self):
        """Export duplicate list to text file"""
        if not self.duplicate_groups:
            show_info(self.root, "No Data", "No duplicates to export. Please run a scan first.")
            return

        # Ask user for save location with default filename
        export_file_path = filedialog.asksaveasfilename(
            title="Export Duplicates List",
            defaultextension=".txt",
            initialfile="duplicates.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not export_file_path:
            return  # User cancelled

        try:
            with open(export_file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write("=" * 80 + "\n")
                f.write("ROM MANAGER - DUPLICATE FILES REPORT\n")
                f.write("=" * 80 + "\n\n")

                # Write summary
                total_groups = len(self.duplicate_groups)
                total_files = sum(len(files) for files in self.duplicate_groups.values())
                total_wasted = 0

                for file_hash, file_paths in self.duplicate_groups.items():
                    if file_paths:
                        file_size = os.path.getsize(file_paths[0])
                        total_wasted += file_size * (len(file_paths) - 1)

                wasted_gb = total_wasted / (1024 * 1024 * 1024)

                f.write(f"Total Duplicate Groups: {total_groups}\n")
                f.write(f"Total Duplicate Files: {total_files}\n")
                f.write(f"Total Wasted Space: {wasted_gb:.2f} GB\n\n")

                # Write scan details
                f.write(f"Scan Folder: {self.current_folder}\n")
                f.write(f"Scan Mode: {self.scan_mode.get()}\n")
                f.write(f"Hash Method: {self.hash_method.get().upper()}\n")
                f.write("\n" + "=" * 80 + "\n\n")

                # Get sorted groups (same as display)
                sorted_groups = []
                for file_hash, file_paths in self.duplicate_groups.items():
                    if file_paths:
                        file_size = os.path.getsize(file_paths[0])
                        wasted = file_size * (len(file_paths) - 1)
                        sorted_groups.append((wasted, file_hash, file_paths))
                sorted_groups.sort(reverse=True)

                # Build a map of file paths to actions from the tree view
                file_to_action = {}
                for group in self.dup_tree.get_children():
                    for child in self.dup_tree.get_children(group):
                        child_tags = self.dup_tree.item(child, "tags")
                        if len(child_tags) >= 3:  # Expecting (tag, file_hash, file_path)
                            child_path = child_tags[2]  # File path is third element
                            child_values = self.dup_tree.item(child, "values")
                            if len(child_values) >= 5:  # Get action from column 4 (index 4)
                                action = child_values[4]
                                file_to_action[child_path] = action

                # Write each group
                for idx, (wasted, file_hash, file_paths) in enumerate(sorted_groups, 1):
                    wasted_mb = wasted / (1024 * 1024)
                    f.write(f"GROUP {idx}: {len(file_paths)} copies, {wasted_mb:.1f} MB wasted\n")
                    f.write(f"Hash: {file_hash}\n")
                    f.write("-" * 80 + "\n")

                    # Write files
                    for file_path in file_paths:
                        filename = os.path.basename(file_path)
                        file_size = os.path.getsize(file_path)
                        action = file_to_action.get(file_path, "Delete")

                        f.write(f"  [{action:6}] {filename}\n")
                        f.write(f"           Size: {self.format_size(file_size)}\n")
                        f.write(f"           Path: {file_path}\n")

                    f.write("\n")

                # Write footer
                f.write("=" * 80 + "\n")
                f.write("End of Report\n")

            show_info(self.root, "Export Complete", f"Duplicate list exported to:\n{export_file_path}")

        except Exception as e:
            show_error(self.root, "Export Error", f"Failed to export list:\n{str(e)}")


    # === COMPARE COLLECTIONS TAB METHODS ===

    def browse_collection_a(self):
        """Browse for Collection A folder"""
        folder = filedialog.askdirectory(title="Select Collection A Folder")
        if folder:
            self.compare_path_a_var.set(folder)

    def browse_collection_b(self):
        """Browse for Collection B folder"""
        folder = filedialog.askdirectory(title="Select Collection B Folder")
        if folder:
            self.compare_path_b_var.set(folder)

    def on_compare_method_change(self):
        """Enable/disable verify integrity checkbox based on compare method"""
        if self.compare_method.get() == "quick":
            self.verify_integrity_cb.config(state="normal")
        else:
            self.verify_integrity_cb.config(state="disabled")

    def start_compare(self):
        """Start the collection comparison"""
        path_a = self.compare_path_a_var.get()
        path_b = self.compare_path_b_var.get()

        if not path_a or not path_b:
            show_error(self.root, "Missing Paths", "Please select both Collection A and Collection B folders.")
            return

        if not os.path.exists(path_a) or not os.path.exists(path_b):
            show_error(self.root, "Invalid Paths", "One or both collection paths do not exist.")
            return

        # Clear previous results
        for item in self.compare_tree_a.get_children():
            self.compare_tree_a.delete(item)
        for item in self.compare_tree_b.get_children():
            self.compare_tree_b.delete(item)
        self.compare_selection_a.clear()
        self.compare_selection_b.clear()

        # Prevent system sleep during comparison
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            self.compare_status_var.set("⚠️ System sleep disabled during comparison")
        except:
            pass  # If Windows API fails, continue anyway

        # Run comparison in background thread
        method = self.compare_method.get()
        if method == "quick":
            verify = self.verify_integrity.get()
            thread = threading.Thread(target=self._quick_compare_worker,
                                    args=(path_a, path_b, verify), daemon=True)
        else:
            thread = threading.Thread(target=self._deep_compare_worker,
                                    args=(path_a, path_b), daemon=True)
        thread.start()

    def _quick_compare_worker(self, path_a, path_b, verify_integrity):
        """Quick comparison by filename"""
        try:
            filter_mode = self.compare_filter_mode.get()
            self.compare_status_var.set("Scanning collections...")
            self.compare_progress_var.set(0)

            # Get all files in both collections with filtering
            files_a = {}  # filename -> full_path
            files_b = {}  # filename -> full_path
            filtered_count_a = 0
            filtered_count_b = 0

            for root, dirs, files in os.walk(path_a):
                # Skip excluded folders
                if filter_mode == "rom_only":
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]

                for file in files:
                    full_path = os.path.join(root, file)
                    if self.should_include_file(full_path, filter_mode):
                        files_a[file] = full_path
                    else:
                        filtered_count_a += 1

            for root, dirs, files in os.walk(path_b):
                # Skip excluded folders
                if filter_mode == "rom_only":
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]

                for file in files:
                    full_path = os.path.join(root, file)
                    if self.should_include_file(full_path, filter_mode):
                        files_b[file] = full_path
                    else:
                        filtered_count_b += 1

            # Find differences
            only_in_a = set(files_a.keys()) - set(files_b.keys())
            only_in_b = set(files_b.keys()) - set(files_a.keys())
            in_both = set(files_a.keys()) & set(files_b.keys())

            self.compare_status_var.set("Analyzing differences...")
            self.compare_progress_var.set(50)

            # Store results
            only_a_list = []
            for filename in sorted(only_in_a):
                full_path = files_a[filename]
                size = os.path.getsize(full_path)
                mod_time = os.path.getmtime(full_path)
                from datetime import datetime
                date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                only_a_list.append((filename, full_path, size, date_str))

            only_b_list = []
            for filename in sorted(only_in_b):
                full_path = files_b[filename]
                size = os.path.getsize(full_path)
                mod_time = os.path.getmtime(full_path)
                from datetime import datetime
                date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                only_b_list.append((filename, full_path, size, date_str))

            # Verify integrity if requested
            corrupted = []
            if verify_integrity and in_both:
                self.compare_status_var.set("Verifying file integrity...")
                total_both = len(in_both)
                for idx, filename in enumerate(in_both):
                    path_a_file = files_a[filename]
                    path_b_file = files_b[filename]

                    # Hash both files
                    hash_a = self._hash_file_quick(path_a_file)
                    hash_b = self._hash_file_quick(path_b_file)

                    if hash_a != hash_b:
                        corrupted.append(filename)

                    if (idx + 1) % 10 == 0:
                        progress = 50 + int((idx + 1) / total_both * 50)
                        self.compare_progress_var.set(progress)
                        self.compare_status_var.set(f"Verifying integrity... {idx + 1}/{total_both}")

            self.compare_results = {
                "only_a": only_a_list,
                "only_b": only_b_list,
                "both": list(in_both),
                "corrupted": corrupted,
                "filtered_a": filtered_count_a,
                "filtered_b": filtered_count_b
            }

            # Update UI in main thread
            self.root.after(0, self._display_compare_results)

        except Exception as e:
            self.root.after(0, lambda: show_error(self.root, "Comparison Error", str(e)))
            self.compare_status_var.set("Error during comparison")

        finally:
            # Restore normal sleep behavior
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except:
                pass

    def _deep_compare_worker(self, path_a, path_b):
        """Deep comparison by content hash"""
        try:
            filter_mode = self.compare_filter_mode.get()
            self.compare_status_var.set("Hashing Collection A...")
            self.compare_progress_var.set(0)

            # Hash all files in Collection A with filtering
            hashes_a = {}  # hash -> (filename, full_path, size, date)
            files_a = []
            filtered_count_a = 0

            for root, dirs, files in os.walk(path_a):
                # Skip excluded folders
                if filter_mode == "rom_only":
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]

                for file in files:
                    full_path = os.path.join(root, file)
                    if self.should_include_file(full_path, filter_mode):
                        files_a.append((file, full_path))
                    else:
                        filtered_count_a += 1

            total_a = len(files_a)
            for idx, (filename, full_path) in enumerate(files_a):
                file_hash = self._hash_file_quick(full_path)
                size = os.path.getsize(full_path)
                mod_time = os.path.getmtime(full_path)
                from datetime import datetime
                date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

                if file_hash in hashes_a:
                    # Duplicate within Collection A - keep first one
                    pass
                else:
                    hashes_a[file_hash] = (filename, full_path, size, date_str)

                if (idx + 1) % 10 == 0 or idx == total_a - 1:
                    progress = int((idx + 1) / total_a * 50)
                    self.compare_progress_var.set(progress)
                    self.compare_status_var.set(f"Hashing Collection A... {idx + 1}/{total_a}")

            # Hash all files in Collection B with filtering
            self.compare_status_var.set("Hashing Collection B...")
            hashes_b = {}  # hash -> (filename, full_path, size, date)
            files_b = []
            filtered_count_b = 0

            for root, dirs, files in os.walk(path_b):
                # Skip excluded folders
                if filter_mode == "rom_only":
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]

                for file in files:
                    full_path = os.path.join(root, file)
                    if self.should_include_file(full_path, filter_mode):
                        files_b.append((file, full_path))
                    else:
                        filtered_count_b += 1

            total_b = len(files_b)
            for idx, (filename, full_path) in enumerate(files_b):
                file_hash = self._hash_file_quick(full_path)
                size = os.path.getsize(full_path)
                mod_time = os.path.getmtime(full_path)
                from datetime import datetime
                date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

                if file_hash in hashes_b:
                    # Duplicate within Collection B - keep first one
                    pass
                else:
                    hashes_b[file_hash] = (filename, full_path, size, date_str)

                if (idx + 1) % 10 == 0 or idx == total_b - 1:
                    progress = 50 + int((idx + 1) / total_b * 50)
                    self.compare_progress_var.set(progress)
                    self.compare_status_var.set(f"Hashing Collection B... {idx + 1}/{total_b}")

            # Find differences
            only_in_a_hashes = set(hashes_a.keys()) - set(hashes_b.keys())
            only_in_b_hashes = set(hashes_b.keys()) - set(hashes_a.keys())
            in_both_hashes = set(hashes_a.keys()) & set(hashes_b.keys())

            only_a_list = [hashes_a[h] for h in sorted(only_in_a_hashes)]
            only_b_list = [hashes_b[h] for h in sorted(only_in_b_hashes)]

            self.compare_results = {
                "only_a": only_a_list,
                "only_b": only_b_list,
                "both": list(in_both_hashes),
                "corrupted": [],  # Deep compare doesn't check corruption
                "filtered_a": filtered_count_a,
                "filtered_b": filtered_count_b
            }

            # Update UI in main thread
            self.root.after(0, self._display_compare_results)

        except Exception as e:
            self.root.after(0, lambda: show_error(self.root, "Comparison Error", str(e)))
            self.compare_status_var.set("Error during comparison")

        finally:
            # Restore normal sleep behavior
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            except:
                pass

    def _hash_file_quick(self, file_path, algorithm="sha1"):
        """Quick hash for comparison"""
        hasher = hashlib.sha1() if algorithm == "sha1" else hashlib.md5()

        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(1048576):  # 1MB chunks
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None

    def _display_compare_results(self):
        """Display comparison results in both panes"""
        only_a = self.compare_results["only_a"]
        only_b = self.compare_results["only_b"]
        both = self.compare_results["both"]
        corrupted = self.compare_results["corrupted"]

        # Clear trees
        for item in self.compare_tree_a.get_children():
            self.compare_tree_a.delete(item)
        for item in self.compare_tree_b.get_children():
            self.compare_tree_b.delete(item)

        # Populate left pane (Only in A)
        for filename, full_path, size, date_str in only_a:
            item_id = self.compare_tree_a.insert("", tk.END,
                                                 values=("☑", filename, self.format_size(size), date_str),
                                                 tags=(full_path,))
            self.compare_selection_a[item_id] = True  # Default checked

        # Populate right pane (Only in B)
        for filename, full_path, size, date_str in only_b:
            item_id = self.compare_tree_b.insert("", tk.END,
                                                 values=("☑", filename, self.format_size(size), date_str),
                                                 tags=(full_path,))
            self.compare_selection_b[item_id] = True  # Default checked

        # Update pane titles
        self.compare_left_pane.config(text=f"Only in Collection A ({len(only_a)} files)")
        self.compare_right_pane.config(text=f"Only in Collection B ({len(only_b)} files)")

        # Update Select All button texts with counts
        self.select_all_a_btn.config(text=f"Select All ({len(only_a)})")
        self.select_all_b_btn.config(text=f"Select All ({len(only_b)})")

        # Update summary
        summary = f"In Both Collections: {len(both)} files"

        # Add filtering statistics if files were filtered
        filtered_a = self.compare_results.get("filtered_a", 0)
        filtered_b = self.compare_results.get("filtered_b", 0)
        total_filtered = filtered_a + filtered_b
        if total_filtered > 0:
            total_found = len(only_a) + len(only_b) + len(both)
            summary += f" | Found {total_found} ROM files (ignored {total_filtered} non-ROM files)"

        if corrupted:
            summary += f" | Verified Identical: {len(both) - len(corrupted)} files | Corrupted: {len(corrupted)} files"
        self.compare_summary_var.set(summary)

        self.compare_status_var.set("Comparison complete - system sleep restored")
        self.compare_progress_var.set(100)

    def on_compare_tree_click(self, event, tree, side):
        """Handle clicks on compare tree checkboxes"""
        item = tree.identify_row(event.y)
        if not item:
            return

        column = tree.identify_column(event.x)

        # Only handle checkbox column clicks
        if column == "#1":
            selection_dict = self.compare_selection_a if side == "a" else self.compare_selection_b
            current_state = selection_dict.get(item, True)
            selection_dict[item] = not current_state

            # Update checkbox display
            new_checkbox = "☐" if current_state else "☑"
            tree.set(item, "select", new_checkbox)
            return "break"

    def copy_files_between_collections(self, direction):
        """Copy selected files between collections"""
        if direction == "a_to_b":
            source_tree = self.compare_tree_a
            selection_dict = self.compare_selection_a
            dest_path = self.compare_path_b_var.get()
            source_name = "Collection A"
            dest_name = "Collection B"
        else:  # b_to_a
            source_tree = self.compare_tree_b
            selection_dict = self.compare_selection_b
            dest_path = self.compare_path_a_var.get()
            source_name = "Collection B"
            dest_name = "Collection A"

        if not dest_path:
            show_error(self.root, "Missing Destination", f"Please select {dest_name} folder first.")
            return

        # Get selected files
        files_to_copy = []
        for item_id, is_selected in selection_dict.items():
            if is_selected:
                tags = source_tree.item(item_id, "tags")
                if tags:
                    source_file = tags[0]
                    filename = source_tree.set(item_id, "filename")
                    files_to_copy.append((source_file, filename))

        if not files_to_copy:
            show_info(self.root, "No Files Selected", "Please select files to copy.")
            return

        # Confirm copy
        message = f"Copy {len(files_to_copy)} files from {source_name} to {dest_name}?"
        if not ask_yesno(self.root, "Confirm Copy", message):
            return

        # Copy files with progress
        progress = ProgressDialog(self.root, "Copying Files", len(files_to_copy))

        def copy_worker():
            copied_count = 0
            failed = []

            for idx, (source_file, filename) in enumerate(files_to_copy):
                try:
                    dest_file = os.path.join(dest_path, filename)
                    progress.update(idx + 1, filename)

                    # Copy file
                    import shutil
                    shutil.copy2(source_file, dest_file)
                    copied_count += 1

                except Exception as e:
                    failed.append((filename, str(e)))

            progress.close()

            if failed:
                error_msg = f"Copied {copied_count} of {len(files_to_copy)} files.\n\nFailed:\n"
                for fname, error in failed[:5]:
                    error_msg += f"  • {fname}: {error}\n"
                if len(failed) > 5:
                    error_msg += f"  ... and {len(failed) - 5} more"
                show_error(self.root, "Copy Incomplete", error_msg)
            else:
                show_info(self.root, "Copy Complete", f"Successfully copied {copied_count} files!")

        thread = threading.Thread(target=copy_worker, daemon=True)
        thread.start()

    def export_compare_list(self, side):
        """Export list of files unique to one collection"""
        if side == "a":
            file_list = self.compare_results.get("only_a", [])
            default_name = "missing_in_collection_b.txt"
            title = "Collection A - Missing in B"
        else:
            file_list = self.compare_results.get("only_b", [])
            default_name = "missing_in_collection_a.txt"
            title = "Collection B - Missing in A"

        if not file_list:
            show_info(self.root, "No Data", "No files to export.")
            return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title=f"Export {title}",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== {title} ===\n")
                f.write(f"Total files: {len(file_list)}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for filename, full_path, size, date_str in file_list:
                    size_str = self.format_size(size)
                    f.write(f"{filename}\n")
                    f.write(f"  Path: {full_path}\n")
                    f.write(f"  Size: {size_str}\n")
                    f.write(f"  Date: {date_str}\n\n")

            show_info(self.root, "Export Complete", f"Exported {len(file_list)} files to:\n{file_path}")

        except Exception as e:
            show_error(self.root, "Export Error", f"Failed to export list:\n{str(e)}")

    def select_all_compare(self, side):
        """Select all files in comparison pane"""
        if side == "a":
            tree = self.compare_tree_a
            selection_dict = self.compare_selection_a
        else:
            tree = self.compare_tree_b
            selection_dict = self.compare_selection_b

        # Select all items
        for item in tree.get_children():
            selection_dict[item] = True
            tree.set(item, "select", "☑")

    def deselect_all_compare(self, side):
        """Deselect all files in comparison pane"""
        if side == "a":
            tree = self.compare_tree_a
            selection_dict = self.compare_selection_a
        else:
            tree = self.compare_tree_b
            selection_dict = self.compare_selection_b

        # Deselect all items
        for item in tree.get_children():
            selection_dict[item] = False
            tree.set(item, "select", "☐")

    # ==================== DAT RENAME TAB METHODS ====================

    def browse_dat_file(self):
        """Browse for a DAT file"""
        file_path = filedialog.askopenfilename(
            title="Select DAT File",
            filetypes=[("DAT files", "*.dat"), ("XML files", "*.xml"), ("All files", "*.*")]
        )

        if file_path:
            try:
                # Parse the DAT file
                self.dat_hash_map = parse_dat_file(file_path)
                self.dat_file_path = file_path
                self.dat_file_var.set(os.path.basename(file_path))

                # Update status with file count if folder is selected
                self._update_dat_status_with_file_count()
            except Exception as e:
                show_error(self.root, "DAT File Error", f"Failed to load DAT file:\n\n{str(e)}")
                self.dat_file_path = None
                self.dat_hash_map = {}
                self.dat_file_var.set("No DAT file selected")

    def _update_dat_status_with_file_count(self):
        """Update the DAT rename status with ROM file count"""
        if not self.current_folder or not os.path.exists(self.current_folder):
            self.dat_scan_status_var.set(f"DAT file loaded: {len(self.dat_hash_map)} hash entries. Select a ROM folder to continue.")
            return

        # Quick count of ROM files
        rom_count = 0
        try:
            for root_dir, dirs, files in os.walk(self.current_folder):
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                for filename in files:
                    file_path = os.path.join(root_dir, filename)
                    if self.should_include_file(file_path, filter_mode="rom_only"):
                        rom_count += 1

            if rom_count > 0:
                self.dat_scan_status_var.set(f"DAT loaded ({len(self.dat_hash_map)} entries). Found {rom_count} ROM file(s) in folder. Click 'Start Scan & Match'.")
            else:
                self.dat_scan_status_var.set(f"DAT loaded ({len(self.dat_hash_map)} entries). No ROM files found in folder.")
        except Exception as e:
            self.dat_scan_status_var.set(f"DAT file loaded: {len(self.dat_hash_map)} hash entries found")

    def start_dat_scan(self):
        """Start scanning and matching ROMs against the DAT file"""
        # Validation
        if not self.current_folder or not os.path.exists(self.current_folder):
            show_warning(self.root, "No Folder Selected", "Please select a ROM folder first.")
            return

        if not self.dat_file_path or not self.dat_hash_map:
            show_warning(self.root, "No DAT File", "Please select a DAT file first.")
            return

        # Clear previous results
        for item in self.dat_results_tree.get_children():
            self.dat_results_tree.delete(item)
        self.dat_matched_files = []
        self.dat_summary_var.set("")

        # Update UI state
        self.dat_scan_running = True
        self.dat_scan_cancelled = False
        self.dat_start_scan_button.config(state="disabled")
        self.dat_stop_scan_button.config(state="normal")
        self.dat_progress_var.set(0)
        self.dat_scan_status_var.set("Starting scan...")

        # Start background thread
        thread = threading.Thread(target=self._dat_scan_worker, args=(self.current_folder,), daemon=True)
        thread.start()

    def stop_dat_scan(self):
        """Stop the current DAT scan"""
        self.dat_scan_cancelled = True
        self.dat_scan_status_var.set("Cancelling scan...")
        self.dat_stop_scan_button.config(state="disabled")

    def _dat_scan_worker(self, scan_folder):
        """Worker thread for scanning and matching files"""
        try:
            # Get all ROM files
            rom_files = []
            for root_dir, dirs, files in os.walk(scan_folder):
                # Check for cancellation
                if self.dat_scan_cancelled:
                    self.root.after(0, self._dat_scan_cancelled)
                    return

                # Filter out excluded folders
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]

                for filename in files:
                    file_path = os.path.join(root_dir, filename)
                    if self.should_include_file(file_path, filter_mode="rom_only"):
                        rom_files.append(file_path)

            total_files = len(rom_files)
            if total_files == 0:
                self.root.after(0, lambda: self.dat_scan_status_var.set("No ROM files found in folder"))
                self.root.after(0, self._dat_scan_complete)
                return

            self.root.after(0, lambda: self.dat_progress_bar.config(maximum=total_files))

            matched = 0
            unmatched = 0
            skipped = 0

            # Process each file
            for idx, file_path in enumerate(rom_files):
                # Check for cancellation
                if self.dat_scan_cancelled:
                    self.root.after(0, self._dat_scan_cancelled)
                    return

                filename = os.path.basename(file_path)
                self.root.after(0, lambda p=idx+1, f=filename: self.dat_scan_status_var.set(
                    f"Scanning {p}/{total_files}: {f[:50]}..."))
                self.root.after(0, lambda p=idx+1: self.dat_progress_var.set(p))

                try:
                    # Calculate hashes for the file
                    crc32, md5, sha1 = calculate_file_hashes(file_path)

                    # Try to match against DAT
                    new_name = None
                    if crc32 in self.dat_hash_map:
                        new_name = self.dat_hash_map[crc32]
                    elif md5 in self.dat_hash_map:
                        new_name = self.dat_hash_map[md5]
                    elif sha1 in self.dat_hash_map:
                        new_name = self.dat_hash_map[sha1]

                    if new_name:
                        # Preserve file extension
                        _, ext = os.path.splitext(filename)
                        new_name_with_ext = new_name + ext

                        # Check if already named correctly
                        if filename == new_name_with_ext:
                            status = "Already Correct"
                            skipped += 1
                        else:
                            status = "Match Found"
                            matched += 1

                        # Store match
                        self.dat_matched_files.append((file_path, new_name_with_ext, status))

                        # Update UI with appropriate tag
                        def insert_with_tag(fname, nname, stat):
                            tag = "match" if stat == "Match Found" else "already_correct"
                            item_id = self.dat_results_tree.insert('', 'end', values=(fname, nname, stat))
                            self.dat_results_tree.item(item_id, tags=(tag,))

                        self.root.after(0, lambda f=filename, n=new_name_with_ext, s=status: insert_with_tag(f, n, s))
                    else:
                        # No match found - display as unmatched
                        unmatched += 1
                        def insert_unmatched(fname):
                            item_id = self.dat_results_tree.insert('', 'end', values=(fname, "-", "No Match"))
                            self.dat_results_tree.item(item_id, tags=("unmatched",))

                        self.root.after(0, lambda f=filename: insert_unmatched(f))

                except Exception as e:
                    # Error hashing file
                    def insert_error(fname, err):
                        item_id = self.dat_results_tree.insert('', 'end', values=(fname, "ERROR", f"Hash failed: {err}"))
                        self.dat_results_tree.item(item_id, tags=("error",))

                    self.root.after(0, lambda f=filename, e=str(e): insert_error(f, e))
                    unmatched += 1

            # Update summary
            summary = f"Total: {total_files} | Matched: {matched} | Already Correct: {skipped} | Unmatched: {unmatched}"
            self.root.after(0, lambda s=summary: self.dat_summary_var.set(s))

            # Show unmatched files dialog if any
            if unmatched > 0:
                self.root.after(0, lambda u=unmatched: self._show_unmatched_dialog(u))

            self.root.after(0, self._dat_scan_complete)

        except Exception as e:
            self.root.after(0, lambda: show_error(self.root, "Scan Error", f"An error occurred during scanning:\n\n{str(e)}"))
            self.root.after(0, self._dat_scan_complete)

    def _dat_scan_complete(self):
        """Called when scan completes successfully"""
        self.dat_scan_running = False
        self.dat_scan_cancelled = False
        self.dat_start_scan_button.config(state="normal")
        self.dat_stop_scan_button.config(state="disabled")

        # Enable rename buttons if we have matches
        has_matches = any(status == "Match Found" for _, _, status in self.dat_matched_files)
        if has_matches:
            self.dat_execute_button.config(state="normal")
            self.dat_rename_selected_button.config(state="normal")
            self.dat_scan_status_var.set("Scan complete! Select files to rename or click 'Execute Rename' to rename all matches")
        elif not self.dat_scan_status_var.get().startswith("No ROM"):
            self.dat_scan_status_var.set("Scan complete! No files need renaming (all correct or unmatched)")

    def _dat_scan_cancelled(self):
        """Called when scan is cancelled"""
        self.dat_scan_running = False
        self.dat_scan_cancelled = False
        self.dat_start_scan_button.config(state="normal")
        self.dat_stop_scan_button.config(state="disabled")
        self.dat_scan_status_var.set("Scan cancelled. Click 'Start Scan & Match' to try again")

    def _show_unmatched_dialog(self, unmatched_count):
        """Show dialog for unmatched files with export option"""
        message = f"{unmatched_count} file(s) could not be matched to the DAT file.\n\nWould you like to export a list of unmatched files?"

        result = ask_yesno(self.root, "Unmatched Files", message)

        if result:
            self._export_unmatched_files()

    def _export_unmatched_files(self):
        """Export unmatched files to a text file"""
        if not self.current_folder:
            return

        # Get list of all scanned files
        all_files = set()
        for root_dir, dirs, files in os.walk(self.current_folder):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
            for filename in files:
                file_path = os.path.join(root_dir, filename)
                if self.should_include_file(file_path, filter_mode="rom_only"):
                    all_files.add(os.path.basename(filename))

        # Get list of matched files
        matched_files = set(os.path.basename(path) for path, _, status in self.dat_matched_files if status != "ERROR")

        # Unmatched = all - matched
        unmatched_files = sorted(all_files - matched_files)

        if not unmatched_files:
            show_info(self.root, "No Unmatched Files", "All files were matched!")
            return

        # Ask where to save
        save_path = filedialog.asksaveasfilename(
            title="Save Unmatched Files List",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="unmatched_roms.txt"
        )

        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(f"Unmatched ROM Files - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total unmatched: {len(unmatched_files)}\n")
                    f.write("=" * 80 + "\n\n")
                    for filename in unmatched_files:
                        f.write(filename + "\n")

                show_info(self.root, "Export Complete", f"Unmatched files list saved to:\n{save_path}")
            except Exception as e:
                show_error(self.root, "Export Error", f"Failed to save list:\n\n{str(e)}")

    def clear_dat_results(self):
        """Clear the DAT rename results"""
        for item in self.dat_results_tree.get_children():
            self.dat_results_tree.delete(item)
        self.dat_matched_files = []
        self.dat_summary_var.set("")
        self.dat_scan_status_var.set("Select a folder and DAT file, then click 'Start Scan & Match'")
        self.dat_progress_var.set(0)

        # Disable rename buttons
        self.dat_execute_button.config(state="disabled")
        self.dat_rename_selected_button.config(state="disabled")

    def rename_selected_dat(self):
        """Rename only the selected files from DAT matches"""
        # Get selected items
        selected = self.dat_results_tree.selection()
        if not selected:
            show_info(self.root, "Rename Selected", "No files selected")
            return

        # Build a set of selected current filenames
        selected_filenames = set()
        for item in selected:
            values = self.dat_results_tree.item(item, "values")
            current_filename = values[0]
            selected_filenames.add(current_filename)

        # Filter to only selected files with "Match Found" status
        files_to_rename = []
        for path, new_name, status in self.dat_matched_files:
            current_filename = os.path.basename(path)
            if current_filename in selected_filenames and status == "Match Found":
                files_to_rename.append((path, new_name))

        if not files_to_rename:
            show_info(self.root, "Nothing to Rename", "No selected files need renaming (already correct or unmatched)")
            return

        # Perform rename with the filtered list
        self._perform_dat_rename(files_to_rename, f"{len(files_to_rename)} selected file(s)")

    def execute_dat_rename(self):
        """Execute the DAT rename operation - respects selection if items are selected"""
        # Check if user has selected specific items
        selected = self.dat_results_tree.selection()

        if selected:
            # User has selected items - only rename those
            selected_filenames = set()
            for item in selected:
                values = self.dat_results_tree.item(item, "values")
                current_filename = values[0]
                selected_filenames.add(current_filename)

            # Filter to only selected files with "Match Found" status
            files_to_rename = []
            for path, new_name, status in self.dat_matched_files:
                current_filename = os.path.basename(path)
                if current_filename in selected_filenames and status == "Match Found":
                    files_to_rename.append((path, new_name))

            if not files_to_rename:
                show_info(self.root, "Nothing to Rename", "No selected files need renaming (already correct or unmatched)")
                return

            # Perform rename with selection count
            self._perform_dat_rename(files_to_rename, f"{len(files_to_rename)} selected file(s)")
        else:
            # No selection - rename all matched files
            files_to_rename = [(path, new_name) for path, new_name, status in self.dat_matched_files
                              if status == "Match Found"]

            if not files_to_rename:
                show_info(self.root, "Nothing to Rename", "All matched files are already correctly named!")
                return

            # Perform rename with total count
            self._perform_dat_rename(files_to_rename, f"{len(files_to_rename)} file(s)")

    def _perform_dat_rename(self, files_to_rename, description):
        """Shared method to perform DAT rename with collision detection"""
        # Build rename plan with collision detection
        rename_plan = []
        collision_paths = set()

        for current_path, new_name in files_to_rename:
            folder = os.path.dirname(current_path)
            new_path = os.path.join(folder, new_name)

            # Skip if target exists (and it's not the source)
            if os.path.exists(new_path) and os.path.normpath(new_path) != os.path.normpath(current_path):
                collision_paths.add(current_path)
                continue

            rename_plan.append((current_path, new_path))

        # Remove duplicate targets
        seen_targets = {}
        filtered_plan = []
        for old_path, new_path in rename_plan:
            if new_path in seen_targets:
                collision_paths.add(old_path)
                collision_paths.add(seen_targets[new_path])
            else:
                seen_targets[new_path] = old_path
                filtered_plan.append((old_path, new_path))

        # Remove collisions from plan
        final_plan = [(old, new) for old, new in filtered_plan if old not in collision_paths]

        if not final_plan:
            show_warning(self.root, "Nothing to Rename", "All files either have collisions or are already correctly named.")
            return

        # Show confirmation with collision info
        confirm_msg = f"Ready to rename {description}.\n\n"
        if collision_paths:
            confirm_msg += f"WARNING: {len(collision_paths)} file(s) will be skipped due to collisions.\n\n"
        confirm_msg += "Proceed with rename?"

        result = ask_yesno(self.root, "Confirm Rename", confirm_msg)
        if not result:
            return

        # Perform renames in a thread with progress dialog
        progress = ProgressDialog(self.root, "Renaming Files", len(final_plan))

        results = {
            'success': 0,
            'skipped': 0,
            'errors': [],
            'undo_history': []
        }

        def rename_worker():
            try:
                for idx, (old_path, new_path) in enumerate(final_plan):
                    filename = os.path.basename(old_path)
                    progress.update(idx + 1, filename)

                    try:
                        # Perform rename
                        os.rename(old_path, new_path)
                        results['success'] += 1
                        results['undo_history'].append((new_path, old_path))

                    except Exception as e:
                        results['errors'].append((filename, str(e)))

                progress.close()
                self.root.after(0, lambda: self._show_dat_rename_results(results))

            except Exception as e:
                progress.close()
                self.root.after(0, lambda: show_error(self.root, "Rename Error", f"An error occurred:\n\n{str(e)}"))

        thread = threading.Thread(target=rename_worker, daemon=True)
        thread.start()

    def _show_dat_rename_results(self, results):
        """Show results of DAT rename operation"""
        success = results['success']
        errors = results['errors']
        undo_history = results['undo_history']

        # Update gamelist.xml if checkbox is enabled
        gamelist_updates = self._update_gamelist_if_enabled(
            self.dat_update_gamelist_var,
            undo_history,
            success
        )

        # Build message with better formatting
        msg = f"Successfully renamed {success} file"
        if success != 1:
            msg += "s"

        if gamelist_updates > 0:
            msg += f"\nUpdated {gamelist_updates} path(s) in gamelist.xml"

        if errors:
            msg += f"\n\nErrors: {len(errors)}"
            msg += "\n\nFirst errors:\n"
            for filename, error in errors[:10]:
                msg += f"  • {filename}: {error}\n"
            if len(errors) > 10:
                msg += f"  ... and {len(errors) - 10} more"

        show_info(self.root, "Rename Complete", msg)

        # Store undo history and enable undo button
        if undo_history:
            self.dat_undo_history = undo_history
            self.dat_undo_button.config(state="normal")

        # Update the tree to reflect renamed files (update current names)
        self._update_dat_tree_after_rename(undo_history)

        # Keep results visible - don't clear
        # User can manually rescan or clear if desired

    def _update_dat_tree_after_rename(self, undo_history):
        """Update the tree to show new current names after rename"""
        if not undo_history:
            return

        # Build a map of old paths to new paths
        rename_map = {}
        for new_path, old_path in undo_history:
            rename_map[old_path] = new_path

        # Update tree items
        for item in self.dat_results_tree.get_children():
            values = self.dat_results_tree.item(item, "values")
            if len(values) < 3:
                continue

            current_name = values[0]
            new_name = values[1]
            status = values[2]

            # Find if this file was renamed
            for old_path, new_path in rename_map.items():
                old_filename = os.path.basename(old_path)
                new_filename = os.path.basename(new_path)

                if current_name == old_filename:
                    # Update to show the new current name
                    # Status changes from "Match Found" to "Already Correct" since it's now correctly named
                    self.dat_results_tree.item(item, values=(new_filename, new_name, "Already Correct"))
                    # Update tag to green
                    self.dat_results_tree.item(item, tags=("already_correct",))
                    break

    def undo_dat_rename(self):
        """Undo the last DAT rename operation"""
        if not self.dat_undo_history:
            show_warning(self.root, "Nothing to Undo", "No recent DAT rename operation to undo.")
            return

        result = ask_yesno(self.root, "Confirm Undo",
                          f"This will undo the last rename operation ({len(self.dat_undo_history)} files).\n\nContinue?")

        if not result:
            return

        # Perform undo
        success = 0
        errors = []

        for new_path, original_path in self.dat_undo_history:
            try:
                # Check if current file still exists
                if not os.path.exists(new_path):
                    errors.append((os.path.basename(original_path), "File no longer exists at new location"))
                    continue

                # Check if original path is now occupied
                if os.path.exists(original_path):
                    errors.append((os.path.basename(original_path), "Original location is now occupied"))
                    continue

                # Perform undo
                os.rename(new_path, original_path)
                success += 1

            except Exception as e:
                errors.append((os.path.basename(original_path), str(e)))

        # Restore gamelist.xml from backup if it exists
        gamelist_restored = self._restore_gamelist_backup()

        # Show results
        msg = f"Undo operation complete!\n\n"
        msg += f"Successfully restored: {success} file(s)\n"
        if gamelist_restored:
            msg += "Restored gamelist.xml from backup\n"

        if errors:
            msg += f"Errors: {len(errors)}\n\n"
            msg += "First errors:\n"
            for filename, error in errors[:10]:
                msg += f"  • {filename}: {error}\n"
            if len(errors) > 10:
                msg += f"  ... and {len(errors) - 10} more\n"

        show_info(self.root, "Undo Complete", msg)

        # Update the tree to reflect undone renames (revert current names)
        self._update_dat_tree_after_undo(self.dat_undo_history)

        # Clear undo history and disable button
        self.dat_undo_history = []
        self.dat_undo_button.config(state="disabled")

    def _update_dat_tree_after_undo(self, undo_history):
        """Update the tree to show original names after undo"""
        if not undo_history:
            return

        # Build a map of new paths to original paths
        undo_map = {}
        for new_path, original_path in undo_history:
            undo_map[new_path] = original_path

        # Update tree items
        for item in self.dat_results_tree.get_children():
            values = self.dat_results_tree.item(item, "values")
            if len(values) < 3:
                continue

            current_name = values[0]
            new_name = values[1]
            status = values[2]

            # Find if this file was undone
            for new_path, original_path in undo_map.items():
                new_filename = os.path.basename(new_path)
                original_filename = os.path.basename(original_path)

                if current_name == new_filename:
                    # Update to show the original current name
                    # Status changes from "Already Correct" back to "Match Found"
                    self.dat_results_tree.item(item, values=(original_filename, new_name, "Match Found"))
                    # Update tag back to grey
                    self.dat_results_tree.item(item, tags=("match",))
                    break

    def dat_select_all(self):
        """Select all items in DAT results tree"""
        for item in self.dat_results_tree.get_children():
            self.dat_results_tree.selection_add(item)

    def dat_deselect_all(self):
        """Deselect all items in DAT results tree"""
        self.dat_results_tree.selection_remove(self.dat_results_tree.selection())

    def dat_refresh_scan(self):
        """Refresh the DAT scan with current folder and DAT file"""
        # Check if we have both folder and DAT file selected
        if not self.current_folder:
            show_warning(self.root, "No Folder", "Please select a ROM folder first.")
            return

        if not hasattr(self, 'dat_file_path') or not self.dat_file_path:
            show_warning(self.root, "No DAT File", "Please select a DAT file first.")
            return

        # Re-run the scan
        self.start_dat_scan()

    def rename_select_all(self):
        """Select all items in rename tree"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def rename_deselect_all(self):
        """Deselect all items in rename tree"""
        self.tree.selection_remove(self.tree.selection())


def main():
    # Load saved theme preference
    config = load_config()
    theme = config.get("theme", "light")

    # Map theme names to ttkbootstrap themes
    theme_map = {
        "light": "litera",
        "dark": "darkly"
    }

    # Create window with ttkbootstrap if available
    if TTKBOOTSTRAP_AVAILABLE:
        root = ttk_boot.Window(themename=theme_map.get(theme, "litera"))

        # Workaround for PyInstaller + ttkbootstrap localization issues on Linux
        # Stub out msgcat if it's not available (known issue on CachyOS, Steam Deck, etc.)
        try:
            root.tk.eval('::msgcat::mcset en test test')
        except tk.TclError:
            # msgcat not available, create stub
            root.tk.eval('proc ::msgcat::mcset {args} {}')
    else:
        root = tk.Tk()

    # Set icon immediately on root window
    set_window_icon(root)

    app = ROMManager(root, theme=theme)

    # Also set after mainloop starts for ttkbootstrap compatibility
    root.after(200, lambda: set_window_icon(root))
    root.mainloop()


if __name__ == "__main__":
    main()
