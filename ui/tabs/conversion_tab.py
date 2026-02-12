"""
Conversion tab for ROM Librarian
Handles conversion of disc images (ISO, CUE/BIN) to CHD format using chdman.exe
"""

import os
import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import shutil

from .base_tab import BaseTab
from ui.helpers import ProgressDialog, show_info, ask_yesno
from ui.tree_utils import create_scrolled_treeview, sort_treeview, get_files_from_tree
from ui.formatters import format_size, parse_size, format_operation_results
from core import logger


class ConversionTab(BaseTab):
    """Tab for converting disc images to CHD format"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)
        self.conversion_mode = tk.StringVar(value="cue_bin")
        self.setup()
        self.add_to_notebook("Conversion")

    def setup(self):
        """Setup the conversion tab with single-pane layout"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Convert disc images to CHD format for use with MAME/RetroArch emulators",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Warning note about chdman requirement
        warning_frame = ttk.Frame(self.tab)
        warning_frame.pack(fill=tk.X, pady=(0, 10))
        warning_label = ttk.Label(warning_frame,
                                  text="⚠ Requires chdman.exe (from MAME tools) in same folder as script or in PATH",
                                  font=("TkDefaultFont", 9, "bold"),
                                  foreground="#cc6600")
        warning_label.pack(anchor=tk.W)

        # Top control frame - Conversion mode selector
        control_frame = ttk.Frame(self.tab)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Conversion Mode:").pack(side=tk.LEFT, padx=(0, 10))

        # Radio buttons for conversion mode
        cue_bin_radio = ttk.Radiobutton(control_frame, text="CUE/BIN → CHD",
                                        variable=self.conversion_mode, value="cue_bin",
                                        command=self.refresh_conversion_lists)
        cue_bin_radio.pack(side=tk.LEFT, padx=(0, 10))

        iso_radio = ttk.Radiobutton(control_frame, text="ISO → CHD",
                                    variable=self.conversion_mode, value="iso",
                                    command=self.refresh_conversion_lists)
        iso_radio.pack(side=tk.LEFT, padx=(0, 10))

        # Single pane container
        pane_frame = ttk.LabelFrame(self.tab, text="Source Files", padding="10")
        pane_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # File list
        list_frame = ttk.Frame(pane_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.conversion_tree = create_scrolled_treeview(list_frame, ("filename", "size", "status"))
        self.conversion_tree.heading("filename", text="Filename",
                                     command=lambda: sort_treeview(self.conversion_tree, "filename", False, parse_size))
        self.conversion_tree.heading("size", text="Size",
                                     command=lambda: sort_treeview(self.conversion_tree, "size", False, parse_size))
        self.conversion_tree.heading("status", text="Status",
                                     command=lambda: sort_treeview(self.conversion_tree, "status", False, parse_size))
        self.conversion_tree.column("filename", width=350)
        self.conversion_tree.column("size", width=100)
        self.conversion_tree.column("status", width=150)
        self.manager.setup_custom_selection(self.conversion_tree)

        # Control buttons
        btn_frame = ttk.Frame(pane_frame)
        btn_frame.pack(fill=tk.X)

        self.delete_source_var = tk.IntVar(value=0)
        tk.Checkbutton(btn_frame, text="Delete source files after successful conversion",
                       variable=self.delete_source_var, onvalue=1, offvalue=0).pack(anchor=tk.W, pady=(0, 5))

        btns = ttk.Frame(btn_frame)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Refresh",
                  command=self.refresh_conversion_lists).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btns, text="Convert Selected",
                  command=self.convert_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btns, text="Convert All",
                  command=self.convert_all).pack(side=tk.LEFT, padx=(0, 5))

        # Status bar for conversion tab
        self.conversion_status_var = tk.StringVar(value="")
        ttk.Label(self.tab, textvariable=self.conversion_status_var).pack(fill=tk.X)

    def refresh_conversion_lists(self):
        """Refresh the conversion file list based on current mode"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Clear tree
        for item in self.conversion_tree.get_children():
            self.conversion_tree.delete(item)

        mode = self.conversion_mode.get()

        try:
            # Get all files in folder
            all_files = []
            for filename in os.listdir(current_folder):
                file_path = os.path.join(current_folder, filename)
                if os.path.isfile(file_path):
                    all_files.append(filename)

            # Populate tree based on mode
            file_count = 0
            if mode == "cue_bin":
                # Show .cue files
                for filename in all_files:
                    if filename.lower().endswith(".cue"):
                        file_path = os.path.join(current_folder, filename)
                        size = os.path.getsize(file_path)
                        size_str = format_size(size)

                        # Validate .bin files exist
                        bin_files = self._get_bin_files_for_cue(file_path)
                        if bin_files is None:
                            status = "Error: Cannot read CUE"
                        elif not bin_files:
                            status = "Error: No BIN files found"
                        else:
                            missing = [b for b in bin_files if not os.path.exists(os.path.join(current_folder, b))]
                            if missing:
                                # Debug: log what we're looking for vs what exists
                                logger.debug(f"CUE file: {filename}")
                                logger.debug(f"Looking for BIN files: {bin_files}")
                                logger.debug(f"Missing: {missing}")
                                logger.debug(f"Folder contents (BIN only): {[f for f in all_files if f.lower().endswith('.bin')]}")
                                status = f"Error: Missing {len(missing)} BIN file(s)"
                            else:
                                status = f"{len(bin_files)} BIN file(s) found"

                        self.conversion_tree.insert("", "end", values=(filename, size_str, status))
                        file_count += 1

            elif mode == "iso":
                # Show .iso files
                for filename in all_files:
                    if filename.lower().endswith(".iso"):
                        file_path = os.path.join(current_folder, filename)
                        size = os.path.getsize(file_path)
                        size_str = format_size(size)

                        # Check if CHD already exists
                        chd_name = os.path.splitext(filename)[0] + ".chd"
                        status = "CHD exists" if chd_name in all_files else "Ready"

                        self.conversion_tree.insert("", "end", values=(filename, size_str, status))
                        file_count += 1

            # Update status
            mode_label = "CUE files" if mode == "cue_bin" else "ISO files"
            status_msg = f"{mode_label}: {file_count}"
            self.conversion_status_var.set(status_msg)

        except Exception as e:
            show_info(self.root, "Error", f"Failed to refresh lists:\n{str(e)}")

    def _get_bin_files_for_cue(self, cue_path):
        """Parse CUE file and return list of referenced BIN files"""
        try:
            bin_files = []
            cue_dir = os.path.dirname(cue_path)

            with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # Look for FILE lines in CUE sheet
                    if line.upper().startswith('FILE'):
                        # Format: FILE "filename.bin" BINARY
                        parts = line.split('"')
                        if len(parts) >= 2:
                            bin_file = parts[1]
                            # Extract just the basename in case there's a path
                            bin_file = os.path.basename(bin_file)
                            if bin_file not in bin_files:
                                bin_files.append(bin_file)
            return bin_files
        except Exception as e:
            logger.error(f"Error parsing CUE file {cue_path}: {e}")
            return None

    def convert_selected(self):
        """Convert selected files"""
        self._convert_files(selected_only=True)

    def convert_all(self):
        """Convert all files"""
        self._convert_files(selected_only=False)

    def _convert_files(self, selected_only=True):
        """Convert disc image files to CHD format"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get files from tree
        files = get_files_from_tree(self.conversion_tree, current_folder, selected_only)
        if not files:
            msg = "Please select files to convert" if selected_only else "No files to convert"
            show_info(self.root, "Convert", msg)
            return

        convert_list = [f[0] for f in files]

        # Check for chdman.exe availability
        chdman_path = self._find_chdman()
        if not chdman_path:
            show_info(self.root, "Error",
                     "chdman.exe not found!\n\n"
                     "Please place chdman.exe in the same folder as this script\n"
                     "or ensure it is available in your system PATH.\n\n"
                     "chdman.exe is part of the MAME tools package.")
            return

        # Confirm and start
        delete_source = bool(self.delete_source_var.get())
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: Source files will be DELETED after successful conversion!" if delete_source else None
        progress, _ = self.manager.confirm_and_start_operation(
            f"Convert {len(convert_list)} {label} file(s)", 1,
            warning_msg=warning, title="Confirm Conversion"
        )
        if not progress:
            return

        # Reset progress for actual file count
        progress.total_items = len(convert_list)
        progress.progress_bar.config(maximum=len(convert_list))

        self.conversion_results = {
            'converted': 0, 'skipped': 0, 'failed': 0, 'errors': []
        }

        self.manager.run_worker_thread(
            self._perform_conversion,
            args=(convert_list, progress, delete_source, chdman_path, self.conversion_results),
            progress=progress,
            on_complete=self._show_conversion_results
        )

    def _find_chdman(self):
        """Find chdman.exe in script folder or PATH"""
        # Check same folder as script first
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels from ui/tabs to root
        root_dir = os.path.dirname(os.path.dirname(script_dir))
        local_chdman = os.path.join(root_dir, "chdman.exe")

        if os.path.exists(local_chdman):
            return local_chdman

        # Check in PATH
        chdman_in_path = shutil.which("chdman.exe")
        if chdman_in_path:
            return chdman_in_path

        return None

    def _perform_conversion(self, convert_list, progress, delete_source, chdman_path, results):
        """Perform the actual conversion operations (runs in worker thread)"""
        current_folder = self.get_current_folder()
        mode = self.conversion_mode.get()

        for idx, file_path in enumerate(convert_list, 1):
            filename = os.path.basename(file_path)
            progress.update(idx, filename)

            try:
                # Determine output CHD path
                chd_name = os.path.splitext(filename)[0] + ".chd"
                chd_path = os.path.join(current_folder, chd_name)

                # Skip if CHD already exists
                if os.path.exists(chd_path):
                    results['errors'].append(f"{filename}: CHD already exists")
                    results['skipped'] += 1
                    continue

                # For CUE files, validate BIN files exist
                if mode == "cue_bin":
                    bin_files = self._get_bin_files_for_cue(file_path)
                    if not bin_files:
                        results['errors'].append(f"{filename}: No BIN files referenced")
                        results['failed'] += 1
                        continue

                    # Check all BIN files exist
                    missing = []
                    for bin_file in bin_files:
                        bin_path = os.path.join(current_folder, bin_file)
                        if not os.path.exists(bin_path):
                            missing.append(bin_file)

                    if missing:
                        results['errors'].append(f"{filename}: Missing BIN files: {', '.join(missing)}")
                        results['failed'] += 1
                        continue

                # Build chdman command
                # For both CUE/BIN and ISO, we use createcd
                cmd = [chdman_path, "createcd", "-i", file_path, "-o", chd_path]

                # Run chdman
                process = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=current_folder,
                    timeout=600  # 10 minute timeout
                )

                # Check if conversion succeeded
                if process.returncode != 0:
                    error_msg = process.stderr.strip() if process.stderr else "Unknown error"
                    results['errors'].append(f"{filename}: {error_msg}")
                    results['failed'] += 1

                    # Clean up partial CHD if it exists
                    if os.path.exists(chd_path):
                        try:
                            os.remove(chd_path)
                        except:
                            pass
                    continue

                # Verify CHD was created
                if not os.path.exists(chd_path):
                    results['errors'].append(f"{filename}: CHD file not created")
                    results['failed'] += 1
                    continue

                results['converted'] += 1

                # Delete source files if requested
                if delete_source:
                    try:
                        # Remove the primary file
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)

                        # For CUE files, also delete the BIN files
                        if mode == "cue_bin":
                            for bin_file in bin_files:
                                bin_path = os.path.join(current_folder, bin_file)
                                if os.path.exists(bin_path):
                                    try:
                                        os.chmod(bin_path, 0o777)
                                        os.remove(bin_path)
                                    except Exception as e:
                                        results['errors'].append(f"{bin_file}: Failed to delete - {str(e)}")
                    except Exception as e:
                        results['errors'].append(f"{filename}: Converted but failed to delete source - {str(e)}")

            except subprocess.TimeoutExpired:
                results['errors'].append(f"{filename}: Conversion timed out")
                results['failed'] += 1
                # Clean up partial CHD
                if os.path.exists(chd_path):
                    try:
                        os.remove(chd_path)
                    except:
                        pass
            except Exception as e:
                results['errors'].append(f"{filename}: {str(e)}")
                results['failed'] += 1

    def _show_conversion_results(self):
        """Show conversion results and update UI (runs in main thread)"""
        results = self.conversion_results

        # Show results
        result_msg = f"Files converted: {results['converted']}\n"
        result_msg += f"Files skipped: {results['skipped']}\n"
        result_msg += f"Files failed: {results['failed']}"

        if results['errors']:
            result_msg += f"\n\nIssues ({len(results['errors'])}):\n" + "\n".join(results['errors'][:10])
            if len(results['errors']) > 10:
                result_msg += f"\n... and {len(results['errors']) - 10} more"

        show_info(self.root, "Conversion Complete", result_msg)

        # Refresh the conversion list
        self.refresh_conversion_lists()
