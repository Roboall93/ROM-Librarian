"""
File operations for ROM Librarian
Handles hashing and basic file operations
"""

import os
import hashlib
import zlib
import zipfile
from core.logging_setup import logger
from core.constants import ROM_EXTENSIONS_WHITELIST


def calculate_file_hashes(file_path):
    """
    Calculate CRC32, MD5, and SHA1 hashes for a file.
    For zip files, hashes the first ROM file found inside.
    Returns: (crc32_hex, md5_hex, sha1_hex)
    """
    logger.debug(f"Calculating hashes for: {file_path}")
    crc32_hash = 0
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()

    try:
        # Check if this is a zip file
        if file_path.lower().endswith('.zip') and zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zipf:
                # Get list of files in the zip
                file_list = zipf.namelist()

                # Find the first ROM file (skip directories and non-ROM files)
                rom_file = None
                for fname in file_list:
                    if not fname.endswith('/'):  # Skip directories
                        # Check if it has a ROM extension
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in ROM_EXTENSIONS_WHITELIST:
                            rom_file = fname
                            break

                if not rom_file:
                    raise Exception(f"No ROM file found in zip: {file_path}")

                # Hash the ROM file contents
                with zipf.open(rom_file) as f:
                    while True:
                        chunk = f.read(1024 * 1024)  # Read 1MB at a time
                        if not chunk:
                            break
                        crc32_hash = zlib.crc32(chunk, crc32_hash)
                        md5_hash.update(chunk)
                        sha1_hash.update(chunk)
        else:
            # Regular file - hash directly
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(1024 * 1024)  # Read 1MB at a time
                    if not chunk:
                        break
                    crc32_hash = zlib.crc32(chunk, crc32_hash)
                    md5_hash.update(chunk)
                    sha1_hash.update(chunk)

        # Format CRC32 as 8-character hex string
        crc32_hex = format(crc32_hash & 0xFFFFFFFF, '08x')
        md5_hex = md5_hash.hexdigest()
        sha1_hex = sha1_hash.hexdigest()

        logger.debug(f"Hash calculation complete for {os.path.basename(file_path)}: CRC32={crc32_hex}")
        return (crc32_hex, md5_hex, sha1_hex)

    except Exception as e:
        logger.error(f"Failed to hash file {file_path}: {e}")
        raise Exception(f"Failed to hash file {file_path}: {str(e)}")
