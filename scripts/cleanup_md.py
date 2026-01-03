#!/usr/bin/env python3
"""
Delete unnecessary .md documentation files
Keep only essential documentation
"""

import os
from pathlib import Path

# Project root
project_root = Path(__file__).parent

print("📝 Deleting Unnecessary .md Files")
print("="*60)

# Files to KEEP
keep_files = {
    "README.md",
    "USER_GUIDE.md",
    "SETUP_GUIDE.md",
    "SECURITY.md",
    "MYSQL_AUTH_FIX.md"
}

# Files to DELETE
delete_files = [
    "CLEANUP_QUICK_GUIDE.md",
    "CLEANUP_REPORT.md",
    "CLEANUP_SUMMARY.md",
    "GOLD_PAGINATION_FIX.md",
    "PAGINATION_FIX_SUMMARY.md",
    "LOT_SELECTION_FIX.md",
    "LOT_SELECTION_FIXES.md",
    "MYSQL_BUILD_FIX.md",
    "LICENSE_FIXES_SUMMARY.md",
    "IMPLEMENTATION_SUMMARY.md",
    "IMPLEMENTATION_SUMMARY_SECURE_LICENSE.md",
    "SECURE_LICENSE_SYSTEM.md",
    "SECURITY_FIXES.md",
    "README_Windows7.md",
    "WEIGHT_ENTRY_INSTALLATION_GUIDE.md",
    "WEIGHT_ENTRY_PAGE_INSTALLATION.md",
    "MD_FILES_ANALYSIS.md",
    "DELIVERY_VOUCHER_FIX.md"
]

total_deleted = 0
total_size = 0

def format_size(size_bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} GB"

print("\n🗑️  Deleting unnecessary .md files...\n")

for md_file in delete_files:
    filepath = project_root / md_file
    if filepath.exists():
        try:
            size = filepath.stat().st_size
            filepath.unlink()
            print(f"  ✅ Deleted: {md_file} ({format_size(size)})")
            total_deleted += 1
            total_size += size
        except Exception as e:
            print(f"  ❌ Error deleting {md_file}: {e}")
    else:
        print(f"  ⚠️  Not found: {md_file}")

print("\n" + "="*60)
print("✅ KEEPING these essential files:")
print("="*60)
for keep_file in sorted(keep_files):
    filepath = project_root / keep_file
    if filepath.exists():
        size = filepath.stat().st_size
        print(f"  ✅ {keep_file} ({format_size(size)})")
    else:
        print(f"  ⚠️  {keep_file} (not found)")

print("\n" + "="*60)
print("🎉 CLEANUP COMPLETE!")
print("="*60)
print(f"Files deleted: {total_deleted}")
print(f"Space saved: {format_size(total_size)}")
print(f"Remaining .md files: {len(keep_files)}")
print("="*60)
print("\n💡 Your documentation is now clean and organized!")
