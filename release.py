#!/usr/bin/env python3
"""
Release script for grummage.
Updates version in pyproject.toml and creates a git tag.
"""

import sys
import re
import subprocess
from pathlib import Path

def update_version(version):
    """Update version in pyproject.toml and snap/snapcraft.yaml"""
    pyproject_path = Path("pyproject.toml")
    snapcraft_path = Path("snap/snapcraft.yaml")
    
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found")
        return False
    
    if not snapcraft_path.exists():
        print("Error: snap/snapcraft.yaml not found")
        return False
    
    # Update pyproject.toml
    content = pyproject_path.read_text()
    updated_content = re.sub(
        r'version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        content
    )
    
    if content == updated_content:
        print("Error: Version not found in pyproject.toml")
        return False
    
    pyproject_path.write_text(updated_content)
    print(f"Updated version to {version} in pyproject.toml")
    
    # Update snap/snapcraft.yaml
    snap_content = snapcraft_path.read_text()
    updated_snap_content = re.sub(
        r"version:\s*'[^']*'",
        f"version: '{version}'",
        snap_content
    )
    
    if snap_content == updated_snap_content:
        print("Error: Version not found in snap/snapcraft.yaml")
        return False
    
    snapcraft_path.write_text(updated_snap_content)
    print(f"Updated version to {version} in snap/snapcraft.yaml")
    
    return True

def create_tag(version):
    """Create and push git tag"""
    try:
        # Add changed files
        subprocess.run(["git", "add", "pyproject.toml", "snap/snapcraft.yaml"], check=True)
        subprocess.run(["git", "commit", "-m", f"Bump version to {version}"], check=True)
        
        # Create tag
        tag_name = f"v{version}"
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {version}"], check=True)
        
        print(f"Created tag {tag_name}")
        print("To push the tag, run:")
        print(f"  git push origin {tag_name}")
        print("This will trigger the GitHub Action to build and release to PyPI")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating tag: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python release.py <version>")
        print("Example: python release.py 1.0.1")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Validate version format (simple check)
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        print("Error: Version must be in format X.Y.Z (e.g., 1.0.1)")
        sys.exit(1)
    
    print(f"Preparing release {version}...")
    
    if not update_version(version):
        sys.exit(1)
    
    if not create_tag(version):
        sys.exit(1)
    
    print(f"Release {version} prepared successfully!")

if __name__ == "__main__":
    main()