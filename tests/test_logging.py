#!/usr/bin/env python3
"""
Test script to demonstrate ROM Librarian logging functionality
"""

import sys
sys.path.insert(0, r'C:\My Projects\ROM Librarian')

from rom_manager import parse_dat_file, calculate_file_hashes, logger
import os

# Test 1: Parse DAT file
print("=" * 60)
print("TEST 1: Parsing DAT File")
print("=" * 60)

dat_path = r"C:\My Projects\Test Roms\Sega - Mega Drive - Genesis.dat"
try:
    hash_dict = parse_dat_file(dat_path)
    print(f"[OK] Successfully parsed DAT file")
    print(f"  Entries in hash dictionary: {len(hash_dict)}")
    # Show a few examples
    print(f"  Sample entries:")
    for i, (hash_val, name) in enumerate(list(hash_dict.items())[:3]):
        print(f"    {hash_val[:16]}... → {name}")
except Exception as e:
    print(f"[FAIL] Failed to parse DAT: {e}")

print()

# Test 2: Calculate hashes for a test ROM
print("=" * 60)
print("TEST 2: Calculating ROM Hashes")
print("=" * 60)

test_rom = r"C:\My Projects\Test Roms\Sonic The Hedgehog (USA, Europe).md"
if os.path.exists(test_rom):
    try:
        crc, md5, sha1 = calculate_file_hashes(test_rom)
        print(f"[OK] Successfully calculated hashes for: {os.path.basename(test_rom)}")
        print(f"  CRC32: {crc}")
        print(f"  MD5:   {md5}")
        print(f"  SHA1:  {sha1}")

        # Check if this ROM is in the DAT
        if crc in hash_dict:
            print(f"  [OK] ROM found in DAT as: {hash_dict[crc]}")
        else:
            print(f"  [FAIL] ROM not found in DAT")
    except Exception as e:
        print(f"[FAIL] Failed to calculate hashes: {e}")
else:
    print(f"[FAIL] Test ROM not found: {test_rom}")

print()
print("=" * 60)
print("Check the log file for detailed logging:")
print(f"  {os.path.expanduser('~/.rom_librarian.log')}")
print("=" * 60)
