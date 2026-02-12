"""
Compare Collections Tab for ROM Librarian
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import hashlib
import ctypes
from datetime import datetime
from pathlib import Path

from .base_tab import BaseTab
from core import (
    logger, load_hash_cache, save_hash_cache,
    ROM_EXTENSIONS_WHITELIST, FILE_EXTENSIONS_BLACKLIST, EXCLUDED_FOLDER_NAMES,
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED
)
from ui import (
    ToolTip, show_info, show_error, ask_yesno,
    create_scrolled_treeview, sort_treeview, format_size, parse_size,
    ProgressDialog
)


class CompareTab(BaseTab):
    """Tab for comparing two ROM collections"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)

        # State variables
        self.compare_path_a_var = tk.StringVar()
        self.compare_path_b_var = tk.StringVar()
        self.compare_filter_mode = tk.StringVar(value="rom_only")
        self.compare_method = tk.StringVar(value="quick")
        self.verify_integrity = tk.BooleanVar(value=True)

        self.compare_results = {"only_a": [], "only_b": [], "both": [], "corrupted": []}
        self.compare_selection_a = {}  # item_id -> True/False
        self.compare_selection_b = {}  # item_id -> True/False

        # Get hash cache from manager
        self.hash_cache = load_hash_cache()

        # UI variables
        self.compare_progress_var = tk.IntVar(value=0)
        self.compare_status_var = tk.StringVar(value="")
        self.compare_summary_var = tk.StringVar(value="📊 Select two collections and click 'Start Compare'")

        self.setup()
        self.add_to_notebook("Compare Collections")

    def setup(self):
        """Setup the compare collections tab UI"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Compare two ROM collections to find missing files and sync between devices.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # === TOP SECTION: Comparison Setup ===
        setup_frame = ttk.LabelFrame(self.tab, text="Comparison Setup", padding="10")
        setup_frame.pack(fill=tk.X, pady=(0, 10))

        # Collection A
        coll_a_frame = ttk.Frame(setup_frame)
        coll_a_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(coll_a_frame, text="Collection A:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(coll_a_frame, textvariable=self.compare_path_a_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(coll_a_frame, text="Browse...", command=self.browse_collection_a).pack(side=tk.LEFT)

        # Collection B
        coll_b_frame = ttk.Frame(setup_frame)
        coll_b_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(coll_b_frame, text="Collection B:", width=12).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(coll_b_frame, textvariable=self.compare_path_b_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(coll_b_frame, text="Browse...", command=self.browse_collection_b).pack(side=tk.LEFT)

        # File filtering options
        filter_frame = ttk.Frame(setup_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="File Filter:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W, pady=(0, 5))

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
        self.verify_integrity_cb = ttk.Checkbutton(verify_frame, text="Verify integrity of matching files",
                                                    variable=self.verify_integrity)
        self.verify_integrity_cb.pack(side=tk.LEFT)
        ToolTip(self.verify_integrity_cb, "Hash files with matching names to detect corruption")

        # Compare button
        compare_btn_frame = ttk.Frame(setup_frame)
        compare_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(compare_btn_frame, text="Refresh",
                  command=self.start_compare).pack(side=tk.LEFT, padx=(0, 5))
        self.start_compare_btn = ttk.Button(compare_btn_frame, text="Start Compare",
                                           command=self.start_compare)
        self.start_compare_btn.pack(side=tk.LEFT)

        # Progress section
        self.compare_progress_bar = ttk.Progressbar(compare_btn_frame, mode='determinate',
                                                    variable=self.compare_progress_var, maximum=100, length=300)
        self.compare_progress_bar.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(compare_btn_frame, textvariable=self.compare_status_var).pack(side=tk.LEFT, padx=(10, 0))

        # === MIDDLE SECTION: Results Display ===
        results_frame = ttk.LabelFrame(self.tab, text="Comparison Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Center info summary
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

        self.compare_tree_a = create_scrolled_treeview(left_tree_frame, ("select", "filename", "size", "date"))
        self.compare_tree_a.heading("select", text="☐")
        self.compare_tree_a.heading("filename", text="Filename",
                                    command=lambda: sort_treeview(self.compare_tree_a, "filename", False, parse_size))
        self.compare_tree_a.heading("size", text="Size",
                                    command=lambda: sort_treeview(self.compare_tree_a, "size", False, parse_size))
        self.compare_tree_a.heading("date", text="Date Modified",
                                    command=lambda: sort_treeview(self.compare_tree_a, "date", False, parse_size))
        self.compare_tree_a.column("select", width=30, anchor="center")
        self.compare_tree_a.column("filename", width=250)
        self.compare_tree_a.column("size", width=80)
        self.compare_tree_a.column("date", width=120)

        # Right Pane: Only in Collection B
        right_pane = ttk.LabelFrame(panes_container, text="Only in Collection B (0 files)", padding="5")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        right_tree_frame = ttk.Frame(right_pane)
        right_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.compare_tree_b = create_scrolled_treeview(right_tree_frame, ("select", "filename", "size", "date"))
        self.compare_tree_b.heading("select", text="☐")
        self.compare_tree_b.heading("filename", text="Filename",
                                    command=lambda: sort_treeview(self.compare_tree_b, "filename", False, parse_size))
        self.compare_tree_b.heading("size", text="Size",
                                    command=lambda: sort_treeview(self.compare_tree_b, "size", False, parse_size))
        self.compare_tree_b.heading("date", text="Date Modified",
                                    command=lambda: sort_treeview(self.compare_tree_b, "date", False, parse_size))
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
        actions_frame = ttk.Frame(self.tab)
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
        if ext_lower in ROM_EXTENSIONS_WHITELIST:
            return True

        # Also include .zip files in ROM-only mode
        if ext_lower == '.zip':
            return True

        # Check blacklist after whitelist
        if ext_lower in FILE_EXTENSIONS_BLACKLIST:
            return False

        # If not in whitelist and not in blacklist, exclude it in ROM-only mode
        return False

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
            logger.debug("System sleep prevention enabled for comparison")
        except Exception as e:
            logger.warning(f"Failed to prevent system sleep: {e}")

        # Run comparison in background thread
        method = self.compare_method.get()
        logger.info(f"Starting collection comparison ({method} mode): {path_a} vs {path_b}")
        if method == "quick":
            verify = self.verify_integrity.get()
            thread = threading.Thread(target=self._quick_compare_worker,
                                    args=(path_a, path_b, verify), daemon=True)
        else:
            thread = threading.Thread(target=self._deep_compare_worker,
                                    args=(path_a, path_b), daemon=True)
        thread.start()
        logger.debug(f"Comparison thread started: {thread.name}")

    def _quick_compare_worker(self, path_a, path_b, verify_integrity):
        """Quick comparison by filename"""
        logger.debug(f"Quick compare worker started: {path_a} vs {path_b}")
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
                date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
                only_a_list.append((filename, full_path, size, date_str))

            only_b_list = []
            for filename in sorted(only_in_b):
                full_path = files_b[filename]
                size = os.path.getsize(full_path)
                mod_time = os.path.getmtime(full_path)
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

            logger.info(f"Quick compare complete: {len(only_a_list)} only in A, {len(only_b_list)} only in B, "
                       f"{len(in_both)} in both, {len(corrupted)} corrupted")

            # Update UI in main thread
            self.root.after(0, self._display_compare_results)

        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            self.root.after(0, lambda: show_error(self.root, "Comparison Error", str(e)))
            self.compare_status_var.set("Error during comparison")

        finally:
            # Save hash cache after comparison
            save_hash_cache(self.hash_cache)

            # Restore normal sleep behavior
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                logger.debug("System sleep prevention disabled")
            except Exception as e:
                logger.warning(f"Failed to restore sleep behavior: {e}")

    def _deep_compare_worker(self, path_a, path_b):
        """Deep comparison by content hash"""
        logger.debug(f"Deep compare worker started: {path_a} vs {path_b}")
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

            logger.info(f"Deep compare complete: {len(only_a_list)} only in A, {len(only_b_list)} only in B, "
                       f"{len(in_both_hashes)} in both (by content hash)")

            # Update UI in main thread
            self.root.after(0, self._display_compare_results)

        except Exception as e:
            logger.error(f"Comparison error: {e}", exc_info=True)
            self.root.after(0, lambda: show_error(self.root, "Comparison Error", str(e)))
            self.compare_status_var.set("Error during comparison")

        finally:
            # Save hash cache after comparison
            save_hash_cache(self.hash_cache)

            # Restore normal sleep behavior
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                logger.debug("System sleep prevention disabled")
            except Exception as e:
                logger.warning(f"Failed to restore sleep behavior: {e}")

    def _hash_file_quick(self, file_path, algorithm="sha1"):
        """Quick hash for comparison (with caching)"""
        try:
            # Get file metadata for cache key
            stat = os.stat(file_path)
            file_size = stat.st_size
            file_mtime = stat.st_mtime

            # Create cache key: path|size|mtime|method
            cache_key = f"{file_path}|{file_size}|{file_mtime}|{algorithm}"

            # Check cache first
            if cache_key in self.hash_cache:
                return self.hash_cache[cache_key]

            # Cache miss - calculate hash
            hasher = hashlib.sha1() if algorithm == "sha1" else hashlib.md5()

            with open(file_path, 'rb') as f:
                while chunk := f.read(1048576):  # 1MB chunks
                    hasher.update(chunk)

            file_hash = hasher.hexdigest()

            # Store in cache
            self.hash_cache[cache_key] = file_hash

            return file_hash
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
                                                 values=("☑", filename, format_size(size), date_str),
                                                 tags=(full_path,))
            self.compare_selection_a[item_id] = True  # Default checked

        # Populate right pane (Only in B)
        for filename, full_path, size, date_str in only_b:
            item_id = self.compare_tree_b.insert("", tk.END,
                                                 values=("☑", filename, format_size(size), date_str),
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
            import shutil
            copied_count = 0
            failed = []

            for idx, (source_file, filename) in enumerate(files_to_copy):
                try:
                    dest_file = os.path.join(dest_path, filename)
                    progress.update(idx + 1, filename)

                    # Copy file
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
                    size_str = format_size(size)
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
