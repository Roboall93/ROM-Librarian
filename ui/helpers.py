"""
UI Helper classes and functions for ROM Librarian
Includes dialogs, tooltips, and utility functions
"""

import os
import tkinter as tk
from tkinter import ttk
from core.logging_setup import logger
from core.constants import ICON_PATH


def set_window_icon(window):
    """Set the app icon on a window"""
    try:
        if os.path.exists(ICON_PATH):
            window.iconbitmap(ICON_PATH)
            logger.debug(f"Window icon set from {ICON_PATH}")
        else:
            logger.warning(f"Icon file not found at {ICON_PATH}")
    except Exception as e:
        logger.warning(f"Failed to set window icon: {e}")


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
