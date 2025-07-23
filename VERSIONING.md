# Versioning Guide for Vibe Tracker

Vibe Tracker uses **Semantic Versioning** (SemVer) to manage releases and track changes.

## Version Format

Versions follow the format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes that are not backward compatible
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes that are backward compatible

## Current Version

The current version is stored in the `VERSION` file in the project root and can be accessed programmatically through the `src/version.py` module.

## Version Management

### In the Application

- Press `Ctrl+V` in the TUI to view current version information
- The version is displayed in the application title bar

### Command Line Interface

Use the `version_manager.py` utility for version management:

```bash
# Show current version
python version_manager.py

# Show detailed version information
python version_manager.py show

# Bump versions
python version_manager.py bump patch    # For bug fixes
python version_manager.py bump minor    # For new features
python version_manager.py bump major    # For breaking changes

# Set specific version
python version_manager.py set 1.2.3

# Git integration
python version_manager.py history       # Show git tag history
python version_manager.py tag          # Create git tag for current version
```

### Direct Module Usage

```python
from src.version import get_version, bump_patch, bump_minor, bump_major

# Get current version
current = get_version()  # Returns string like "1.0.0"

# Bump versions
new_patch = bump_patch()    # 1.0.0 → 1.0.1
new_minor = bump_minor()    # 1.0.1 → 1.1.0  
new_major = bump_major()    # 1.1.0 → 2.0.0
```

## When to Bump Versions

### PATCH (x.x.X)
- Bug fixes
- Performance improvements
- Documentation updates
- Code refactoring without API changes

### MINOR (x.X.x)
- New features
- New instruments or effects
- New export formats
- Enhanced UI components
- Backward-compatible API additions

### MAJOR (X.x.x)
- Breaking API changes
- Incompatible file format changes
- Major architectural changes
- Removal of deprecated features

## Git Integration

The version manager can automatically create git tags:

1. When bumping or setting a version, you'll be prompted to create a git tag
2. Tags follow the format `vX.Y.Z` (e.g., `v1.0.0`)
3. You can optionally push tags to remote repository

## Best Practices

1. **Always update version before releases**
2. **Use descriptive commit messages** when bumping versions
3. **Create git tags** for all releases
4. **Document changes** in commit messages or changelog
5. **Test thoroughly** before bumping major versions

## File Structure

```
vibe-tracker/
├── VERSION                 # Current version (e.g., "1.0.0")
├── version_manager.py      # CLI utility for version management
├── src/
│   └── version.py         # Version management module
└── VERSIONING.md          # This documentation
```

## Examples

### Release Workflow

```bash
# After implementing bug fixes
python version_manager.py bump patch
# Creates v1.0.1 and optionally tags in git

# After adding new features
python version_manager.py bump minor  
# Creates v1.1.0 and optionally tags in git

# After major changes
python version_manager.py bump major
# Creates v2.0.0 and optionally tags in git
```

### Development Workflow

1. Make changes to code
2. Test changes thoroughly
3. Determine appropriate version bump type
4. Run `python version_manager.py bump [type]`
5. Commit changes with version bump
6. Push to repository (including tags if created)

## Troubleshooting

### Version File Not Found
If you get errors about missing VERSION file, create it manually:
```bash
echo "1.0.0" > VERSION
```

### Git Tag Conflicts
If git tag creation fails due to existing tags:
```bash
# List existing tags
git tag -l

# Delete local tag if needed
git tag -d v1.0.0

# Delete remote tag if needed
git push origin --delete v1.0.0
```

### Import Errors
Make sure you're running commands from the project root directory where `src/` folder is located.
