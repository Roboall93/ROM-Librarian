"""
Gamelist.xml operations for ROM Librarian
Handles EmulationStation/RetroPie gamelist.xml updates
"""

import os
import shutil
import xml.etree.ElementTree as ET
from core.logging_setup import logger


def update_gamelist_xml(folder_path, rename_map):
    """
    Update gamelist.xml file with renamed paths.
    rename_map is a dict of {old_path: new_path}
    Only updates <path> tags, leaves everything else (images, metadata) unchanged.
    """
    gamelist_path = os.path.join(folder_path, "gamelist.xml")

    if not os.path.exists(gamelist_path):
        logger.debug(f"No gamelist.xml found at {gamelist_path}")
        return 0  # No gamelist.xml found, nothing to update

    logger.info(f"Updating gamelist.xml at {gamelist_path} with {len(rename_map)} renames")
    try:
        # Parse the XML file
        tree = ET.parse(gamelist_path)
        root = tree.getroot()

        updates_made = 0

        # Find all <game> elements
        for game in root.findall('game'):
            path_element = game.find('path')
            if path_element is not None and path_element.text:
                current_path = path_element.text

                # Check if this path needs updating
                # Path in XML is relative like "./filename.zip"
                # We need to match just the filename part
                for old_path, new_path in rename_map.items():
                    old_filename = os.path.basename(old_path)
                    new_filename = os.path.basename(new_path)

                    # Check if the XML path ends with the old filename
                    if current_path.endswith(old_filename):
                        # Replace just the filename part, keeping the ./ prefix
                        new_xml_path = current_path.replace(old_filename, new_filename)
                        path_element.text = new_xml_path
                        updates_made += 1
                        break

        if updates_made > 0:
            # Backup the original file
            backup_path = gamelist_path + ".backup"
            shutil.copy2(gamelist_path, backup_path)
            logger.debug(f"Created backup at {backup_path}")

            # Write the updated XML
            tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
            logger.info(f"Updated {updates_made} entries in gamelist.xml")
        else:
            logger.debug("No updates needed for gamelist.xml")

        return updates_made

    except Exception as e:
        logger.error(f"Failed to update gamelist.xml at {gamelist_path}: {e}")
        raise Exception(f"Failed to update gamelist.xml: {str(e)}")
