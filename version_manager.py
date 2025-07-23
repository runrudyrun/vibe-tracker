#!/usr/bin/env python3
"""
Vibe Tracker Version Manager CLI

A convenient command-line interface for managing semantic versioning
in the vibe-tracker project.

Usage:
    python version_manager.py                    # Show current version
    python version_manager.py show              # Show detailed version info
    python version_manager.py bump major        # Bump major version (breaking changes)
    python version_manager.py bump minor        # Bump minor version (new features)
    python version_manager.py bump patch        # Bump patch version (bug fixes)
    python version_manager.py set 1.2.3         # Set specific version
    python version_manager.py history           # Show git tag history (if available)
    python version_manager.py tag               # Create git tag for current version
"""

import sys
import os
import subprocess
from datetime import datetime

# Add src directory to path to import version module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from version import Version, VersionManager, get_version, get_version_info
except ImportError as e:
    print(f"Error importing version module: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def show_version_info():
    """Display detailed version information."""
    version = get_version()
    major, minor, patch = get_version_info()
    
    print(f"🎵 Vibe Tracker Version Manager")
    print(f"{'='*40}")
    print(f"Current Version: {version}")
    print(f"  Major: {major} (Breaking changes)")
    print(f"  Minor: {minor} (New features)")
    print(f"  Patch: {patch} (Bug fixes)")
    print()
    print("Semantic Versioning Guidelines:")
    print("  MAJOR: Incompatible API changes")
    print("  MINOR: Backward-compatible functionality")
    print("  PATCH: Backward-compatible bug fixes")


def bump_version(version_type: str):
    """Bump version and optionally create git tag."""
    vm = VersionManager()
    old_version = vm.get_current_version()
    
    if version_type == "major":
        new_version = vm.bump_major()
        change_type = "MAJOR (Breaking Changes)"
    elif version_type == "minor":
        new_version = vm.bump_minor()
        change_type = "MINOR (New Features)"
    elif version_type == "patch":
        new_version = vm.bump_patch()
        change_type = "PATCH (Bug Fixes)"
    else:
        print(f"Invalid version type: {version_type}")
        print("Use: major, minor, or patch")
        return False
    
    print(f"✅ Version bumped: {old_version} → {new_version}")
    print(f"   Change type: {change_type}")
    
    # Ask if user wants to create git tag
    if is_git_repo():
        response = input(f"\nCreate git tag 'v{new_version}'? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            create_git_tag(str(new_version))
    
    return True


def set_version(version_str: str):
    """Set specific version."""
    try:
        version = Version.from_string(version_str)
        vm = VersionManager()
        old_version = vm.get_current_version()
        vm.set_version(version)
        
        print(f"✅ Version set: {old_version} → {version}")
        
        # Ask if user wants to create git tag
        if is_git_repo():
            response = input(f"\nCreate git tag 'v{version}'? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                create_git_tag(str(version))
        
        return True
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False


def is_git_repo():
    """Check if current directory is a git repository."""
    try:
        subprocess.run(['git', 'rev-parse', '--git-dir'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_git_tag(version: str):
    """Create git tag for version."""
    try:
        tag_name = f"v{version}"
        message = f"Release version {version}"
        
        # Create annotated tag
        subprocess.run(['git', 'tag', '-a', tag_name, '-m', message], check=True)
        print(f"✅ Git tag '{tag_name}' created")
        
        # Ask if user wants to push tag
        response = input("Push tag to remote? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            subprocess.run(['git', 'push', 'origin', tag_name], check=True)
            print(f"✅ Tag '{tag_name}' pushed to remote")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating git tag: {e}")
    except FileNotFoundError:
        print("❌ Git not found. Make sure git is installed.")


def show_git_history():
    """Show git tag history."""
    if not is_git_repo():
        print("❌ Not a git repository")
        return
    
    try:
        result = subprocess.run(['git', 'tag', '-l', '--sort=-version:refname'], 
                              capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print("No git tags found")
            return
            
        print("🏷️  Git Tag History:")
        print("=" * 20)
        
        for tag in result.stdout.strip().split('\n'):
            if tag.startswith('v'):
                # Get tag date
                try:
                    date_result = subprocess.run(['git', 'log', '-1', '--format=%ai', tag], 
                                               capture_output=True, text=True, check=True)
                    date_str = date_result.stdout.strip()
                    if date_str:
                        date_obj = datetime.fromisoformat(date_str.replace(' ', 'T', 1))
                        formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                        print(f"  {tag:<12} ({formatted_date})")
                    else:
                        print(f"  {tag}")
                except:
                    print(f"  {tag}")
                    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting git history: {e}")


def show_help():
    """Show help information."""
    print(__doc__)


def main():
    """Main CLI interface."""
    if len(sys.argv) == 1:
        # No arguments - show current version
        print(f"Current version: {get_version()}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        show_version_info()
    
    elif command == "bump":
        if len(sys.argv) != 3:
            print("Usage: python version_manager.py bump [major|minor|patch]")
            return
        bump_version(sys.argv[2].lower())
    
    elif command == "set":
        if len(sys.argv) != 3:
            print("Usage: python version_manager.py set VERSION")
            return
        set_version(sys.argv[2])
    
    elif command == "history":
        show_git_history()
    
    elif command == "tag":
        version = get_version()
        create_git_tag(version)
    
    elif command in ["help", "-h", "--help"]:
        show_help()
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python version_manager.py help' for usage information")


if __name__ == "__main__":
    main()
