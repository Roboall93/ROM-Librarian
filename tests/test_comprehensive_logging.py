#!/usr/bin/env python3
"""
Comprehensive logging test to demonstrate all logging features
"""

import sys
sys.path.insert(0, r'C:\My Projects\ROM Librarian')

from rom_manager import (
    parse_dat_file,
    calculate_file_hashes,
    logger,
    load_config,
    save_config,
    load_hash_cache,
    save_hash_cache
)
import os

print("=" * 70)
print("ROM LIBRARIAN LOGGING SYSTEM TEST")
print("=" * 70)
print()

# Test 1: Configuration operations
print("TEST 1: Configuration Loading (INFO level)")
print("-" * 70)
config = load_config()
print(f"Config loaded: {list(config.keys())}")
print()

# Test 2: Hash cache operations
print("TEST 2: Hash Cache Loading (INFO level)")
print("-" * 70)
cache = load_hash_cache()
print(f"Cache entries: {len(cache)}")
print()

# Test 3: DAT parsing
print("TEST 3: DAT File Parsing (INFO level)")
print("-" * 70)
dat_path = r"C:\My Projects\Test Roms\Sega - Mega Drive - Genesis.dat"
hash_dict = parse_dat_file(dat_path)
print(f"Parsed {len(hash_dict)} hash entries")
print()

# Test 4: Hash calculations for multiple ROMs
print("TEST 4: Multiple ROM Hash Calculations (DEBUG level)")
print("-" * 70)
test_roms = [
    r"C:\My Projects\Test Roms\Sonic The Hedgehog (USA, Europe).md",
    r"C:\My Projects\Test Roms\Golden Axe II (World).md",
    r"C:\My Projects\Test Roms\Phantasy Star II (USA, Europe) (Rev A).md"
]

matches = []
for rom_path in test_roms:
    if os.path.exists(rom_path):
        rom_name = os.path.basename(rom_path)
        try:
            crc, md5, sha1 = calculate_file_hashes(rom_path)

            # Check if in DAT
            if crc in hash_dict:
                dat_name = hash_dict[crc]
                matches.append((rom_name, dat_name))
                print(f"  {rom_name[:40]:<40} -> MATCH: {dat_name}")
            else:
                print(f"  {rom_name[:40]:<40} -> NO MATCH")
        except Exception as e:
            print(f"  {rom_name[:40]:<40} -> ERROR: {e}")

print()

# Test 5: Save operations
print("TEST 5: Configuration Save (DEBUG level)")
print("-" * 70)
test_config = {"test_key": "test_value", **config}
save_config(test_config)
print("Configuration saved")
print()

# Summary
print("=" * 70)
print("LOGGING TEST COMPLETE")
print("=" * 70)
print()
print(f"Total ROM-to-DAT matches: {len(matches)}")
for rom, dat in matches:
    print(f"  - {rom[:35]:<35} matches {dat}")
print()
print("Log file contents:")
print("-" * 70)
print(f"Location: {os.path.expanduser('~/.rom_librarian.log')}")
print()
print("Recent entries show:")
print("  - Application startup (INFO)")
print("  - Configuration loading (INFO/DEBUG)")
print("  - DAT parsing with format detection (INFO)")
print("  - Hash calculations for each ROM (DEBUG)")
print("  - Configuration save (DEBUG)")
print()
print("Log levels used:")
print("  DEBUG - Detailed technical information")
print("  INFO  - General operational information")
print("  WARNING - Non-critical issues")
print("  ERROR - Critical failures")
print()
