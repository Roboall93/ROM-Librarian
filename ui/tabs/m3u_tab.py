"""
M3U Tab for ROM Librarian
Creates M3U playlist files for multi-disc games
"""

import os
import re
import shutil
import threading
import tkinter as tk
from tkinter import ttk
from ui.tabs.base_tab import BaseTab
from ui import (
    ToolTip, ProgressDialog, show_info, show_error, show_warning, ask_yesno,
    create_scrolled_treeview, sort_treeview, parse_size
)


# Check if ttkbootstrap is available (imported from main module)
try:
    import rom_manager
    TTKBOOTSTRAP_AVAILABLE = rom_manager.TTKBOOTSTRAP_AVAILABLE
except:
    TTKBOOTSTRAP_AVAILABLE = False


class M3UTab(BaseTab):
    """Tab for creating M3U playlist files for multi-disc games"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)
        self.setup()
        self.add_to_notebook("M3U Creation")

    def setup(self):
        """Setup the M3U playlist creation tab"""
        # === GUIDANCE TEXT ===
        guidance_frame = ttk.Frame(self.tab)
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
        settings_frame = ttk.LabelFrame(self.tab, text="Scan Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Scan mode
        scan_mode_frame = ttk.Frame(settings_frame)
        scan_mode_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scan_mode_frame, text="Scan Mode:", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

        self.scan_mode = tk.StringVar(value="folder_only")

        rb1 = ttk.Radiobutton(scan_mode_frame, text="This folder only",
                              variable=self.scan_mode, value="folder_only")
        rb1.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb1, "Scan only the selected ROM folder")

        rb2 = ttk.Radiobutton(scan_mode_frame, text="Include subfolders",
                              variable=self.scan_mode, value="with_subfolders")
        rb2.pack(anchor=tk.W, padx=(20, 0))
        ToolTip(rb2, "Scan the selected folder and all subdirectories")

        # Scan button
        scan_btn_frame = ttk.Frame(settings_frame)
        scan_btn_frame.pack(fill=tk.X)

        ttk.Button(scan_btn_frame, text="Refresh",
                  command=self.scan).pack(side=tk.LEFT, padx=(0, 5))

        self.scan_btn = ttk.Button(scan_btn_frame, text="Scan for Multi-Disc Games",
                                   command=self.scan)
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.scan_status_var = tk.StringVar(value="Select a ROM folder and click scan")
        ttk.Label(scan_btn_frame, textvariable=self.scan_status_var).pack(side=tk.LEFT)

        # === RESULTS DISPLAY ===
        results_frame = ttk.LabelFrame(self.tab, text="Multi-Disc Games Found", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Summary
        self.summary_var = tk.StringVar(value="No scan performed yet")
        ttk.Label(results_frame, textvariable=self.summary_var,
                  font=("TkDefaultFont", 9)).pack(anchor=tk.W, pady=(0, 5))

        # Results tree
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = create_scrolled_treeview(
            tree_frame,
            ("select", "game_name", "disc_count", "location", "status"),
            show="headings"
        )
        self.tree.heading("select", text="☑")
        self.tree.heading("game_name", text="Game Name",
                          command=lambda: sort_treeview(self.tree, "game_name", False, parse_size))
        self.tree.heading("disc_count", text="Discs",
                          command=lambda: sort_treeview(self.tree, "disc_count", False, parse_size))
        self.tree.heading("location", text="Location",
                          command=lambda: sort_treeview(self.tree, "location", False, parse_size))
        self.tree.heading("status", text="Status",
                          command=lambda: sort_treeview(self.tree, "status", False, parse_size))
        self.tree.column("select", width=30, anchor="center")
        self.tree.column("game_name", width=350)
        self.tree.column("disc_count", width=60, anchor="center")
        self.tree.column("location", width=300)
        self.tree.column("status", width=120)

        # Configure tag colors - only highlight done/error, ready uses default background
        if TTKBOOTSTRAP_AVAILABLE and hasattr(self.root, 'style'):
            colors = self.root.style.colors
            self.tree.tag_configure("done", background=colors.success)
            self.tree.tag_configure("error", background=colors.danger, foreground="white")
        else:
            self.tree.tag_configure("done", background="#d4edda")
            self.tree.tag_configure("error", background="#f8d7da")

        # Bind click for checkbox toggle
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Initialize selection tracking
        self.selection = {}  # item_id -> True/False
        self.disc_data = {}  # item_id -> {'game_name': str, 'discs': [(disc_num, filepath)], 'folder': str}

        # === ACTIONS ===
        actions_frame = ttk.Frame(self.tab)
        actions_frame.pack(fill=tk.X)

        # Selection buttons
        select_frame = ttk.Frame(actions_frame)
        select_frame.pack(fill=tk.X, pady=(0, 10))

        self.select_all_btn = ttk.Button(select_frame, text="Select All",
                                         command=self.select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.deselect_all_btn = ttk.Button(select_frame, text="Deselect All",
                                           command=self.deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=(0, 20))

        # Create M3U button
        self.create_btn = ttk.Button(select_frame, text="Create M3U Files for Selected",
                                     command=self.create_files, state="disabled")
        self.create_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(self.create_btn,
                "Creates .m3u playlist files and moves disc files to .hidden folder")

        # Info label
        info_label = ttk.Label(select_frame,
                               text="Creates .m3u files and moves discs to .hidden/ folder",
                               font=("TkDefaultFont", 8), foreground="#666666")
        info_label.pack(side=tk.LEFT)

    def _on_tree_click(self, event):
        """Handle click on M3U tree to toggle checkbox"""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        column = self.tree.identify_column(event.x)

        # Only handle checkbox column clicks
        if column == "#1":
            current_state = self.selection.get(item, True)
            self.selection[item] = not current_state

            # Update checkbox display
            new_checkbox = "☐" if current_state else "☑"
            self.tree.set(item, "select", new_checkbox)

            self._update_create_button()
            return "break"

    def _update_create_button(self):
        """Update the create button based on selection"""
        selected_count = sum(1 for v in self.selection.values() if v)
        if selected_count > 0:
            self.create_btn.config(state="normal",
                                   text=f"Create M3U Files for Selected ({selected_count})")
        else:
            self.create_btn.config(state="disabled",
                                   text="Create M3U Files for Selected")

    def select_all(self):
        """Select all items in M3U tree"""
        for item in self.tree.get_children():
            # Only select items that aren't already done
            status = self.tree.set(item, "status")
            if status != "Done":
                self.selection[item] = True
                self.tree.set(item, "select", "☑")
        self._update_create_button()

    def deselect_all(self):
        """Deselect all items in M3U tree"""
        for item in self.tree.get_children():
            self.selection[item] = False
            self.tree.set(item, "select", "☐")
        self._update_create_button()

    def scan(self):
        """Scan for multi-disc games"""
        current_folder = self.get_current_folder()
        if not current_folder or not os.path.exists(current_folder):
            show_warning(self.root, "No Folder",
                        "Please select a ROM folder first using the Browse button at the top")
            return

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.selection.clear()
        self.disc_data.clear()

        self.scan_status_var.set("Scanning...")
        self.scan_btn.config(state="disabled")
        self.root.update()

        # Run scan in background
        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()

    def _scan_worker(self):
        """Background worker for scanning multi-disc games"""
        try:
            scan_mode = self.scan_mode.get()
            scan_folder = self.get_current_folder()

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
            self.root.after(0, lambda: self._display_results(multi_disc_games))

        except Exception as e:
            self.root.after(0, lambda: show_error(self.root, "Scan Error", str(e)))
            self.root.after(0, lambda: self.scan_btn.config(state="normal"))
            self.root.after(0, lambda: self.scan_status_var.set("Scan failed"))

    def _display_results(self, multi_disc_games):
        """Display multi-disc scan results"""
        self.scan_btn.config(state="normal")

        if not multi_disc_games:
            self.summary_var.set("No multi-disc games found")
            self.scan_status_var.set("Scan complete - no multi-disc games found")
            self.create_btn.config(state="disabled")
            return

        # Clear and populate tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        total_games = 0
        total_discs = 0
        current_folder = self.get_current_folder()

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
            if folder == current_folder:
                display_folder = "(root)"
            else:
                display_folder = os.path.relpath(folder, current_folder)

            item_id = self.tree.insert("", tk.END, values=(
                checkbox,
                game_display_name,
                str(len(disc_list)),
                display_folder,
                status
            ), tags=(tag,))

            self.selection[item_id] = selected
            self.disc_data[item_id] = {
                'game_name': base_name,  # Keep extension for M3U filename
                'discs': disc_list,
                'folder': folder
            }

            total_games += 1
            total_discs += len(disc_list)

        self.summary_var.set(f"Found {total_games} multi-disc games ({total_discs} total disc files)")
        self.scan_status_var.set("Scan complete")
        self._update_create_button()

    def create_files(self):
        """Create M3U files for selected games"""
        # Get selected items
        items_to_process = []
        for item_id, is_selected in self.selection.items():
            if is_selected and item_id in self.disc_data:
                status = self.tree.set(item_id, "status")
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
                data = self.disc_data[item_id]
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
                        self.root.after(0, lambda iid=item_id: self._mark_done(iid))
                    else:
                        failed += 1

                except Exception as e:
                    errors.append(f"{game_name}: {str(e)}")
                    failed += 1
                    # Update tree item as error
                    self.root.after(0, lambda iid=item_id: self._mark_error(iid))

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
            self.root.after(0, self._update_create_button)

        # Run in background
        thread = threading.Thread(target=create_worker, daemon=True)
        thread.start()

    def _mark_done(self, item_id):
        """Mark an M3U tree item as done"""
        self.tree.set(item_id, "status", "Done")
        self.tree.set(item_id, "select", "☐")
        self.tree.item(item_id, tags=("done",))
        self.selection[item_id] = False

    def _mark_error(self, item_id):
        """Mark an M3U tree item as error"""
        self.tree.set(item_id, "status", "Error")
        self.tree.item(item_id, tags=("error",))
