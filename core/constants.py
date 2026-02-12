"""
Constants and configuration for ROM Librarian
"""

import os

# App version
VERSION = "1.2.0"

# File paths
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian_config.json")
HASH_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian_hash_cache.json")
LOG_FILE = os.path.join(os.path.expanduser("~"), ".rom_librarian.log")
ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cartridge.ico")

# Windows API constants for sleep prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# ROM file filtering constants
ROM_EXTENSIONS_WHITELIST = {
    # Cartridge-based systems
    '.nds', '.gba', '.gbc', '.gb', '.sfc', '.smc', '.nes', '.n64', '.z64', '.v64',
    '.md', '.smd', '.gen', '.gg', '.sms', '.pce', '.ngp', '.ngc', '.ws', '.wsc',
    # Disc-based systems
    '.bin', '.iso', '.cue', '.chd', '.cso', '.gcm', '.rvz', '.wbfs', '.wad',
    # Modern systems
    '.dol', '.elf', '.nsp', '.xci', '.nca',
    # Archives
    '.zip', '.7z', '.rar', '.gz'
}

# Alias for backward compatibility
ROM_EXTENSIONS = ROM_EXTENSIONS_WHITELIST

# Archive extensions
ARCHIVE_EXTENSIONS = {'.zip', '.7z', '.rar', '.gz'}

FILE_EXTENSIONS_BLACKLIST = {
    # Images
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.ico',
    # Documents
    '.pdf', '.txt', '.doc', '.docx', '.rtf', '.md',
    # Executables
    '.exe', '.dll', '.bat', '.sh', '.msi',
    # Media
    '.mp4', '.avi', '.mkv', '.mp3', '.wav', '.flac',
    # Metadata
    '.xml', '.json', '.dat', '.ini', '.cfg',
    # Other
    '.db', '.tmp', '.log', '.bak'
}

EXCLUDED_FOLDER_NAMES = {
    'media', 'screenshots', 'manuals', 'boxart', 'box art', 'images',
    'saves', 'savedata', 'docs', 'documentation', 'videos'
}
