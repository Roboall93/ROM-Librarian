"""
Compression tab for ROM Librarian
Handles compression and extraction of ROM files to/from ZIP archives
"""

import os
import pathlib
import re
import shutil
import tempfile
import tkinter as tk
import zipfile
from tkinter import ttk, messagebox
import py7zr

from ui.formatters import format_size, parse_size, format_operation_results
from ui.helpers import ProgressDialog, show_info, ask_yesno
from ui.tree_utils import create_scrolled_treeview, sort_treeview, get_files_from_tree
from .base_tab import BaseTab

from pathlib import Path



class CompressionTab(BaseTab):
    """Tab for compressing and extracting ROM files"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)
        self.setup()
        self.add_to_notebook("Compression")
        # self.update_vimms_delete_button()

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
        common_exts = ["*.gba", "*.gbc", "*.gb", "*.smc", "*.sfc", "*.nes", "*.md", "*.n64", "*.rvz", "*.j64", "*.ciso", "*.iso", "*.chd"]
        for ext in common_exts:
            btn = ttk.Button(control_frame, text=ext.replace("*.", "").upper(), width=5,
                           command=lambda e=ext: self.set_compression_extension(e))
            btn.pack(side="left", padx=2)

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
        left_list_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.uncompressed_tree = create_scrolled_treeview(left_list_frame, ("filename", "size", "status"))
        self.uncompressed_tree.heading("filename", text="Filename", anchor="w",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "filename", False, parse_size))
        self.uncompressed_tree.heading("size", text="Size", anchor="w",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "size", False, parse_size))
        self.uncompressed_tree.heading("status", text="Status", anchor="w",
                                       command=lambda: sort_treeview(self.uncompressed_tree, "status", False, parse_size))
        self.uncompressed_tree.column("filename", width=250)
        self.uncompressed_tree.column("size", width=80)
        self.uncompressed_tree.column("status", width=70)
        self.manager.setup_custom_selection(self.uncompressed_tree)

        style = ttk.Style()
        style.theme_use("clam")  # Important on Windows if colors don't apply
        style.configure(
            "Custom.Treeview.Heading",
            background="#2d2d2d",
            foreground="white"
        )

        # self.uncompressed_tree.configure(style="Custom.Treeview")

        # Left pane buttons
        left_btn_frame = ttk.Frame(left_pane)
        left_btn_frame.pack(fill=tk.X)

        self.delete_originals_var = tk.IntVar(value=0)
        ttk.Checkbutton(left_btn_frame, text="Delete originals after compression",
                       variable=self.delete_originals_var, onvalue=1, offvalue=0).pack(anchor=tk.W, pady=(0, 5))

        left_btns = ttk.Frame(left_btn_frame)
        left_btns.pack(fill=tk.X)
        ttk.Button(left_btns, text="Refresh",
                  command=self.refresh_compression_lists).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="Compress Selected",
                  command=self.compress_selected_roms).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btns, text="Compress All",
                  command=self.compress_all_roms).pack(side=tk.LEFT, padx=(0, 5))
        # self.delete_vimms_btn = ttk.Button(left_btns, text="Delete Vimm's Lair.txt",
        #            command=self.delete_vimms_text)
        self.delete_archived_btn = ttk.Button(left_btns, text="Delete Archived Only",
                  command=self.delete_archived_roms, state="disabled")

        # # Disable if file exists
        # file_path = "Vimm's Lair.txt"
        # if os.path.exists(file_path):
        #     self.delete_vimms_btn.state(["!disabled"])
        #     info = self.parse_vimms_text("Vimm's Lair.txt")
        #     self.update_compression_info(info)
        #     print(info)

        # self.delete_vimms_btn.pack(side="left", padx=(0, 5))
        self.delete_archived_btn.pack(side="left", padx=(0, 5))

        # === RIGHT PANE: Compressed Archives ===
        right_pane = ttk.LabelFrame(panes_frame, text="Compressed Archives", padding="10")
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Right pane list
        right_list_frame = ttk.Frame(right_pane)
        right_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.compressed_tree = create_scrolled_treeview(right_list_frame, ("filename", "size"))
        self.compressed_tree.heading("filename", text="Filename", anchor="w",
                                     command=lambda: sort_treeview(self.compressed_tree, "filename", False, parse_size))
        self.compressed_tree.heading("size", text="Size", anchor="w",
                                     command=lambda: sort_treeview(self.compressed_tree, "size", False, parse_size))
        self.compressed_tree.column("filename", width=300)
        self.compressed_tree.column("size", width=100)
        self.manager.setup_custom_selection(self.compressed_tree)

        # Right pane buttons
        right_btn_frame = ttk.Frame(right_pane)
        right_btn_frame.pack(fill=tk.X)
        options_frame = ttk.Frame(right_btn_frame)
        options_frame.pack(anchor="w", fill=tk.X, pady=(0, 5))
        self.delete_archives_var = tk.IntVar(value=0)
        ttk.Checkbutton(options_frame, text="Delete archives after extraction",
                       variable=self.delete_archives_var, onvalue=1, offvalue=0).pack(side="left", pady=(0, 5))
        self.check_overwrite_var = tk.IntVar(value=0)
        ttk.Checkbutton(options_frame, text="Check and Avoid Overwrite",
                       variable=self.check_overwrite_var, onvalue=1, offvalue=0).pack(side="left", pady=(0, 5))
        right_btns = ttk.Frame(right_btn_frame)
        right_btns.pack(fill=tk.X)
        ttk.Button(right_btns, text="Extract Selected",
                  command=self.extract_selected_zips).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_btns, text="Extract All",
                  command=self.extract_all_zips).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_btns, text="Delete Selected",
                  command=self.delete_selected_zips).pack(side=tk.LEFT)
        self.delete_unarchived_btn = (ttk.Button(right_btns, text="Delete Extracted Only",
                  command=self.delete_extracted_roms, state="disabled"))
        self.delete_unarchived_btn.pack(side=tk.LEFT)
        # Status bar for compression tab
        self.compression_status_var = tk.StringVar(value="")
        ttk.Label(self.tab, textvariable=self.compression_status_var).pack(fill=tk.X)
        # Info bar for compression tab
        self.compression_info_var = tk.StringVar(value="")
        ttk.Label(self.tab, textvariable=self.compression_info_var).pack(fill=tk.X)

    def update_compression_info(self, info: dict):
        single_line = True
        if single_line:
            text = (
                "Vimm's Lair.txt Info : "
                f"{info.get('platform', '?')} | "
                f"{info.get('iso_name', '?')} | "
                f"CRC {info.get('crc', '-')} | "
                f"MD5 {info.get('md5', '-')}"
            )
        else:
            text = (
                f"Platform : {info.get('platform', '-')}\n"
                f"File     : {info.get('iso_name', '-')}\n"
                f"CRC      : {info.get('crc', '-')}\n"
                f"MD5      : {info.get('md5', '-')}\n"
                f"SHA-1    : {info.get('sha1', '-')}\n"
                f"Date     : {info.get('date', '-')}"
            )

        self.compression_info_var.set(text)

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

                    # Check if corresponding ZIP exists
                    zip_name = os.path.splitext(filename)[0] + ".zip"
                    z7p_name = os.path.splitext(filename)[0] + ".7z"
                    status = "Archived" if (zip_name in all_files or z7p_name in all_files) else ""

                    file_stem = Path(filename).stem  # removes only last suffix
                    file_stem2 = Path(file_stem).stem  # removes second-to-last suffix, if any

                    # Check archives with all plausible stems
                    possible_archives = [
                        f"{file_stem}.zip",
                        f"{file_stem2}.zip",
                        f"{file_stem}.7z",
                        f"{file_stem2}.7z"
                    ]

                    status = "Archived" if any(a in all_files for a in possible_archives) else ""
                    if status == "Archived":
                        archived_count += 1

                    self.uncompressed_tree.insert("", "end", values=(filename, size_str, status))
                    uncompressed_count += 1

            # Populate right pane (ZIP archives)
            compressed_count = 0
            for filename in all_files:
                if filename.lower().endswith(".zip") or filename.lower().endswith(".7z"):
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
                self.delete_unarchived_btn.config(state="normal")
            else:
                self.delete_archived_btn.config(state="disabled")
                self.delete_unarchived_btn.config(state="disabled")
        except Exception as e:
            show_info(self.root, "Error", f"Failed to refresh lists:\n{str(e)}")

    def compress_selected_roms(self):
        """Compress selected ROMs from the left pane"""
        self._compress_roms(selected_only=True)

    def compress_all_roms(self):
        """Compress all ROMs from the left pane"""
        self._compress_roms(selected_only=False)

    def update_vimms_delete_button(self):

        # Disable if file exists
        # file_path = "Vimm's Lair.txt"
        # if os.path.exists(file_path):
        #     self.delete_vimms_btn.state(["!disabled"])
        #     info = self.parse_vimms_text("Vimm's Lair.txt")
        #     self.update_compression_info(info)
        #     print(info)

        current_folder = self.get_current_folder()
        if current_folder is not None:
            file_path = Path(current_folder) / "Vimm's Lair.txt"

            if file_path.exists():
                self.delete_vimms_btn.state(["!disabled"])
                text = Path(file_path).read_text(encoding="utf-8")

                info = self.parse_vimms_text(text)
                self.update_compression_info(info)
            else:
                self.delete_vimms_btn.state(["disabled"])

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

        # Confirm and start
        delete_originals = bool(self.delete_originals_var.get())
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: Original files will be DELETED after compression!" if delete_originals else None
        progress, _ = self.manager.confirm_and_start_operation(
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

        self.manager.run_worker_thread(
            self._perform_compression,
            args=(compress_list, progress, delete_originals, self.compression_results),
            progress=progress,
            on_complete=self._show_compression_results
        )

    def extract_selected_zips(self):
        """Extract selected ZIP files from the right pane"""
        self._extract_zips(selected_only=True)
        # Disable if file exists
        # self.update_vimms_delete_button()

    def extract_all_zips(self):
        """Extract all ZIP files from the right pane"""
        self._extract_zips(selected_only=False)
        # Disable if file exists
        # self.update_vimms_delete_button()

    def _extract_zips(self, selected_only=True):
        """Extract ZIP files from the right pane"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        # Get files from tree
        files = get_files_from_tree(self.compressed_tree, current_folder, selected_only)
        if not files:
            msg = "Please select ZIP files to extract" if selected_only else "No ZIP files to extract"
            show_info(self.root, "Extract", msg)
            return

        zip_files = [f[0] for f in files]

        # Confirm and start
        delete_zips = bool(self.delete_archives_var.get())
        label = "selected" if selected_only else "ALL"
        warning = "WARNING: ZIP files will be DELETED after extraction!" if delete_zips else None
        progress, _ = self.manager.confirm_and_start_operation(
            f"Extract {len(zip_files)} {label} ZIP file(s)", 1,
            warning_msg=warning, title="Confirm Extraction"
        )
        if not progress:
            return

        # Reset progress for actual file count
        progress.total_items = len(zip_files)
        progress.progress_bar.config(maximum=len(zip_files))

        self.uncompression_results = {
            'extracted': 0, 'skipped': 0, 'failed': 0, 'errors': []
        }

        self.manager.run_worker_thread(
            self._perform_uncompression,
            args=(zip_files, progress, delete_zips, self.uncompression_results),
            progress=progress,
            on_complete=self._show_uncompression_results
        )

    def delete_selected_zips(self):
        """Delete selected ZIP files from the right pane"""
        current_folder = self.get_current_folder()
        if not current_folder:
            return

        files = get_files_from_tree(self.compressed_tree, current_folder, selected_only=True)
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

        result_msg = format_operation_results({'Deleted': deleted, 'Failed': failed}, errors)
        show_info(self.root, "Delete Complete", result_msg)
        self.refresh_compression_lists()

    @staticmethod
    def parse_vimms_text(text):
        # text = Path(path).read_text(encoding="utf-8")

        def find(pattern):
            m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            return m.group(1).strip() if m else None

        return {
            "platform": find(r"This\s+(.+?)\s+game\s+is\s+verified"),
            "iso_name": find(r"^(.+\.(?:iso|bin|img|nrg|mdf|cue|chd|gdi))$"),
            "crc": find(r"CRC:\s*([A-Fa-f0-9]+)"),
            "md5": find(r"MD5:\s*([A-Fa-f0-9]+)"),
            "sha1": find(r"SHA-1:\s*([A-Fa-f0-9]+)"),
            "date": find(r"Date:\s*([\d\-]+)"),
        }

    def delete_vimms_text(self):
        current_folder = self.get_current_folder()
        file_path = Path(current_folder) / "Vimm's Lair.txt"

        if file_path.exists():
            try:
                text = Path(file_path).read_text(encoding="utf-8")
                info = self.parse_vimms_text(text)
                self.update_compression_info(info)
                print(info)
                file_path.unlink()
                messagebox.showinfo("Deleted", "Vimm's Lair.txt was deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file:\n{e}")
        else:
            messagebox.showwarning("Not Found", "Vimm's Lair.txt does not exist.")

        # Refresh button state
        self.update_vimms_delete_button()

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

    def delete_extracted_roms(self):
        """Delete ONLY archive files that have already been extracted (safe cleanup)"""
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

        confirm_msg = (f"Delete {len(files_to_delete)} archive file(s)?\n\n"
                      "These files all have been extracted.\n"
                      "The archive files will be deleted.\n\n"
                      "This cannot be undone. Continue?")
        if not ask_yesno(self.root, "Confirm Delete Archived Files", confirm_msg):
            return

        progress = ProgressDialog(self.root, "Deleting Archive Files", len(files_to_delete))
        self.delete_results = {'deleted': 0, 'failed': 0, 'errors': []}

        def do_delete():
            for idx, (filename, file_path) in enumerate(files_to_delete, 1):
                try:
                    base = Path(file_path)
                    for ext in (".zip", ".7z"):
                        archive = base.with_suffix(ext)
                        if archive.exists():
                            archive.unlink()  # delete the file
                            self.delete_results['deleted'] += 1
                    progress.update(idx, archive)
                    # os.chmod(archive, 0o777)
                    # os.remove(archive)
                    # self.delete_results['deleted'] += 1
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

    def _perform_compression(self, compress_list, progress, delete_originals, results):
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

                zip_name = os.path.splitext(filename)[0] + ".zip"
                zip_path = os.path.join(current_folder, zip_name)

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
        current_folder = self.get_current_folder()

        for idx, zip_path in enumerate(zip_files, 1):
            zip_filename = os.path.basename(zip_path)
            progress.update(idx, zip_filename)

            filepath = pathlib.Path(zip_path).absolute()
            extension = filepath.suffix.lower()

            try:
                if extension == ".7z":
                    if not py7zr.is_7zfile(zip_path):
                        results['errors'].append(f"{zip_filename}: Not a valid 7Z file")
                        results['skipped'] += 1
                        continue
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with py7zr.SevenZipFile(zip_path, mode="r") as z7pf:
                            z7pf.extractall(path=temp_dir)
                        for extracted_path in Path(temp_dir).rglob("*"):
                            if extracted_path.is_dir():
                                continue
                            filename = extracted_path.name
                            # 🎯 Handle Vimm's Lair.txt
                            if filename == "Vimm's Lair.txt":
                                # vimms_path = os.path.join(current_folder, filename)
                                text = Path(extracted_path).read_text(encoding="utf-8")
                                self.parse_vimms_text(text)
                                os.remove(extracted_path)
                                vimms_found = True
                                continue

                            target = Path(current_folder) / filename
                            check_overwrite = bool(self.check_overwrite_var.get())
                            if target.exists() and check_overwrite:
                                results['errors'].append(
                                    f"{zip_filename}: Would overwrite {filename}"
                                )
                                results['skipped'] += 1
                                continue
                            shutil.move(str(extracted_path), str(target))

                elif extension == ".zip":
                    if not zipfile.is_zipfile(zip_path):
                        results['errors'].append(f"{zip_filename}: Not a valid ZIP file")
                        results['skipped'] += 1
                        continue
                    with tempfile.TemporaryDirectory() as temp_dir:
                        with py7zr.SevenZipFile(zip_path, mode="r") as zipf:
                            zipf.extractall(path=temp_dir)
                        for extracted_path in Path(temp_dir).rglob("*"):
                            if extracted_path.is_dir():
                                continue
                            filename = extracted_path.name
                            # 🎯 Handle Vimm's Lair.txt
                            if filename == "Vimm's Lair.txt":
                                # vimms_path = os.path.join(current_folder, filename)
                                text = Path(extracted_path).read_text(encoding="utf-8")
                                self.parse_vimms_text(text)
                                os.remove(extracted_path)
                                vimms_found = True
                                continue

                            target = Path(current_folder) / filename
                            check_overwrite = bool(self.check_overwrite_var.get())
                            if target.exists() and check_overwrite:
                                results['errors'].append(
                                    f"{zip_filename}: Would overwrite {filename}"
                                )
                                results['skipped'] += 1
                                continue
                            shutil.move(str(extracted_path), str(target))

                if extracted_path != target and target.exists():
                    parent = target.parent
                    while parent != Path(current_folder):
                        if parent.is_dir() and not any(parent.iterdir()):
                            parent.rmdir()
                            parent = parent.parent
                        else:
                            break

                self.auto_detect_extension()
                results['extracted'] += 1

                # Delete archive if requested
                if delete_zips:
                    try:
                        os.remove(zip_path)
                    except Exception as e:
                        results['errors'].append(
                            f"{zip_filename}: Extracted but failed to delete archive - {str(e)}"
                        )

            except Exception as e:
                results['errors'].append(f"{zip_filename}: {str(e)}")
                results['failed'] += 1

    def auto_detect_extension(self):
        """Auto-detect ROM file extensions in the current folder"""
        current_folder = self.get_current_folder()
        if not current_folder:
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
            for item in os.listdir(current_folder):
                full_path = os.path.join(current_folder, item)
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
                    self.manager.status_var.set(detection_msg)
                else:
                    self.manager.status_var.set(f"Auto-detected: {most_common_count} {most_common_ext.upper()} files")
            else:
                # Check if we have zip files
                zip_count = sum(1 for _, _, path in self.files_data if path.lower().endswith('.zip'))
                if zip_count > 0:
                    self.manager.status_var.set(f"Loaded {len(self.files_data)} files ({zip_count} zipped)")
                else:
                    self.manager.status_var.set(f"Loaded {len(self.files_data)} files")

        except Exception as e:
            # Silently fail auto-detection
            pass

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

