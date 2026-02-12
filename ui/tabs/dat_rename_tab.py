"""
DAT Rename tab for ROM Librarian
Handles bulk renaming using DAT files (No-Intro, MAME, etc.)
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog
import threading
from datetime import datetime

from .base_tab import BaseTab
from ui.helpers import ProgressDialog, show_info, show_warning, show_error, ask_yesno
from ui.tree_utils import sort_treeview
from ui.formatters import parse_size
from parsers import parse_dat_file
from operations import calculate_file_hashes, update_gamelist_xml
from core import EXCLUDED_FOLDER_NAMES


class DATRenameTab(BaseTab):
    """Tab for bulk renaming ROMs based on DAT files"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)

        # DAT-specific attributes
        self.dat_file_var = tk.StringVar(value="No DAT file selected")
        self.dat_scan_status_var = tk.StringVar(value="Select a folder and DAT file, then click 'Start Scan & Match'")
        self.dat_progress_var = tk.IntVar(value=0)
        self.dat_update_gamelist_var = tk.BooleanVar(value=True)
        self.dat_summary_var = tk.StringVar(value="")

        self.dat_file_path = None
        self.dat_hash_map = {}
        self.dat_scan_running = False
        self.dat_scan_cancelled = False
        self.dat_matched_files = []  # List of (current_path, new_name, status)
        self.dat_undo_history = []  # List of (new_path, original_path) tuples

        self.setup()
        self.add_to_notebook("DAT Rename")

    def setup(self):
        """Setup the DAT rename tab for bulk renaming using DAT files"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Bulk rename ROMs based on DAT files (No-Intro, MAME, etc.). ROMs are matched by hash and renamed automatically.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # === DAT FILE SELECTION ===
        dat_frame = ttk.LabelFrame(self.tab, text="DAT File", padding="10")
        dat_frame.pack(fill=tk.X, pady=(0, 10))

        dat_select_frame = ttk.Frame(dat_frame)
        dat_select_frame.pack(fill=tk.X)

        ttk.Label(dat_select_frame, text="Selected DAT:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(dat_select_frame, textvariable=self.dat_file_var, state="readonly", width=60).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(dat_select_frame, text="Browse DAT...", command=self.browse_dat_file).pack(side=tk.LEFT)

        # === SCAN CONTROLS ===
        scan_frame = ttk.LabelFrame(self.tab, text="Scan & Match", padding="10")
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

        ttk.Label(status_frame, textvariable=self.dat_scan_status_var).pack(anchor=tk.W)

        # Progress bar
        progress_frame = ttk.Frame(scan_frame)
        progress_frame.pack(fill=tk.X)

        self.dat_progress_bar = ttk.Progressbar(progress_frame, mode='determinate', variable=self.dat_progress_var)
        self.dat_progress_bar.pack(fill=tk.X)

        # Gamelist.xml auto-update option
        dat_gamelist_frame = ttk.Frame(scan_frame)
        dat_gamelist_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Checkbutton(dat_gamelist_frame, text="Auto-Update gamelist.xml (EmulationStation/RetroPie)",
                       variable=self.dat_update_gamelist_var).pack(side=tk.LEFT)

        # === RESULTS TREE ===
        results_frame = ttk.LabelFrame(self.tab, text="Matched Files", padding="10")
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
                                      command=lambda: sort_treeview(self.dat_results_tree, "current", False, parse_size))
        self.dat_results_tree.heading('new', text='New Name (from DAT)',
                                      command=lambda: sort_treeview(self.dat_results_tree, "new", False, parse_size))
        self.dat_results_tree.heading('status', text='Status',
                                      command=lambda: sort_treeview(self.dat_results_tree, "status", False, parse_size))

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
        self.manager.setup_custom_selection(self.dat_results_tree)

        # Summary label
        ttk.Label(results_frame, textvariable=self.dat_summary_var, font=("TkDefaultFont", 9)).pack(anchor=tk.W, pady=(5, 0))

        # === ACTION BUTTONS ===
        action_frame = ttk.Frame(self.tab)
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
        current_folder = self.get_current_folder()
        if not current_folder or not os.path.exists(current_folder):
            self.dat_scan_status_var.set(f"DAT file loaded: {len(self.dat_hash_map)} hash entries. Select a ROM folder to continue.")
            return

        # Quick count of ROM files
        rom_count = 0
        try:
            for root_dir, dirs, files in os.walk(current_folder):
                dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
                for filename in files:
                    file_path = os.path.join(root_dir, filename)
                    if self.manager.should_include_file(file_path, filter_mode="rom_only"):
                        rom_count += 1

            if rom_count > 0:
                self.dat_scan_status_var.set(f"DAT loaded ({len(self.dat_hash_map)} entries). Found {rom_count} ROM file(s) in folder. Click 'Start Scan & Match'.")
            else:
                self.dat_scan_status_var.set(f"DAT loaded ({len(self.dat_hash_map)} entries). No ROM files found in folder.")
        except Exception as e:
            self.dat_scan_status_var.set(f"DAT file loaded: {len(self.dat_hash_map)} hash entries found")

    def start_dat_scan(self):
        """Start scanning and matching ROMs against the DAT file"""
        current_folder = self.get_current_folder()

        # Validation
        if not current_folder or not os.path.exists(current_folder):
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
        thread = threading.Thread(target=self._dat_scan_worker, args=(current_folder,), daemon=True)
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
                    if self.manager.should_include_file(file_path, filter_mode="rom_only"):
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
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get list of all scanned files
        all_files = set()
        for root_dir, dirs, files in os.walk(current_folder):
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_FOLDER_NAMES]
            for filename in files:
                file_path = os.path.join(root_dir, filename)
                if self.manager.should_include_file(file_path, filter_mode="rom_only"):
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
        cue_updates_needed = []  # Track CUE files that need updating

        def rename_worker():
            try:
                for idx, (old_path, new_path) in enumerate(final_plan):
                    filename = os.path.basename(old_path)
                    progress.update(idx + 1, filename)

                    try:
                        old_name = os.path.basename(old_path)
                        new_name = os.path.basename(new_path)

                        # Check if this is a BIN file - we'll need to update CUE files
                        if old_name.lower().endswith('.bin'):
                            cue_updates_needed.append((old_name, new_name, os.path.dirname(old_path)))

                        # Perform rename
                        os.rename(old_path, new_path)
                        results['success'] += 1
                        results['undo_history'].append((new_path, old_path))

                    except Exception as e:
                        results['errors'].append((filename, str(e)))

                # Update CUE files if any BIN files were renamed
                if cue_updates_needed:
                    logger.info(f"Updating {len(cue_updates_needed)} BIN file references in CUE files")
                    cue_update_count = self._update_cue_files(cue_updates_needed, results)
                    if cue_update_count > 0:
                        logger.info(f"Updated {cue_update_count} CUE file(s)")

                progress.close()
                self.root.after(0, lambda: self._show_dat_rename_results(results))

            except Exception as e:
                progress.close()
                self.root.after(0, lambda: show_error(self.root, "Rename Error", f"An error occurred:\n\n{str(e)}"))

        thread = threading.Thread(target=rename_worker, daemon=True)
        thread.start()

    def _update_cue_files(self, cue_updates_needed, results):
        """Update CUE files to reference renamed BIN files

        Args:
            cue_updates_needed: List of tuples (old_bin_name, new_bin_name, folder_path)
            results: Results dictionary for tracking errors

        Returns:
            Number of CUE files successfully updated
        """
        updated_count = 0

        # Group by folder for efficiency
        folders = set(folder for _, _, folder in cue_updates_needed)

        for folder in folders:
            # Get all CUE files in this folder
            try:
                cue_files = [f for f in os.listdir(folder) if f.lower().endswith('.cue')]
            except Exception as e:
                logger.error(f"Failed to list CUE files in {folder}: {e}")
                continue

            # Create mapping of old -> new BIN names for this folder
            bin_renames = {old: new for old, new, fld in cue_updates_needed if fld == folder}

            for cue_file in cue_files:
                cue_path = os.path.join(folder, cue_file)
                try:
                    # Read CUE file
                    with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    # Check if any updates are needed
                    modified = False
                    new_lines = []

                    for line in lines:
                        new_line = line
                        # Look for FILE lines
                        if line.strip().upper().startswith('FILE'):
                            # Extract filename from: FILE "filename.bin" BINARY
                            parts = line.split('"')
                            if len(parts) >= 2:
                                old_bin_ref = parts[1]
                                old_bin_basename = os.path.basename(old_bin_ref)

                                # Check if this BIN was renamed
                                if old_bin_basename in bin_renames:
                                    new_bin_name = bin_renames[old_bin_basename]
                                    # Replace the old BIN name with new one
                                    new_line = line.replace(f'"{old_bin_ref}"', f'"{new_bin_name}"')
                                    modified = True
                                    logger.debug(f"Updated CUE {cue_file}: {old_bin_basename} -> {new_bin_name}")

                        new_lines.append(new_line)

                    # Write back if modified
                    if modified:
                        with open(cue_path, 'w', encoding='utf-8', newline='') as f:
                            f.writelines(new_lines)
                        updated_count += 1
                        logger.info(f"Updated CUE file: {cue_file}")

                except Exception as e:
                    error_msg = f"Failed to update CUE file {cue_file}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append((cue_file, error_msg))

        return updated_count

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
        current_folder = self.get_current_folder()

        # Check if we have both folder and DAT file selected
        if not current_folder:
            show_warning(self.root, "No Folder", "Please select a ROM folder first.")
            return

        if not hasattr(self, 'dat_file_path') or not self.dat_file_path:
            show_warning(self.root, "No DAT File", "Please select a DAT file first.")
            return

        # Re-run the scan
        self.start_dat_scan()

    def _update_gamelist_if_enabled(self, checkbox_var, undo_history, success_count):
        """
        Helper to update gamelist.xml if checkbox is enabled.
        Returns number of paths updated.
        """
        if not checkbox_var.get() or success_count == 0:
            return 0

        try:
            current_folder = self.get_current_folder()
            # Create rename map from undo history: {old_path: new_path}
            rename_map = {old_path: new_path for new_path, old_path in undo_history}
            return update_gamelist_xml(current_folder, rename_map)
        except Exception:
            # Don't fail the whole operation if gamelist update fails
            return 0

    def _restore_gamelist_backup(self):
        """
        Helper to restore gamelist.xml from backup.
        Returns True if backup was restored, False otherwise.
        """
        current_folder = self.get_current_folder()
        if not current_folder:
            return False

        gamelist_path = os.path.join(current_folder, "gamelist.xml")
        backup_path = gamelist_path + ".backup"

        if not os.path.exists(backup_path):
            return False

        try:
            shutil.copy2(backup_path, gamelist_path)
            os.remove(backup_path)
            return True
        except Exception:
            return False
