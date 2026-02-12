"""
DAT file parser for ROM Librarian
Supports No-Intro, MAME/Arcade, and other XML-based DAT formats
"""

import xml.etree.ElementTree as ET
from core.logging_setup import logger


def parse_dat_file(dat_path):
    """
    Parse a DAT file (No-Intro or MAME XML format) and return a dictionary of game entries.
    Supports both <game> tags (No-Intro) and <machine> tags (MAME/Arcade).
    Returns: {crc32: game_name, md5: game_name, sha1: game_name}
    """
    logger.info(f"Parsing DAT file: {dat_path}")
    hash_to_name = {}

    try:
        tree = ET.parse(dat_path)
        root = tree.getroot()

        # Check for both <game> elements (No-Intro) and <machine> elements (MAME/Arcade)
        games = root.findall('game')
        machines = root.findall('machine')

        # Determine which format we're dealing with
        if games and machines:
            logger.info(f"DAT file contains both <game> ({len(games)}) and <machine> ({len(machines)}) tags - processing both")
            entries = games + machines
            entry_type = "mixed"
        elif games:
            logger.info(f"DAT file format: No-Intro (<game> tags)")
            entries = games
            entry_type = "game"
        elif machines:
            logger.info(f"DAT file format: MAME/Arcade (<machine> tags)")
            entries = machines
            entry_type = "machine"
        else:
            logger.warning("No <game> or <machine> elements found in DAT file")
            return hash_to_name

        # Process all entries (games or machines)
        for entry in entries:
            entry_name = entry.get('name', '')
            if not entry_name:
                continue

            # Get all <rom> entries for this game/machine
            for rom in entry.findall('rom'):
                # Get hash values
                crc = rom.get('crc', '').lower()
                md5 = rom.get('md5', '').lower()
                sha1 = rom.get('sha1', '').lower()

                # Store mappings for each available hash
                if crc:
                    hash_to_name[crc] = entry_name
                if md5:
                    hash_to_name[md5] = entry_name
                if sha1:
                    hash_to_name[sha1] = entry_name

        logger.info(f"DAT parse complete: {len(hash_to_name)} hash entries from {len(entries)} {entry_type} entries")
        return hash_to_name

    except Exception as e:
        logger.error(f"Failed to parse DAT file {dat_path}: {e}")
        raise Exception(f"Failed to parse DAT file: {str(e)}")
