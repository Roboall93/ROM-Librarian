#!/usr/bin/env python3
"""
ROM Librarian - Retro Gaming Collection Organizer
A tool for managing, renaming, and organizing ROM files
"""

import os
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import Frame, WORD, LEFT, Label, Text, DISABLED, TclError, Button, W, Tk, X, Toplevel, FLAT, Menu, SUNKEN, \
    BooleanVar, BOTH, NORMAL, StringVar
from tkinter import ttk, filedialog

# Import modular components
from core import (
    logger, VERSION, LOG_FILE, load_config, save_config, ROM_EXTENSIONS_WHITELIST, FILE_EXTENSIONS_BLACKLIST,
    EXCLUDED_FOLDER_NAMES
)
from ui import (
    set_window_icon, ProgressDialog, show_info, show_error, ask_yesno,
    sort_treeview, parse_size
)
from ui.tabs import M3UTab, CompressionTab, ConversionTab, RenameTab, DATRenameTab, DuplicatesTab, CompareTab

# Try to import ttkbootstrap for theming
TTKBOOTSTRAP_AVAILABLE = False
ttk_boot = None
ttkbootstrap_error = None
try:
    # Disable ttkbootstrap localization to avoid msgcat issues on some Linux systems
    os.environ['TTKBOOTSTRAP_DISABLE_LOCALIZATION'] = '1'
    import ttkbootstrap as ttk_boot
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except Exception as e:
    # Catch all exceptions including TclError from msgcat issues during import
    TTKBOOTSTRAP_AVAILABLE = False
    ttk_boot = None
    ttkbootstrap_error = e
    if "msgcat" in str(e).lower():
        print(f"Warning: ttkbootstrap disabled due to msgcat error. Using default theme.")
    elif not isinstance(e, ImportError):
        print(f"Warning: ttkbootstrap import failed: {str(e)}. Using default theme.")

# Log application startup (logger imported from core module)
logger.info(f"ROM Librarian v{VERSION} starting up")
logger.info(f"Log file: {LOG_FILE}")
logger.info(f"Platform: {os.name}")

# Log ttkbootstrap status
if TTKBOOTSTRAP_AVAILABLE:
    logger.info("ttkbootstrap theming available")
else:
    if ttkbootstrap_error:
        if "msgcat" in str(ttkbootstrap_error).lower():
            logger.warning(f"ttkbootstrap disabled due to msgcat error: {ttkbootstrap_error}")
        elif isinstance(ttkbootstrap_error, ImportError):
            logger.info("ttkbootstrap not installed, using default theme")
        else:
            logger.warning(f"ttkbootstrap import failed: {ttkbootstrap_error}")
    else:
        logger.info("ttkbootstrap not available, using default theme")

