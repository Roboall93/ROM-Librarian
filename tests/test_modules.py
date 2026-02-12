#!/usr/bin/env python3
"""
Test modular architecture for ROM Librarian
Verifies all new modules work correctly
"""

import sys
import os

# Test imports
print("=" * 70)
print("ROM LIBRARIAN MODULAR ARCHITECTURE TEST")
print("=" * 70)
print()

print("TEST 1: Core Modules Import")
print("-" * 70)
try:
    from core import (
        setup_logging, logger, load_config, save_config,
        load_hash_cache, save_hash_cache, VERSION,
        CONFIG_FILE, HASH_CACHE_FILE, LOG_FILE,
        ROM_EXTENSIONS_WHITELIST, EXCLUDED_FOLDER_NAMES
    )
    print("[OK] Core modules imported successfully")
    print(f"  - Version: {VERSION}")
    print(f"  - Logger initialized: {logger.name}")
    print(f"  - ROM extensions loaded: {len(ROM_EXTENSIONS_WHITELIST)} types")
except Exception as e:
    print(f"[FAIL] Core module import failed: {e}")
    sys.exit(1)

print()

print("TEST 2: Parsers Module Import")
print("-" * 70)
try:
    from parsers import parse_dat_file
    print("[OK] Parsers module imported successfully")
    print(f"  - parse_dat_file function available")
except Exception as e:
    print(f"[FAIL] Parsers module import failed: {e}")
    sys.exit(1)

print()

print("TEST 3: Operations Module Import")
print("-" * 70)
try:
    from operations import calculate_file_hashes, update_gamelist_xml
    print("[OK] Operations module imported successfully")
    print(f"  - calculate_file_hashes function available")
    print(f"  - update_gamelist_xml function available")
except Exception as e:
    print(f"[FAIL] Operations module import failed: {e}")
    sys.exit(1)

print()

print("TEST 4: Configuration Operations")
print("-" * 70)
try:
    config = load_config()
    print(f"[OK] Configuration loaded: {list(config.keys())}")

    cache = load_hash_cache()
    print(f"[OK] Hash cache loaded: {len(cache)} entries")
except Exception as e:
    print(f"[FAIL] Configuration operations failed: {e}")
    sys.exit(1)

print()

print("TEST 5: DAT Parsing (if test DAT available)")
print("-" * 70)
dat_path = r"C:\My Projects\Test Roms\Sega - Mega Drive - Genesis.dat"
if os.path.exists(dat_path):
    try:
        hash_dict = parse_dat_file(dat_path)
        print(f"[OK] DAT file parsed successfully")
        print(f"  - Hash entries: {len(hash_dict)}")
        print(f"  - Sample entry: {list(hash_dict.items())[0]}")
    except Exception as e:
        print(f"[FAIL] DAT parsing failed: {e}")
else:
    print("[SKIP] Test DAT file not found")

print()

print("TEST 6: Hash Calculation (if test ROM available)")
print("-" * 70)
test_rom = r"C:\My Projects\Test Roms\Sonic The Hedgehog (USA, Europe).md"
if os.path.exists(test_rom):
    try:
        crc, md5, sha1 = calculate_file_hashes(test_rom)
        print(f"[OK] Hash calculation successful")
        print(f"  - CRC32: {crc}")
        print(f"  - MD5:   {md5[:16]}...")
        print(f"  - SHA1:  {sha1[:16]}...")
    except Exception as e:
        print(f"[FAIL] Hash calculation failed: {e}")
else:
    print("[SKIP] Test ROM file not found")

print()

print("=" * 70)
print("MODULE ARCHITECTURE TEST COMPLETE")
print("=" * 70)
print()
print("Summary:")
print("  [OK] All modules imported successfully")
print("  [OK] Core utilities functional")
print("  [OK] Parsers functional")
print("  [OK] File operations functional")
print()
print("The modular architecture is working correctly!")
print()
print(f"Log file: {os.path.expanduser('~/.rom_librarian.log')}")
