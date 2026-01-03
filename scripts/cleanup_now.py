#!/usr/bin/env python3
"""
Custom cleanup - Delete unwanted files but keep chrome_session and build folders
"""

import os
import shutil
from pathlib import Path

# Project root
project_root = Path(__file__).parent

print("🧹 MANAK Automation - Custom Cleanup")
print("="*60)
print("Will DELETE:")
print("  ✅ Backup files")
print("  ✅ Test files")
print("  ✅ Variant files (_new, _clean)")
print("  ✅ Python cache (__pycache__)")
print("  ✅ All log files")
print("  ✅ Cache files (.json, .db)")
print("\nWill KEEP:")
print("  ⚠️ chrome_session/ folder")
print("  ⚠️ build/ folder")
print("  ⚠️ dist/ folder")
print("="*60)

total_size = 0
deleted_count = 0

def get_size(path):
    """Get file size in bytes"""
    try:
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    except:
        return 0

def format_size(size_bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def delete_item(path, item_type="file"):
    """Delete file or directory"""
    global total_size, deleted_count
    try:
        size = get_size(path)
        
        if path.is_file():
            path.unlink()
            print(f"  ✅ Deleted file: {path.name} ({format_size(size)})")
        elif path.is_dir():
            shutil.rmtree(path)
            print(f"  ✅ Deleted folder: {path.name}/ ({format_size(size)})")
        
        total_size += size
        deleted_count += 1
        return True
    except Exception as e:
        print(f"  ❌ Error deleting {path.name}: {e}")
        return False

# 1. Delete backup files
print("\n📦 Deleting backup files...")
for backup_file in project_root.glob("*_backup*.py"):
    delete_item(backup_file)

# 2. Delete test files
print("\n🧪 Deleting test files...")
for test_file in project_root.glob("test_*.py"):
    delete_item(test_file)

# 3. Delete variant files
print("\n🔄 Deleting variant files...")
for variant_file in list(project_root.glob("*_new.py")) + list(project_root.glob("*_clean.py")):
    delete_item(variant_file)

# 4. Delete __pycache__
print("\n🗂️ Deleting Python cache...")
pycache_dir = project_root / "__pycache__"
if pycache_dir.exists():
    delete_item(pycache_dir)

# 5. Delete all logs
print("\n📝 Deleting all log files...")
logs_dir = project_root / "logs"
if logs_dir.exists():
    for log_file in logs_dir.glob("*.log"):
        delete_item(log_file)

# 6. Delete cache files
print("\n💾 Deleting cache files...")
cache_files = [
    "license_cache.json",
    "trial_info.json", 
    "job_data.db",
    "weight_data___20250725_141552.json",
    "weights.xlsx"
]

for cache_file in cache_files:
    filepath = project_root / cache_file
    if filepath.exists():
        delete_item(filepath)

# 7. Delete old data files
print("\n📄 Deleting old data files...")
old_json_files = project_root.glob("weight_data___*.json")
for old_file in old_json_files:
    delete_item(old_file)

# Summary
print("\n" + "="*60)
print("🎉 CLEANUP COMPLETE!")
print("="*60)
print(f"Files/folders deleted: {deleted_count}")
print(f"Total space saved: {format_size(total_size)}")
print("="*60)
print("\n✅ Kept: chrome_session/ folder")
print("✅ Kept: build/ folder")
print("✅ Kept: dist/ folder")
print("\n💡 Your project is now cleaner!")