# Note: Helper functions and classes (dialogs, tooltips, progress) and core functions
# are now imported from the modular components at the top of this file:
# - set_window_icon, CenteredDialog, ProgressDialog, ToolTip from ui.helpers
# - show_info, show_error, show_warning, ask_yesno from ui.helpers
# - parse_dat_file from parsers.dat_parser
# - update_gamelist_xml from operations.gamelist
# - calculate_file_hashes from operations.file_ops
# - Configuration, constants, and logging from core modules


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
        self.sort_reverse = {}  # Track sort direction for each treeview column
        self.last_sort = {}  # Track last sort column and direction for each tree
        self.last_filtered_count = 0  # Track filtered files count for display

        # Queue for thread-safe UI updates (Linux compatibility)
        self.ui_update_queue = Queue()
        self._start_queue_processor()

        self.setup_ui()

        # Check for updates on startup if enabled (after UI is ready)
        if self.config.get("check_updates_on_startup", True):
            self.root.after(1000, lambda: self.check_for_updates(manual=False))

    def _start_queue_processor(self):
        """Start periodic queue processing for thread-safe UI updates"""
        def process_queue():
            try:
                while True:
                    callback = self.ui_update_queue.get_nowait()
                    callback()
            except Empty:
                pass
            finally:
                # Schedule next check
                self.root.after(100, process_queue)
        self.root.after(100, process_queue)

    def setup_ui(self):
        """Create the main UI layout"""
        # Menu bar
        self.setup_menubar()

        # Top frame - Folder selection (shared across all tabs)
        top_frame = ttk.Frame(self.root, padding="5")
        top_frame.pack(fill=X)

        ttk.Label(top_frame, text="ROM Folder:").pack(side=LEFT, padx=(0, 5))
        self.folder_var = StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var, state="readonly", width=60).pack(side=LEFT, padx=(0, 5))
        ttk.Button(top_frame, text="Browse...", command=lambda: self.choose_folder(usedownloadfolder=False)).pack(side=LEFT, padx=(0, 5))
        ttk.Button(top_frame, text="Downloads", command=lambda: self.choose_folder(usedownloadfolder=True)).pack(side=LEFT, padx=(0, 5))

        # Create tabbed notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=0, pady=(0, 5))

        # Create tabs
        self.rename_tab = RenameTab(self.notebook, self.root, self)
        self.dat_rename_tab = DATRenameTab(self.notebook, self.root, self)
        self.compression_tab = CompressionTab(self.notebook, self.root, self)
        self.conversion_tab = ConversionTab(self.notebook, self.root, self)
        self.m3u_tab = M3UTab(self.notebook, self.root, self)
        self.duplicates_tab = DuplicatesTab(self.notebook, self.root, self)
        self.compare_tab = CompareTab(self.notebook, self.root, self)

        # Bottom status bar (shared across all tabs)
        bottom_frame = ttk.Frame(self.root, padding="5")
        bottom_frame.pack(fill="x")

        self.status_var = StringVar(value="Select a folder to begin")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side=LEFT)

    def _set_app_icon(self):
        """Set the application icon"""
        # Delay icon setting to ensure window is fully initialized
        self.root.after(100, lambda: set_window_icon(self.root))

    def setup_menubar(self):
        """Create the menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        self.theme_var = StringVar(value=getattr(self, 'current_theme', 'light'))
        view_menu.add_radiobutton(label="Light Mode", variable=self.theme_var,
                                  value="light", command=lambda: self.change_theme("light"))
        view_menu.add_radiobutton(label="Dark Mode", variable=self.theme_var,
                                  value="dark", command=lambda: self.change_theme("dark"))

        # About menu
        about_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="About", menu=about_menu)
        about_menu.add_command(label="About ROM Librarian", command=self.show_about)

        # Updates menu
        updates_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Updates", menu=updates_menu)
        updates_menu.add_command(label="Check for Updates", command=self.check_for_updates_manual)

        # Check on Startup toggle
        self.check_updates_on_startup_var = BooleanVar(value=self.config.get("check_updates_on_startup", True))
        updates_menu.add_checkbutton(label="Check on Startup",
                                     variable=self.check_updates_on_startup_var,
                                     command=self.toggle_check_on_startup)

    def show_about(self):
        """Show the About dialog with attributions"""
        import webbrowser

        about_dialog = Toplevel(self.root)
        about_dialog.title("About ROM Librarian")
        about_dialog.resizable(False, False)
        about_dialog.transient(self.root)
        set_window_icon(about_dialog)

        # Main container
        container = Frame(about_dialog, padx=30, pady=20)
        container.pack(fill=BOTH, expand=True)

        # App name and version
        title_label = Label(container, text="ROM Librarian", font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=(0, 5))

        subtitle_label = Label(container, text="Retro Gaming Collection Organizer",
                               font=("TkDefaultFont", 10, "italic"), foreground="#666666")
        subtitle_label.pack(pady=(0, 2))

        author_label = Label(container, text="by RobotWizard",
                             font=("TkDefaultFont", 9), foreground="#666666")
        author_label.pack(pady=(0, 15))

        # Credits section
        credits_frame = Frame(container)
        credits_frame.pack(fill=X, pady=(0, 15))

        # Claude attribution
        Label(credits_frame, text="Developed with Claude Code",
              font=("TkDefaultFont", 9, "bold")).pack(anchor=W)
        Label(credits_frame, text="by Anthropic",
              font=("TkDefaultFont", 9), foreground="#666666").pack(anchor=W, pady=(0, 10))

        # Icon attribution
        Label(credits_frame, text="App Icon",
              font=("TkDefaultFont", 9, "bold")).pack(anchor=W)

        icon_link = Label(credits_frame,
                          text="Game cartridge icons created by Creatype - Flaticon",
                          font=("TkDefaultFont", 9), foreground="#0066cc", cursor="hand2")
        icon_link.pack(anchor=W)
        icon_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.flaticon.com/free-icons/game-cartridge"))
        icon_link.bind("<Enter>", lambda e: icon_link.config(font=("TkDefaultFont", 9, "underline")))
        icon_link.bind("<Leave>", lambda e: icon_link.config(font=("TkDefaultFont", 9)))

        # Version number
        version_label = Label(container, text=f"Version {VERSION}",
                              font=("TkDefaultFont", 8), foreground="#999999")
        version_label.pack(pady=(10, 0))

        # OK button
        ok_btn = Button(container, text="OK", command=about_dialog.destroy, width=10)
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
        from urllib.request import Request, urlopen
        from json import loads

        def check_updates_worker():
            try:
                url = "https://api.github.com/repos/Roboall93/ROM-Librarian/releases/latest"
                req = Request(url)
                req.add_header('User-Agent', 'ROM-Librarian')

                with urlopen(req, timeout=5) as response:
                    data = loads(response.read().decode())
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
        thread = Thread(target=check_updates_worker, daemon=True)
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

        dialog = Toplevel(self.root)
        dialog.title("Update Available")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        set_window_icon(dialog)

        container = ttk.Frame(dialog, padding=30)
        container.pack(fill=BOTH, expand=True)

        # Title
        title_label = ttk.Label(container, text="Update Available!",
                               font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 15))

        # Version info
        info_text = f"A new version of ROM Librarian is available!\n\n"
        info_text += f"Current version: {VERSION}\n"
        info_text += f"Latest version: {version}"

        info_label = ttk.Label(container, text=info_text, justify=LEFT)
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
            notes_header.pack(anchor=W, pady=(0, 5))

            notes_frame = ttk.Frame(container, relief=SUNKEN, borderwidth=1)
            notes_frame.pack(fill=BOTH, pady=(0, 20))

            # Create text widget for better formatting
            notes_text = Text(notes_frame, height=8, width=50,
                              font=("TkDefaultFont", 9),
                              wrap=WORD, padx=10, pady=10,
                              relief=FLAT, state=NORMAL)
            notes_text.insert(1.0, notes_preview)
            notes_text.config(state=DISABLED)
            notes_text.pack(fill=BOTH, expand=True)

        # Buttons
        button_frame = ttk.Frame(container)
        button_frame.pack()

        download_btn = ttk.Button(button_frame, text="Download Update",
                                 command=lambda: [webbrowser.open(url), dialog.destroy()],
                                 width=18)
        download_btn.pack(side=LEFT, padx=(0, 10))

        later_btn = ttk.Button(button_frame, text="Later",
                              command=dialog.destroy, width=12)
        later_btn.pack(side=LEFT)

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

    def choose_folder(self, usedownloadfolder: bool = False):
        """Open folder browser dialog"""
        if usedownloadfolder:
            folder = Path.home() / "Downloads"
        else:
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

            # Notify tabs about the loaded files
            self.rename_tab.refresh_file_list()
            self.compression_tab.refresh_compression_lists()

            self.status_var.set(f"Loaded {len(self.files_data)} files")

        except Exception as e:
            show_error(self.root, "Error", f"Failed to load files: {str(e)}")

    # Note: Utility methods now imported from ui module:
    # - format_size, parse_size, get_file_metadata, format_operation_results from ui.formatters
    # - create_scrolled_treeview, sort_treeview, get_files_from_tree from ui.tree_utils

    def run_worker_thread(self, work_func, args=(), progress=None, on_complete=None):
        """Run a function in a background thread with optional progress and completion callback."""
        def worker():
            work_func(*args)
            if progress:
                progress.close()
            if on_complete:
                self.root.after(0, on_complete)
        thread = Thread(target=worker, daemon=True)
        thread.start()

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

    # Note: get_file_metadata and sort_treeview now imported from ui module

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
                           command=lambda c=column: sort_treeview(tree, c, new_reverse, parse_size))
            else:
                # Remove arrow from other columns
                tree.heading(column, text=base_name,
                           command=lambda c=column: sort_treeview(tree, c, False, parse_size))

    def reload_files(self):
        """Reload files from disk (called by Refresh button)"""
        if self.current_folder:
            self.load_files()
        self.status_var.set(f"Refreshed: {len(self.files_data)} files")

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
                self.compression_tab.compress_ext_var.set(f"*{most_common_ext}")
                self.compression_tab.refresh_compression_lists()

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

    # ==================== DAT RENAME TAB METHODS ====================



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
        # Workaround for PyInstaller + ttkbootstrap localization issues on Linux
        # Try to create ttkbootstrap Window, but fall back to plain Tk if msgcat fails
        try:
            root = ttk_boot.Window(themename=theme_map.get(theme, "litera"))
        except TclError as e:
            if "msgcat" in str(e):
                # msgcat not available (known issue on CachyOS, Steam Deck, etc.)
                # Fall back to plain Tk - themes won't work but app will run
                print(f"Warning: ttkbootstrap themes unavailable due to msgcat error. Using default theme.")
                root = Tk()
            else:
                raise
    else:
        root = Tk()

    # Set icon immediately on root window
    set_window_icon(root)

    app = ROMManager(root, theme=theme)

    # Also set after mainloop starts for ttkbootstrap compatibility
    root.after(200, lambda: set_window_icon(root))
    root.mainloop()


if __name__ == "__main__":
    main()
