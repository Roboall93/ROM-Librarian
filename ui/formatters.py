"""
Data formatting utilities for ROM Librarian
Provides file size and date formatting functions
"""

import os
from datetime import datetime


def format_size(size_bytes):
    """
    Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes

    Returns:
        Formatted string (e.g., "5.2 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def parse_size(size_str):
    """
    Parse formatted size string back to bytes for sorting.

    Args:
        size_str: Formatted size string (e.g., "5.2 MB")

    Returns:
        Size in bytes, or 0 if parsing fails
    """
    try:
        parts = size_str.split()
        if len(parts) != 2:
            return 0
        value = float(parts[0])
        unit = parts[1]

        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        return value * multipliers.get(unit, 1)
    except:
        return 0


def get_file_metadata(file_path):
    """
    Get file size and formatted modification date.

    Args:
        file_path: Path to file

    Returns:
        Tuple of (size_bytes, date_string)
    """
    size = os.path.getsize(file_path)
    mod_time = os.path.getmtime(file_path)
    date_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")
    return size, date_str


def format_operation_results(counts, errors=None, max_errors=10):
    """
    Format operation results into a display message.

    Args:
        counts: Dict like {'Compressed': 5, 'Failed': 2}
        errors: List of error strings
        max_errors: Maximum number of errors to display

    Returns:
        Formatted message string
    """
    lines = [f"{k}: {v}" for k, v in counts.items() if v > 0 or k in ('Success', 'Failed')]
    msg = "\n".join(lines)
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors[:max_errors])
        if len(errors) > max_errors:
            msg += f"\n... and {len(errors) - max_errors} more"
    return msg
