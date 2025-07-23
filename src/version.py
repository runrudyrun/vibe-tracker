"""
Version management for vibe-tracker using semantic versioning.

Semantic versioning follows the format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)
"""

import os
import re
from typing import Tuple, Optional


class Version:
    """Handles semantic versioning for vibe-tracker."""
    
    def __init__(self, major: int = 1, minor: int = 0, patch: int = 0):
        self.major = major
        self.minor = minor
        self.patch = patch
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __repr__(self) -> str:
        return f"Version({self.major}, {self.minor}, {self.patch})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other) -> bool:
        return self == other or self < other
    
    def __gt__(self, other) -> bool:
        return not self <= other
    
    def __ge__(self, other) -> bool:
        return not self < other
    
    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        """Parse version string in format 'MAJOR.MINOR.PATCH'."""
        pattern = r'^(\d+)\.(\d+)\.(\d+)$'
        match = re.match(pattern, version_str.strip())
        
        if not match:
            raise ValueError(f"Invalid version format: {version_str}. Expected format: MAJOR.MINOR.PATCH")
        
        major, minor, patch = map(int, match.groups())
        return cls(major, minor, patch)
    
    def bump_major(self) -> 'Version':
        """Increment major version and reset minor and patch to 0."""
        return Version(self.major + 1, 0, 0)
    
    def bump_minor(self) -> 'Version':
        """Increment minor version and reset patch to 0."""
        return Version(self.major, self.minor + 1, 0)
    
    def bump_patch(self) -> 'Version':
        """Increment patch version."""
        return Version(self.major, self.minor, self.patch + 1)


class VersionManager:
    """Manages version file and operations."""
    
    def __init__(self, version_file_path: Optional[str] = None):
        if version_file_path is None:
            # Default to VERSION file in project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            version_file_path = os.path.join(project_root, "VERSION")
        
        self.version_file_path = version_file_path
    
    def get_current_version(self) -> Version:
        """Read current version from VERSION file."""
        try:
            with open(self.version_file_path, 'r') as f:
                version_str = f.read().strip()
            return Version.from_string(version_str)
        except FileNotFoundError:
            # If VERSION file doesn't exist, start with 1.0.0
            return Version(1, 0, 0)
        except Exception as e:
            raise RuntimeError(f"Error reading version file: {e}")
    
    def set_version(self, version: Version) -> None:
        """Write version to VERSION file."""
        try:
            with open(self.version_file_path, 'w') as f:
                f.write(str(version))
        except Exception as e:
            raise RuntimeError(f"Error writing version file: {e}")
    
    def bump_major(self) -> Version:
        """Bump major version and save to file."""
        current = self.get_current_version()
        new_version = current.bump_major()
        self.set_version(new_version)
        return new_version
    
    def bump_minor(self) -> Version:
        """Bump minor version and save to file."""
        current = self.get_current_version()
        new_version = current.bump_minor()
        self.set_version(new_version)
        return new_version
    
    def bump_patch(self) -> Version:
        """Bump patch version and save to file."""
        current = self.get_current_version()
        new_version = current.bump_patch()
        self.set_version(new_version)
        return new_version


# Global version manager instance
version_manager = VersionManager()

# Convenience functions
def get_version() -> str:
    """Get current version as string."""
    return str(version_manager.get_current_version())

def get_version_info() -> Tuple[int, int, int]:
    """Get current version as tuple (major, minor, patch)."""
    version = version_manager.get_current_version()
    return (version.major, version.minor, version.patch)

def bump_major() -> str:
    """Bump major version and return new version string."""
    return str(version_manager.bump_major())

def bump_minor() -> str:
    """Bump minor version and return new version string."""
    return str(version_manager.bump_minor())

def bump_patch() -> str:
    """Bump patch version and return new version string."""
    return str(version_manager.bump_patch())


if __name__ == "__main__":
    # CLI interface for version management
    import sys
    
    if len(sys.argv) < 2:
        print(f"Current version: {get_version()}")
        print("Usage: python version.py [major|minor|patch|set VERSION]")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "major":
        new_version = bump_major()
        print(f"Bumped to version: {new_version}")
    elif command == "minor":
        new_version = bump_minor()
        print(f"Bumped to version: {new_version}")
    elif command == "patch":
        new_version = bump_patch()
        print(f"Bumped to version: {new_version}")
    elif command == "set" and len(sys.argv) == 3:
        try:
            version = Version.from_string(sys.argv[2])
            version_manager.set_version(version)
            print(f"Set version to: {version}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Invalid command. Use: major, minor, patch, or set VERSION")
        sys.exit(1)
