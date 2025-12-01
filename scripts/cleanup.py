#!/usr/bin/env python3
"""
Project Cleanup Script
Removes temporary files, cache, and build artifacts from the project
"""

import os
import shutil
from pathlib import Path

# Patterns to remove
PATTERNS_TO_REMOVE = [
    '**/__pycache__',
    '**/*.pyc',
    '**/.pytest_cache',
    '**/.coverage',
    'frontend/build',
    'frontend/.env.local',
    'frontend/.env.development.local',
    'backend/.env',
]

# Directories to skip
SKIP_DIRS = {
    'node_modules',  # Keep node_modules, just remove cache files
    '.git',
    '.venv',
    'acc-dataset',
}

PROJECT_ROOT = Path(__file__).parent.parent

def clean_project():
    """Remove temporary and cache files from the project"""
    
    print("🧹 Starting project cleanup...")
    
    removed_count = 0
    
    for pattern in PATTERNS_TO_REMOVE:
        for item in PROJECT_ROOT.glob(pattern):
            if any(skip in item.parts for skip in SKIP_DIRS):
                continue
                
            try:
                if item.is_dir():
                    print(f"  Removing directory: {item.relative_to(PROJECT_ROOT)}")
                    shutil.rmtree(item)
                    removed_count += 1
                else:
                    print(f"  Removing file: {item.relative_to(PROJECT_ROOT)}")
                    item.unlink()
                    removed_count += 1
            except Exception as e:
                print(f"  ⚠️  Error removing {item}: {e}")
    
    print(f"\n✅ Cleanup complete! Removed {removed_count} items.")
    print("\n📊 Project Status:")
    print(f"  ✓ Cache files cleaned")
    print(f"  ✓ Build artifacts removed")
    print(f"  ✓ Python bytecode removed")
    print(f"  ✓ Test cache removed")
    print(f"\nProject is ready for development!")

if __name__ == '__main__':
    clean_project()
