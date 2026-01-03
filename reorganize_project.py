#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANAK Automation - Folder Structure Reorganization Script
Reorganizes project into a professional folder structure
"""

import os
import shutil
from pathlib import Path
import sys

# Set utf-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class ProjectReorganizer:
    def __init__(self, project_root, dry_run=True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.moved_files = []
        
    def create_folders(self):
        """Create new folder structure"""
        folders = [
            'src',
            'src/processors',
            'src/license',
            'scripts',
            'drivers',
            'resources',
            'database',
            'docs'
        ]
        
        print("\nCreating folder structure...")
        for folder in folders:
            folder_path = self.project_root / folder
            if self.dry_run:
                print(f"  [DRY RUN] Would create: {folder}/")
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"  Created: {folder}/")
    
    def get_file_mapping(self):
        """Define where each file should go"""
        return {
            # Processors
            'job_cards_processor.py': 'src/processors/',
            'weight_capture_processor.py': 'src/processors/',
            'delivery_voucher_processor.py': 'src/processors/',
            'multiple_jobs_processor.py': 'src/processors/',
            'bulk_jobs_report_submit.py': 'src/processors/',
            'huid_data_processor.py': 'src/processors/',
            'request_generator.py': 'src/processors/',
            
            # License
            'device_license.py': 'src/license/',
            'license_methods.py': 'src/license/',
            
            # Main app
            'manak_desktop_app.py': 'src/',
            'desktop_manak_app.py': 'src/',
            'config.py': 'src/',
            
            # Scripts
            'build_exe.py': 'scripts/',
            'build_win7.py': 'scripts/',
            'rebuild_exe.py': 'scripts/',
            'cleanup_project.py': 'scripts/',
            'cleanup_now.py': 'scripts/',
            'cleanup_md.py': 'scripts/',
            'quick_setup.bat': 'scripts/',
            'distribute.bat': 'scripts/',
            'run_desktop_app.py': 'scripts/',
            'start_app.py': 'scripts/',
            'run_manak_automation.bat': 'scripts/',
            'start_manak.bat': 'scripts/',
            
            # Driver
            'chromedriver.exe': 'drivers/',
            
            # Resources
            'admin_panel.html': 'resources/',
            'weight_entry_modal_addon.html': 'resources/',
            'version_info.txt': 'resources/',
            
            # Database
            'device_license_api.php': 'database/',
            'submit_huid_data_api.php': 'database/',
            'device_licenses.sql': 'database/',
            
            # Documentation
            'README.md': 'docs/',
            'USER_GUIDE.md': 'docs/',
            'SETUP_GUIDE.md': 'docs/',
            'SECURITY.md': 'docs/',
            'MYSQL_AUTH_FIX.md': 'docs/',
            'FOLDER_STRUCTURE_ANALYSIS.md': 'docs/',
            
            # PyInstaller hooks
            'hook-mysql.connector.py': 'scripts/',
        }
    
    def move_files(self):
        """Move files to their new locations"""
        print("\nMoving files...")
        
        file_mapping = self.get_file_mapping()
        
        for filename, destination in file_mapping.items():
            source = self.project_root / filename
            dest_dir = self.project_root / destination
            dest_file = dest_dir / filename
            
            if source.exists():
                if self.dry_run:
                    print(f"  [DRY RUN] {filename} -> {destination}")
                else:
                    try:
                        shutil.move(str(source), str(dest_file))
                        print(f"  Moved: {filename} -> {destination}")
                        self.moved_files.append((filename, destination))
                    except Exception as e:
                        print(f"  Error moving {filename}: {e}")
    
    def create_init_files(self):
        """Create __init__.py files"""
        print("\nCreating __init__.py files...")
        
        init_locations = [
            'src/__init__.py',
            'src/processors/__init__.py',
            'src/license/__init__.py'
        ]
        
        for init_file in init_locations:
            init_path = self.project_root / init_file
            if self.dry_run:
                print(f"  [DRY RUN] Would create: {init_file}")
            else:
                if not init_path.exists():
                    init_path.write_text('"""MANAK Automation Module"""\n', encoding='utf-8')
                    print(f"  Created: {init_file}")
    
    def create_main_entry_point(self):
        """Create main.py in src/"""
        print("\nCreating main entry point...")
        
        main_content = '''#!/usr/bin/env python3
"""Main Entry Point"""
from manak_desktop_app import main
if __name__ == '__main__':
    main()
'''
        
        main_path = self.project_root / 'src' / 'main.py'
        if self.dry_run:
            print(f"  [DRY RUN] Would create: src/main.py")
        else:
            main_path.write_text(main_content, encoding='utf-8')
            print(f"  Created: src/main.py")
    
    def create_root_run_script(self):
        """Create run.py in root"""
        print("\nCreating root run script...")
        
        run_content = '''#!/usr/bin/env python3
"""MANAK Automation - Quick Start"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from manak_desktop_app import main
if __name__ == '__main__':
    print("Starting MANAK Automation...")
    main()
'''
        
        run_path = self.project_root / 'run.py'
        if self.dry_run:
            print(f"  [DRY RUN] Would create: run.py")
        else:
            run_path.write_text(run_content, encoding='utf-8')
            print(f"  Created: run.py")
    
    def print_summary(self):
        """Print summary"""
        print("\n" + "="*60)
        print("REORGANIZATION SUMMARY")
        print("="*60)
        if self.dry_run:
            print("MODE: DRY RUN")
        else:
            print("MODE: EXECUTED")
            print(f"Files moved: {len(self.moved_files)}")
            print("\nNext steps:")
            print("  1. Run: python run.py")
            print("  2. Test application")
        print("="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Reorganize project')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    
    if args.execute:
        print("\nWARNING: This will reorganize your project!")
        response = input("Type 'YES' to continue: ")
        if response != 'YES':
            print("Cancelled.")
            return
    
    reorganizer = ProjectReorganizer('.', dry_run=not args.execute)
    
    print("="*60)
    print("PROJECT REORGANIZATION")
    print("="*60)
    
    reorganizer.create_folders()
    reorganizer.move_files()
    reorganizer.create_init_files()
    reorganizer.create_main_entry_point()
    reorganizer.create_root_run_script()
    reorganizer.print_summary()


if __name__ == '__main__':
    main()
