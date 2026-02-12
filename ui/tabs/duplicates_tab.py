"""
Duplicates tab for ROM Librarian
Handles duplicate file detection and deletion based on content hashing
"""

import os
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import queue
from datetime import datetime

from .base_tab import BaseTab
from ui.helpers import ProgressDialog, ToolTip, show_info, show_warning, show_error, ask_yesno
from ui.tree_utils import create_scrolled_treeview
from ui.formatters import format_size, parse_size
from core import logger, EXCLUDED_FOLDER_NAMES, load_hash_cache, save_hash_cache

# Check for ttkbootstrap availability
try:
    import ttkbootstrap
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    TTKBOOTSTRAP_AVAILABLE = False


class DuplicatesTab(BaseTab):
    """Tab for finding and managing duplicate files"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)

        # Duplicates-specific attributes
        self.scan_mode = tk.StringVar(value="folder_only")
        self.hash_method = tk.StringVar(value="sha1")
        self.dup_filter_mode = tk.StringVar(value="rom_only")
        self.auto_select_strategy = tk.StringVar(value="Manual selection only")

        self.dup_progress_var = tk.IntVar(value=0)
        self.dup_scan_status_var = tk.StringVar(value="Ready to scan")
        self.dup_summary_var = tk.StringVar(value="📁 Select a ROM folder above, then click 'Start Scan' to find duplicates")

        # State variables
        self.scan_running = False
        self.scan_cancelled = False
        self.duplicate_groups = {}  # hash -> [file_paths]
        self.file_hashes = {}  # file_path -> hash
        self.group_selection = {}  # group_id -> True/False (selected or not)
        self.hash_cache = load_hash_cache()  # Persistent cache: "path|size|mtime|method" -> hash
        self.cache_hits = 0  # Track cache performance
        self.last_filtered_count = 0  # Track filtered files count for display

        # UI update queue for thread-safe updates
        self.ui_update_queue = manager.ui_update_queue

        self.setup()
        self.add_to_notebook("Duplicates")

    def setup(self):
        """Setup the duplicates detection tab"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Find duplicate files by content (not filename). Keep one copy, delete the rest.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Archive limitation note
        note_label = ttk.Label(guidance_frame,
                              text="⚠ Note: Archives (.zip, .7z, etc.) are compared as files, not by ROM content inside. "
                                   "Extract archives first for accurate duplicate detection across different compression formats.",
                              font=("TkDefaultFont", 8, "italic"),
                              foreground="#cc7000",
                              wraplength=800)
        note_label.pack(anchor=tk.W, pady=(5, 0))

        # === TOP SECTION: Scan Settings ===
        scan_settings_frame = ttk.LabelFrame(self.tab, text="Scan Settings", padding="10")
        scan_settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Scan mode and Hash method side by side
        options_frame = ttk.Frame(scan_settings_frame)
        options_frame.pack(fill=tk.X, pady=(5, 5))

        # Left: Scan Mode
        scan_mode_frame = ttk.Frame(options_frame)
        scan_mode_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        ttk.Label(scan_mode_frame, text="Scan Mode:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

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
        ttk.Button(scan_buttons_frame, text="Refresh", command=self.start_duplicate_scan).pack(side=tk.LEFT, padx=(0, 5))
        self.start_scan_btn = ttk.Button(scan_buttons_frame, text="Start Scan", command=self.start_duplicate_scan)
        self.start_scan_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_scan_btn = ttk.Button(scan_buttons_frame, text="Stop Scan", command=self.stop_duplicate_scan, state="disabled")
        self.stop_scan_btn.pack(side=tk.LEFT)

        # Progress section
        progress_frame = ttk.Frame(scan_settings_frame)
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        self.dup_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', variable=self.dup_progress_var, maximum=100)
        self.dup_progress_bar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(progress_frame, textvariable=self.dup_scan_status_var).pack(anchor=tk.W)

        # === MIDDLE SECTION: Results Display ===
        results_frame = ttk.LabelFrame(self.tab, text="Duplicate Groups", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Summary header with empty state message
        summary_label = ttk.Label(results_frame, textvariable=self.dup_summary_var,
                                 font=("TkDefaultFont", 9))
        summary_label.pack(anchor=tk.W, pady=(0, 5))

        # Results tree
        results_tree_frame = ttk.Frame(results_frame)
        results_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.dup_tree = create_scrolled_treeview(
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
        actions_frame = ttk.Frame(self.tab)
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        # Auto-selection strategy section
        auto_select_section = ttk.LabelFrame(actions_frame, text="Auto-Selection Strategy", padding="10")
        auto_select_section.pack(fill=tk.X, pady=(0, 10))

        auto_select_inner = ttk.Frame(auto_select_section)
        auto_select_inner.pack(fill=tk.X)

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

    def start_duplicate_scan(self):
        """Start scanning for duplicate files"""
        current_folder = self.get_current_folder()
        if not current_folder or not os.path.exists(current_folder):
            show_warning(self.root, "No Folder", "Please select a ROM folder first using the Browse button at the top")
            return

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
        logger.info(f"Starting duplicate scan in folder: {current_folder}")
        scan_thread = threading.Thread(target=self._scan_files_worker, args=(current_folder,), daemon=True)
        scan_thread.start()
        logger.debug(f"Duplicate scan thread started: {scan_thread.name}")

    def stop_duplicate_scan(self):
        """Stop the currently running scan"""
        self.scan_cancelled = True
        self.dup_scan_status_var.set("Cancelling...")
        self.stop_scan_btn.config(state="disabled")

    def _scan_files_worker(self, scan_folder):
        """Background worker thread for scanning and hashing files"""
        logger.debug(f"Duplicate scan worker started for: {scan_folder}")
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
                        if self.manager.should_include_file(full_path, filter_mode):
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
                        if self.manager.should_include_file(full_path, filter_mode):
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
                            if self.manager.should_include_file(full_path, filter_mode):
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
                            if self.manager.should_include_file(full_path, filter_mode):
                                files_to_scan.append(full_path)
                            else:
                                filtered_count += 1

            if self.scan_cancelled:
                self.ui_update_queue.put(self._scan_cancelled)
                return

            total_files = len(files_to_scan)
            if total_files == 0:
                self.ui_update_queue.put(lambda: show_info(self.root, "No Files", "No files found to scan"))
                self.ui_update_queue.put(self._scan_complete)
                return

            # Hash all files
            hash_method = self.hash_method.get()
            hashed_count = 0
            hash_dict = {}  # hash -> [file_paths]

            for file_path in files_to_scan:
                if self.scan_cancelled:
                    self.ui_update_queue.put(self._scan_cancelled)
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

                self.ui_update_queue.put(lambda p=progress, s=status_text: self._update_scan_progress(p, s))

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

            # Log scan results
            logger.info(f"Duplicate scan complete: {len(self.duplicate_groups)} duplicate groups found, "
                       f"{self.cache_hits} cache hits out of {total_files} files")

            # Save hash cache to disk
            save_hash_cache(self.hash_cache)

            # Display results
            self.ui_update_queue.put(lambda: self._display_duplicate_groups())
            self.ui_update_queue.put(self._scan_complete)

        except Exception as e:
            logger.error(f"Duplicate scan error: {e}", exc_info=True)
            error_msg = f"Scan error: {str(e)}"
            self.ui_update_queue.put(lambda: show_error(self.root, "Scan Error", error_msg))
            self.ui_update_queue.put(self._scan_complete)

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
                                        values=("", filename, mod_date, format_size(file_size), action, dir_path),
                                        tags=(tag, file_hash, file_path))
                except OSError:
                    continue  # Skip files that no longer exist or are inaccessible

        # Update summary
        wasted_gb = total_wasted_space / (1024 * 1024 * 1024)
        summary = f"Duplicate Groups: {total_groups} groups found | {total_dup_files} duplicate files | {wasted_gb:.2f} GB wasted space"

        # Add filtering statistics if files were filtered
        if self.last_filtered_count > 0:
            summary += f" | Ignored {self.last_filtered_count} non-ROM files"

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
                    'size': parse_size(size_str),
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
                    size_bytes = parse_size(size_str)
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
                        size_bytes = parse_size(size_str)
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
                        try:
                            file_size = os.path.getsize(file_paths[0])
                            total_wasted += file_size * (len(file_paths) - 1)
                        except:
                            pass

                wasted_gb = total_wasted / (1024 * 1024 * 1024)

                f.write(f"Total Duplicate Groups: {total_groups}\n")
                f.write(f"Total Duplicate Files: {total_files}\n")
                f.write(f"Total Wasted Space: {wasted_gb:.2f} GB\n\n")

                # Write scan details
                current_folder = self.get_current_folder()
                f.write(f"Scan Folder: {current_folder}\n")
                f.write(f"Scan Mode: {self.scan_mode.get()}\n")
                f.write(f"Hash Method: {self.hash_method.get().upper()}\n")
                f.write("\n" + "=" * 80 + "\n\n")

                # Get sorted groups (same as display)
                sorted_groups = []
                for file_hash, file_paths in self.duplicate_groups.items():
                    if file_paths:
                        try:
                            file_size = os.path.getsize(file_paths[0])
                            wasted = file_size * (len(file_paths) - 1)
                            sorted_groups.append((wasted, file_hash, file_paths))
                        except:
                            pass

                sorted_groups.sort(reverse=True)

                # Write groups
                for idx, (wasted, file_hash, file_paths) in enumerate(sorted_groups, 1):
                    wasted_mb = wasted / (1024 * 1024)
                    f.write(f"Group {idx}: {len(file_paths)} copies, {wasted_mb:.1f} MB wasted\n")
                    f.write(f"Hash: {file_hash}\n\n")

                    for file_path in file_paths:
                        try:
                            size = os.path.getsize(file_path)
                            f.write(f"  {file_path} ({format_size(size)})\n")
                        except:
                            f.write(f"  {file_path} (size unknown)\n")

                    f.write("\n")

            show_info(self.root, "Export Complete", f"Duplicate list saved to:\n{export_file_path}")

        except Exception as e:
            show_error(self.root, "Export Error", f"Failed to export list:\n\n{str(e)}")
