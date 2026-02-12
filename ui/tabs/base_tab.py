"""
Base class for all tab controllers in ROM Librarian
Provides common patterns and shared functionality
"""

import tkinter as tk
from tkinter import ttk


class BaseTab:
    """Base class for all tab controllers"""

    def __init__(self, parent_notebook, root, manager):
        """
        Initialize the tab controller.

        Args:
            parent_notebook: The ttk.Notebook widget to add this tab to
            root: The main Tk root window
            manager: Reference to ROMManager for shared state access
        """
        self.notebook = parent_notebook
        self.root = root
        self.manager = manager

        # Create the tab frame
        self.tab = ttk.Frame(parent_notebook, padding="5")

        # Tab-specific state
        self.widgets = {}  # Store widget references

    def add_to_notebook(self, title):
        """Add this tab to the notebook with the given title"""
        self.notebook.add(self.tab, text=title)

    def setup(self):
        """Setup the tab UI - must be overridden in subclasses"""
        raise NotImplementedError("Subclasses must implement setup()")

    # Common accessor methods for shared state

    def get_current_folder(self):
        """Get current folder from manager"""
        return self.manager.current_folder

    def get_files_data(self):
        """Get files data from manager"""
        return self.manager.files_data

    def set_status(self, message):
        """Set status bar message"""
        if hasattr(self.manager, 'status_label'):
            self.manager.status_label.config(text=message)

    def get_config(self):
        """Get configuration from manager"""
        return self.manager.config

    def save_config(self):
        """Trigger config save in manager"""
        if hasattr(self.manager, 'save_current_config'):
            self.manager.save_current_config()
