"""
Rename tab for ROM Librarian
Handles regex-based file renaming with preview and collision detection
"""

import os
import re
import gc
import time
import shutil
import tkinter as tk
from tkinter import ttk
import threading

from .base_tab import BaseTab
from ui.helpers import ProgressDialog, ToolTip, show_info, show_warning, show_error, ask_yesno
from ui.tree_utils import create_scrolled_treeview, sort_treeview
from ui.formatters import format_size, parse_size
from operations import update_gamelist_xml
from core import logger

# Check for ttkbootstrap availability
try:
    import ttkbootstrap
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    TTKBOOTSTRAP_AVAILABLE = False


class RenameTab(BaseTab):
    """Tab for regex-based file renaming with preview"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)

        # Rename-specific attributes
        self.pattern_var = tk.StringVar()
        self.replacement_var = tk.StringVar()
        self.collision_strategy = tk.StringVar(value="skip")
        self.update_gamelist_var = tk.BooleanVar(value=True)
        self.undo_history = []
        self.rename_results = {}

        self.setup()
        self.add_to_notebook("Rename")

    def setup(self):
        """Setup the rename tab"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Preview filename changes before applying. Use presets or custom regex patterns.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Regex rename controls
        rename_frame = ttk.LabelFrame(self.tab, text="Regex Rename", padding="10")
        rename_frame.pack(fill=tk.X, pady=(0, 10))

        # Pattern input
        pattern_frame = ttk.Frame(rename_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(pattern_frame, text="Pattern:").pack(side=tk.LEFT, padx=(0, 5))
        self.pattern_entry = ttk.Entry(pattern_frame, textvariable=self.pattern_var, width=40)
        self.pattern_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Replacement input
        ttk.Label(pattern_frame, text="Replace with:").pack(side=tk.LEFT, padx=(10, 5))
        self.replacement_entry = ttk.Entry(pattern_frame, textvariable=self.replacement_var, width=20)
        self.replacement_entry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(pattern_frame, text="Preview", command=self.preview_rename).pack(side=tk.LEFT, padx=(10, 0))

        # Collision handling options
        collision_frame = ttk.Frame(rename_frame)
        collision_frame.pack(fill=tk.X, pady=(5, 5))
        ttk.Label(collision_frame, text="If duplicates occur:").pack(side=tk.LEFT, padx=(0, 5))

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
        list_frame = ttk.Frame(self.tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree = create_scrolled_treeview(list_frame, ("original", "preview", "size"))
        self.tree.heading("original", text="Original Filename",
                         command=lambda: sort_treeview(self.tree, "original", False, parse_size))
        self.tree.heading("preview", text="Preview (after rename)",
                         command=lambda: sort_treeview(self.tree, "preview", False, parse_size))
        self.tree.heading("size", text="Size",
                         command=lambda: sort_treeview(self.tree, "size", False, parse_size))
        self.tree.column("original", width=400)
        self.tree.column("preview", width=400)
        self.tree.column("size", width=100)

        # Configure selection colors (blue for user selection)
        style = ttk.Style()
        style.map('Treeview',
                  background=[('selected', '#0078d7')],  # Blue background for selection
                  foreground=[('selected', 'white')])     # White text for selection

        self.manager.setup_custom_selection(self.tree)

        # Bottom frame - Action buttons
        button_frame = ttk.Frame(self.tab)
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

        ttk.Button(button_frame, text="Refresh", command=self.manager.reload_files).pack(side=tk.RIGHT)

    def load_preset(self, pattern, replacement):
        """Load a preset pattern into the input fields"""
        self.pattern_var.set(pattern)
        self.replacement_var.set(replacement)
        # Auto-update preview when preset is selected
        if self.manager.files_data:  # Only preview if files are loaded
            self.preview_rename()

    def refresh_file_list(self):
        """Refresh the file list display (called when files are loaded)"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add files from manager's files_data
        for filename, size, full_path in self.manager.files_data:
            self.tree.insert("", tk.END, values=(
                filename,
                "",  # Preview will be filled when user clicks Preview
                format_size(size)
            ))

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

        for filename, size, full_path in self.manager.files_data:
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
        current_folder = self.get_current_folder()
        existing_collisions = []
        for new_name in rename_map.keys():
            new_path = os.path.join(current_folder, new_name)
            # Check if a file with this name exists and is NOT in our files being renamed
            if os.path.exists(new_path) and new_name not in new_names_map:
                existing_collisions.append(new_name)

        # Second pass: display in tree with collision warnings
        changes_count = 0
        for filename, size, full_path in self.manager.files_data:
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
                format_size(size)
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
            if hasattr(self.manager, 'current_theme') and self.manager.current_theme == 'dark':
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
            self.manager.status_var.set(status_msg)
        else:
            self.manager.status_var.set(status_msg)

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

        for filename, size, full_path in self.manager.files_data:
            existing_files_map[filename.lower()] = filename

        current_folder = self.get_current_folder()

        # Only process selected files
        for filename, size, full_path in self.manager.files_data:
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

                new_path = os.path.join(current_folder, new_name)
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
                        suffixed_path = os.path.join(current_folder, suffixed_name)
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

        current_folder = self.get_current_folder()

        # First, build rename plan and detect collisions
        rename_plan = []  # List of (old_path, new_path, original_filename, new_filename)
        new_name_counts = {}  # Track how many files want each new name
        existing_files_map = {}  # Map of current filenames in lowercase

        for filename, size, full_path in self.manager.files_data:
            existing_files_map[filename.lower()] = filename

        for filename, size, full_path in self.manager.files_data:
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

                new_path = os.path.join(current_folder, new_name)
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
                        suffixed_path = os.path.join(current_folder, suffixed_name)
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
        logger.debug(f"Performing {len(final_rename_plan)} rename operations")
        undo_history = []
        cue_updates_needed = []  # Track CUE files that need updating

        for idx, (old_path, new_path, old_name, new_name) in enumerate(final_rename_plan, 1):
            # Update progress
            progress.update(idx, old_name)

            try:
                # Final check if destination exists
                if os.path.exists(new_path):
                    results['errors'].append(f"{old_name} -> {new_name}: Destination already exists")
                    results['error_count'] += 1
                    continue

                # Check if this is a BIN file - we'll need to update CUE files
                if old_name.lower().endswith('.bin'):
                    cue_updates_needed.append((old_name, new_name, os.path.dirname(old_path)))

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

        # Update CUE files if any BIN files were renamed
        if cue_updates_needed:
            logger.info(f"Updating {len(cue_updates_needed)} BIN file references in CUE files")
            cue_update_count = self._update_cue_files(cue_updates_needed, results)
            if cue_update_count > 0:
                logger.info(f"Updated {cue_update_count} CUE file(s)")

        # Store undo history
        results['undo_history'] = undo_history
        logger.info(f"Rename operation complete: {results['success_count']} succeeded, {results['error_count']} failed")

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
                    results['errors'].append(error_msg)

        return updated_count

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
        self.manager.load_files()
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
        self.manager.load_files()

    def rename_select_all(self):
        """Select all items in rename tree"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def rename_deselect_all(self):
        """Deselect all items in rename tree"""
        self.tree.selection_remove(self.tree.selection())
