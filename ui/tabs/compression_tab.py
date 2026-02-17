"""
Compression tab for ROM Librarian
Handles compression and extraction of ROM files to/from ZIP and 7z archives
"""

import os
import tkinter as tk
from tkinter import ttk
import threading
import zipfile
import py7zr

from .base_tab import BaseTab
from ui.helpers import ProgressDialog, show_info, ask_yesno
from ui.tree_utils import create_scrolled_treeview, sort_treeview, get_files_from_tree
from ui.formatters import format_size, parse_size, format_operation_results
from core import logger


class CompressionTab(BaseTab):
    """Tab for compressing and extracting ROM files"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)
        self.compression_format = tk.StringVar(value="zip")  # "zip" or "7z"
        self.setup()
        self.add_to_notebook("Compression")

    def setup(self):
        """Setup the compression tab with dual-pane layout"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
        guidance_frame.pack(fill=tk.X, pady=(0, 10))
        guidance_label = ttk.Label(guidance_frame,
                                   text="Compress ROMs to save space. Extract archives when needed.",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="#666666")
        guidance_label.pack(anchor=tk.W)

        # Top control frame - File extension selector
        control_frame = ttk.Frame(self.tab)
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
        panes_frame = ttk.Frame(self.tab)
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

        self.uncompressed_tree = create_scrolled_treeview(left_list_frame, ("filename", "size", "status"))
        self.uncompressed_tree.heading("filename", text="Filename",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "filename", False, parse_size))
        self.uncompressed_tree.heading("size", text="Size",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "size", False, parse_size))
        self.uncompressed_tree.heading("status", text="Status",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "status", False, parse_size))
        self.uncompressed_tree.column("filename", width=250)
        self.uncompressed_tree.column("size", width=80)
        self.uncompressed_tree.column("status", width=70)
        self.manager.setup_custom_selection(self.uncompressed_tree)

        # Left pane buttons
        left_btn_frame = ttk.Frame(left_pane)
        left_btn_frame.pack(fill=tk.X)

        # Archive format selection
        format_frame = ttk.Frame(left_btn_frame)
        format_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(format_frame, text="Archive Format:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(format_frame, text="ZIP", variable=self.compression_format, value="zip").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(format_frame, text="7z (better compression)", variable=self.compression_format, value="7z").pack(side=tk.LEFT)

        self.delete_originals_var = tk.IntVar(value=0)
        tk.Checkbutton(left_btn_frame, text="Delete originals after compression",
                       variable=self.delete_originals_var, onvalue=1, offvalue=0).pack(anchor=tk.W, pady=(0, 5))

        left_btns = ttk.Frame(left_btn_frame)
        left_btns.pack(fill=tk.X)
        ttk.Button(left_btns, text="Refresh",
                  command=self.refresh_compression_lists).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="Compress Selected",
                  command=self.compress_selected_roms).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="Compress All",
                  command=self.compress_all_roms).pack(side=tk.LEFT, padx=(0, 5))
        self.delete_archived_btn = ttk.Button(left_btns, text="Delete Archived Only",
                  command=self.delete_archived_roms, state="disabled")
        self.delete_archived_btn.pack(side=tk.LEFT)

        # === RIGHT PANE: Compressed Archives ===
        right_pane = ttk.LabelFrame(panes_frame, text="Compressed Archives (ZIP/7z)", padding="10")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Right pane list
        right_list_frame = ttk.Frame(right_pane)
        right_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.compressed_tree = create_scrolled_treeview(right_list_frame, ("filename", "size"))
        self.compressed_tree.heading("filename", text="Filename",
                                     command=lambda: sort_treeview(self.compressed_tree, "filename", False, parse_size))
        self.compressed_tree.heading("size", text="Size",
                                     command=lambda: sort_treeview(self.compressed_tree, "size", False, parse_size))
        self.compressed_tree.column("filename", width=300)
        self.compressed_tree.column("size", width=100)
        self.manager.setup_custom_selection(self.compressed_tree)

        # Right pane buttons
        right_btn_frame = ttk.Frame(right_pane)
        right_btn_frame.pack(fill=tk.X)

        self.delete_archives_var = tk.IntVar(value=0)
        tk.Checkbutton(right_btn_frame, text="Delete archives after extraction",
                       variable=self.delete_archives_var, onvalue=1, offvalue=0).pack(anchor=tk.W, pady=(0, 5))

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
        ttk.Label(self.tab, textvariable=self.compression_status_var).pack(fill=tk.X)


    def set_compression_extension(self, extension):
        """Set the file extension filter"""
        self.compress_ext_var.set(extension)
        self.refresh_compression_lists()

    def refresh_compression_lists(self):
        """Refresh both uncompressed and compressed file lists"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Clear both trees
        for tree in (self.uncompressed_tree, self.compressed_tree):
            for item in tree.get_children():
                tree.delete(item)

        # Get extension pattern
        ext_pattern = self.compress_ext_var.get()
        if not ext_pattern.startswith("*."):
            ext_pattern = f"*.{ext_pattern}"

        try:
            # Get all files in folder
            all_files = []
            for filename in os.listdir(current_folder):
                file_path = os.path.join(current_folder, filename)
                if os.path.isfile(file_path):
                    all_files.append(filename)

            # Populate left pane (uncompressed files matching extension)
            import fnmatch
            uncompressed_count = 0
            archived_count = 0
            for filename in all_files:
                if fnmatch.fnmatch(filename.lower(), ext_pattern.lower()):
                    file_path = os.path.join(current_folder, filename)
                    size = os.path.getsize(file_path)
                    size_str = format_size(size)

                    # Check if corresponding ZIP or 7z exists
                    base_name = os.path.splitext(filename)[0]
                    zip_name = base_name + ".zip"
                    seven_z_name = base_name + ".7z"
                    status = "Archived" if (zip_name in all_files or seven_z_name in all_files) else ""
                    if status == "Archived":
                        archived_count += 1

                    self.uncompressed_tree.insert("", "end", values=(filename, size_str, status))
                    uncompressed_count += 1

            # Populate right pane (ZIP and 7z archives)
            compressed_count = 0
            for filename in all_files:
                if filename.lower().endswith((".zip", ".7z")):
                    file_path = os.path.join(current_folder, filename)
                    size = os.path.getsize(file_path)
                    size_str = format_size(size)
                    self.compressed_tree.insert("", "end", values=(filename, size_str))
                    compressed_count += 1

            # Update status
            status_msg = f"Uncompressed: {uncompressed_count} | Compressed: {compressed_count}"
            self.compression_status_var.set(status_msg)

            # Enable/disable "Delete Archived Only" button
            if archived_count > 0:
                self.delete_archived_btn.config(state="normal")
            else:
                self.delete_archived_btn.config(state="disabled")

        except Exception as e:
            show_info(self.root, "Error", f"Failed to refresh lists:\n{str(e)}")

    def compress_selected_roms(self):
        """Compress selected ROMs from the left pane"""
        self._compress_roms(selected_only=True)

    def compress_all_roms(self):
        """Compress all ROMs from the left pane"""
        self._compress_roms(selected_only=False)

    def _compress_roms(self, selected_only=True):
        """Compress ROM files from the left pane"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get files from tree
        files = get_files_from_tree(self.uncompressed_tree, current_folder, selected_only)
        if not files:
            msg = "Please select files to compress" if selected_only else "No files to compress"
            show_info(self.root, "Compress", msg)
            return

        compress_list = [f[0] for f in files]

        # Get compression format
        compression_format = self.compression_format.get()

        # Confirm and start
        delete_originals = bool(self.delete_originals_var.get())
        label = "selected" if selected_only else "ALL"
        format_label = "7z" if compression_format == "7z" else "ZIP"
        warning = "WARNING: Original files will be DELETED after compression!" if delete_originals else None
        progress, _ = self.manager.confirm_and_start_operation(
            f"Compress {len(compress_list)} {label} file(s) to {format_label}", 1,
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

        self.manager.run_worker_thread(
            self._perform_compression,
            args=(compress_list, progress, delete_originals, compression_format, self.compression_results),
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
        """Extract ZIP and 7z files from the right pane"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get files from tree
        files = get_files_from_tree(self.compressed_tree, current_folder, selected_only)
        if not files:
            msg = "Please select archives to extract" if selected_only else "No archives to extract"
            show_info(self.root, "Extract", msg)
            return

        archive_files = [f[0] for f in files]

        # Confirm and start
        delete_archives = bool(self.delete_archives_var.get())
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: Archives will be DELETED after extraction!" if delete_archives else None
        progress, _ = self.manager.confirm_and_start_operation(
            f"Extract {len(archive_files)} {label} archive(s)", 1,
            warning_msg=warning, title="Confirm Extraction"
        )
        if not progress:
            return

        # Reset progress for actual file count
        progress.total_items = len(archive_files)
        progress.progress_bar.config(maximum=len(archive_files))

        self.uncompression_results = {
            'extracted': 0, 'skipped': 0, 'failed': 0, 'errors': []
        }

        self.manager.run_worker_thread(
            self._perform_uncompression,
            args=(archive_files, progress, delete_archives, self.uncompression_results),
            progress=progress,
            on_complete=self._show_uncompression_results
        )

    def delete_selected_zips(self):
        """Delete selected archive files from the right pane"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        files = get_files_from_tree(self.compressed_tree, current_folder, selected_only=True)
        if not files:
            show_info(self.root, "Delete", "Please select archives to delete")
            return

        if not ask_yesno(self.root, "Confirm Delete",
                        f"Delete {len(files)} selected archive(s)?\n\nThis cannot be undone!"):
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

        result_msg = format_operation_results({'Deleted': deleted, 'Failed': failed}, errors)
        show_info(self.root, "Delete Complete", result_msg)
        self.refresh_compression_lists()

    def delete_archived_roms(self):
        """Delete ONLY ROM files that have corresponding ZIP archives (safe cleanup)"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get files with "Archived" status
        files_to_delete = []
        for item in self.uncompressed_tree.get_children():
            values = self.uncompressed_tree.item(item, "values")
            if len(values) > 2 and values[2] == "Archived":
                full_path = os.path.join(current_folder, values[0])
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
            msg = format_operation_results(
                {'Deleted': self.delete_results['deleted'], 'Failed': self.delete_results['failed']},
                self.delete_results['errors']
            )
            show_info(self.root, "Delete Complete", msg)
            self.refresh_compression_lists()

        self.manager.run_worker_thread(do_delete, progress=progress, on_complete=show_results)

    def _perform_compression(self, compress_list, progress, delete_originals, compression_format, results):
        """Perform the actual compression operations (runs in worker thread)"""
        current_folder = self.get_current_folder()

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

                # Determine archive name and path based on format
                if compression_format == "7z":
                    archive_ext = ".7z"
                else:
                    archive_ext = ".zip"

                archive_name = os.path.splitext(filename)[0] + archive_ext
                archive_path = os.path.join(current_folder, archive_name)

                # Skip if archive already exists
                if os.path.exists(archive_path):
                    results['errors'].append(f"{filename}: {archive_ext.upper()} already exists")
                    results['skipped'] += 1
                    continue

                # Compress based on format
                if compression_format == "7z":
                    # Use py7zr for 7z compression
                    with py7zr.SevenZipFile(archive_path, 'w') as archive:
                        archive.write(file_path, arcname=filename)
                else:
                    # Use zipfile for ZIP compression
                    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                        zipf.write(file_path, filename)

                # Verify archive was created
                if not os.path.exists(archive_path):
                    results['errors'].append(f"{filename}: Failed to create {archive_ext.upper()}")
                    results['failed'] += 1
                    continue

                compressed_size = os.path.getsize(archive_path)
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

    def _perform_uncompression(self, archive_files, progress, delete_archives, results):
        """Perform the actual uncompression operations (runs in worker thread)"""
        current_folder = self.get_current_folder()

        for idx, archive_path in enumerate(archive_files, 1):
            archive_filename = os.path.basename(archive_path)
            progress.update(idx, archive_filename)

            try:
                is_7z = archive_path.lower().endswith('.7z')

                # Get list of files that will be extracted
                file_list = []
                if is_7z:
                    with py7zr.SevenZipFile(archive_path, 'r') as archive:
                        file_list = archive.getnames()
                else:
                    # Verify it's a valid ZIP file
                    if not zipfile.is_zipfile(archive_path):
                        results['errors'].append(f"{archive_filename}: Not a valid ZIP file")
                        results['skipped'] += 1
                        continue
                    with zipfile.ZipFile(archive_path, 'r') as zipf:
                        file_list = zipf.namelist()

                # Check if any files would be overwritten
                existing_files = []
                for filename in file_list:
                    target_path = os.path.join(current_folder, filename)
                    if os.path.exists(target_path):
                        existing_files.append(filename)

                # Skip if files would be overwritten
                if existing_files:
                    results['errors'].append(f"{archive_filename}: Would overwrite {len(existing_files)} file(s)")
                    results['skipped'] += 1
                    continue

                # Extract archive
                if is_7z:
                    with py7zr.SevenZipFile(archive_path, 'r') as archive:
                        archive.extractall(path=current_folder)
                else:
                    with zipfile.ZipFile(archive_path, 'r') as zipf:
                        zipf.extractall(current_folder)

                results['extracted'] += 1

                # Delete archive if requested
                if delete_archives:
                    try:
                        os.remove(archive_path)
                    except Exception as e:
                        results['errors'].append(f"{archive_filename}: Extracted but failed to delete archive - {str(e)}")

            except Exception as e:
                results['errors'].append(f"{archive_filename}: {str(e)}")
                results['failed'] += 1

    def _show_uncompression_results(self):
        """Show uncompression results and update UI (runs in main thread)"""
        results = self.uncompression_results

        # Show results
        result_msg = f"Archives extracted: {results['extracted']}\n"
        result_msg += f"Archives skipped: {results['skipped']}\n"
        result_msg += f"Archives failed: {results['failed']}"

        if results['errors']:
            result_msg += f"\n\nIssues ({len(results['errors'])}):\n" + "\n".join(results['errors'][:10])
            if len(results['errors']) > 10:
                result_msg += f"\n... and {len(results['errors']) - 10} more"

        show_info(self.root, "Extraction Complete", result_msg)

        # Refresh the compression lists
        self.refresh_compression_lists()
