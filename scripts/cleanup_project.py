#!/usr/bin/env python3
"""
MANAK Automation - Project Cleanup Script
Safely removes unwanted files to reduce project size
"""

import os
import shutil
from pathlib import Path
import argparse
from datetime import datetime, timedelta

class ProjectCleaner:
    def __init__(self, project_root, dry_run=True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.deleted_files = []
        self.deleted_dirs = []
        self.total_size_saved = 0
        
    def get_file_size(self, path):
        """Get file size in bytes"""
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        except Exception:
            return 0
    
    def format_size(self, size_bytes):
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def delete_file(self, filepath, reason=""):
        """Delete a single file"""
        try:
            size = self.get_file_size(filepath)
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete: {filepath.name} ({self.format_size(size)}) - {reason}")
            else:
                filepath.unlink()
                print(f"✅ Deleted: {filepath.name} ({self.format_size(size)}) - {reason}")
                self.deleted_files.append(str(filepath))
                self.total_size_saved += size
            
            return True
        except Exception as e:
            print(f"❌ Error deleting {filepath}: {e}")
            return False
    
    def delete_directory(self, dirpath, reason=""):
        """Delete an entire directory"""
        try:
            size = self.get_file_size(dirpath)
            
            if self.dry_run:
                print(f"[DRY RUN] Would delete directory: {dirpath.name}/ ({self.format_size(size)}) - {reason}")
            else:
                shutil.rmtree(dirpath)
                print(f"✅ Deleted directory: {dirpath.name}/ ({self.format_size(size)}) - {reason}")
                self.deleted_dirs.append(str(dirpath))
                self.total_size_saved += size
            
            return True
        except Exception as e:
            print(f"❌ Error deleting directory {dirpath}: {e}")
            return False
    
    def clean_backup_files(self):
        """Remove backup files"""
        print("\n📦 Cleaning backup files...")
        backup_patterns = ['*_backup*.py', '*_old*.py']
        
        for pattern in backup_patterns:
            for filepath in self.project_root.glob(pattern):
                if filepath.is_file():
                    self.delete_file(filepath, "Backup file")
    
    def clean_test_files(self):
        """Remove test files"""
        print("\n🧪 Cleaning test files...")
        test_patterns = ['test_*.py']
        
        for pattern in test_patterns:
            for filepath in self.project_root.glob(pattern):
                if filepath.is_file():
                    self.delete_file(filepath, "Test file")
    
    def clean_variant_files(self):
        """Remove variant files (new, clean)"""
        print("\n🔄 Cleaning variant files...")
        variant_patterns = ['*_new.py', '*_clean.py']
        
        for pattern in variant_patterns:
            for filepath in self.project_root.glob(pattern):
                if filepath.is_file():
                    self.delete_file(filepath, "Variant file")
    
    def clean_pycache(self):
        """Remove __pycache__ directories"""
        print("\n🗂️ Cleaning Python cache...")
        for pycache_dir in self.project_root.rglob('__pycache__'):
            if pycache_dir.is_dir():
                self.delete_directory(pycache_dir, "Python cache")
    
    def clean_build_artifacts(self):
        """Remove build directories"""
        print("\n🏗️ Cleaning build artifacts...")
        
        build_dir = self.project_root / 'build'
        if build_dir.exists() and build_dir.is_dir():
            self.delete_directory(build_dir, "Build artifacts")
    
    def clean_old_logs(self, days=30):
        """Remove log files older than specified days"""
        print(f"\n📝 Cleaning logs older than {days} days...")
        
        logs_dir = self.project_root / 'logs'
        if not logs_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for log_file in logs_dir.glob('*.log'):
            try:
                modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if modified_time < cutoff_date:
                    self.delete_file(log_file, f"Log older than {days} days")
            except Exception as e:
                print(f"⚠️ Could not check {log_file.name}: {e}")
    
    def clean_cache_files(self):
        """Remove cache and temporary files"""
        print("\n💾 Cleaning cache files...")
        
        cache_files = [
            'license_cache.json',
            'trial_info.json',
            'job_data.db'
        ]
        
        for cache_file in cache_files:
            filepath = self.project_root / cache_file
            if filepath.exists() and filepath.is_file():
                self.delete_file(filepath, "Cache file")
    
    def clean_chrome_session(self):
        """Remove Chrome session data"""
        print("\n🌐 Cleaning Chrome session data...")
        print("   ⚠️ WARNING: This will log you out of MANAK portal!")
        
        chrome_dir = self.project_root / 'chrome_session'
        if chrome_dir.exists() and chrome_dir.is_dir():
            self.delete_directory(chrome_dir, "Chrome session/cache")
    
    def print_summary(self):
        """Print cleanup summary"""
        print("\n" + "="*60)
        print("🎉 CLEANUP SUMMARY")
        print("="*60)
        print(f"Mode: {'DRY RUN (no files deleted)' if self.dry_run else 'LIVE (files deleted)'}")
        print(f"Files {'would be' if self.dry_run else ''} deleted: {len(self.deleted_files)}")
        print(f"Directories {'would be' if self.dry_run else ''} deleted: {len(self.deleted_dirs)}")
        print(f"Total space {'would be' if self.dry_run else ''} saved: {self.format_size(self.total_size_saved)}")
        print("="*60)
        
        if self.dry_run:
            print("\n💡 To actually delete files, run with --execute flag")
    
    def run_conservative_cleanup(self):
        """Run conservative cleanup (safest)"""
        print("\n🟢 CONSERVATIVE CLEANUP - Safest option")
        print("Deleting: backups, test files, Python cache\n")
        
        self.clean_backup_files()
        self.clean_test_files()
        self.clean_pycache()
        
        self.print_summary()
    
    def run_moderate_cleanup(self):
        """Run moderate cleanup (recommended)"""
        print("\n🟡 MODERATE CLEANUP - Recommended option")
        print("Deleting: backups, tests, cache, build artifacts, old logs\n")
        
        self.clean_backup_files()
        self.clean_test_files()
        self.clean_variant_files()
        self.clean_pycache()
        self.clean_build_artifacts()
        self.clean_old_logs(days=30)
        self.clean_cache_files()
        
        self.print_summary()
    
    def run_aggressive_cleanup(self):
        """Run aggressive cleanup (maximum space)"""
        print("\n🔴 AGGRESSIVE CLEANUP - Maximum space recovery")
        print("Deleting: All moderate items + Chrome session data\n")
        
        self.clean_backup_files()
        self.clean_test_files()
        self.clean_variant_files()
        self.clean_pycache()
        self.clean_build_artifacts()
        self.clean_old_logs(days=7)  # Keep only last week
        self.clean_cache_files()
        self.clean_chrome_session()
        
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description='MANAK Automation Project Cleanup Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview) - Conservative cleanup
  python cleanup_project.py --mode conservative
  
  # Actually delete files - Conservative cleanup
  python cleanup_project.py --mode conservative --execute
  
  # Dry run - Moderate cleanup (recommended)
  python cleanup_project.py --mode moderate
  
  # Actually delete files - Moderate cleanup
  python cleanup_project.py --mode moderate --execute
  
  # Dry run - Aggressive cleanup (max space)
  python cleanup_project.py --mode aggressive
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['conservative', 'moderate', 'aggressive'],
        default='conservative',
        help='Cleanup mode: conservative (safest), moderate (recommended), aggressive (max space)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete files (default is dry-run)'
    )
    
    parser.add_argument(
        '--project-root',
        type=str,
        default='.',
        help='Project root directory (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Confirm if executing
    if args.execute:
        print("\n⚠️  WARNING: You are about to DELETE files!")
        print(f"Mode: {args.mode.upper()}")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled.")
            return
    
    # Create cleaner instance
    project_root = Path(args.project_root).resolve()
    cleaner = ProjectCleaner(project_root, dry_run=not args.execute)
    
    # Run cleanup based on mode
    if args.mode == 'conservative':
        cleaner.run_conservative_cleanup()
    elif args.mode == 'moderate':
        cleaner.run_moderate_cleanup()
    elif args.mode == 'aggressive':
        cleaner.run_aggressive_cleanup()


if __name__ == '__main__':
    main()
