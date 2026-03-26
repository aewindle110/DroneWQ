#!/usr/bin/env python3
"""
Post-process Sphinx documentation after apidoc generation.

This script:
1. Removes micasense references from RST files
2. Removes empty 'Module contents' sections
3. Copies processed files to docs/source/api/ for building
"""

import re
import shutil
from pathlib import Path

PRIMARY_DEMO_FILEPATH = Path(__file__).parent.parent / "examples" / "primary_demo.ipynb"


FILES_TO_SKIP_DELETE = [
    "index.rst",
    "intro.rst",
]


def copy_demo_nb(source_path, dest_dir):
    """Copy the primary demo notebook to the docs/source/api/ directory."""
    print(f"Copying {source_path} to {dest_dir}")
    dest = dest_dir / "primary_demo.ipynb"
    shutil.copy2(source_path, dest)


def remove_micasense_from_rst(content):
    """Remove micasense references from RST content."""
    # Remove micasense entries from toctree
    content = re.sub(r"\s+dronewq\.micasense\s*\n", "\n", content)
    return content


def remove_module_contents(content):
    """Remove empty Module contents sections."""
    # Match Module contents section with automodule that has no actual content
    pattern = r"Module contents\s*\n[-=]+\s*\n+\s*\.\. automodule::[^\n]+\s*:members:\s*:undoc-members:\s*:show-inheritance:\s*\n*"
    content = re.sub(pattern, "", content, flags=re.DOTALL)
    return content


def process_rst_file(filepath):
    """Process a single RST file."""
    content = filepath.read_text()
    original = content

    # Apply transformations
    content = remove_micasense_from_rst(content)
    content = remove_module_contents(content)

    # Clean up multiple blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    if content != original:
        filepath.write_text(content)
        print(f"Processed: {filepath.name}")
        return True
    return False


def main():
    """Main entry point."""
    docs_dir = Path(__file__).parent
    api_dir = docs_dir / "api"
    source_dir = docs_dir / "source"

    # Create source/api directory
    source_dir.mkdir(parents=True, exist_ok=True)

    # Clean old files in source/api
    if source_dir.exists():
        for f in source_dir.glob("*.rst"):
            if f.name in FILES_TO_SKIP_DELETE:
                continue
            f.unlink()

    # Process all RST files in api/
    processed = []
    if api_dir.exists():
        for rst_file in api_dir.glob("*.rst"):
            # Skip micasense files entirely
            if "micasense" in rst_file.name:
                print(f"Skipping micasense file: {rst_file.name}")
                continue

            # Process the file
            if process_rst_file(rst_file):
                processed.append(rst_file.name)

            # Copy to source/api/
            dest = source_dir / rst_file.name
            shutil.copy2(rst_file, dest)

    copy_demo_nb(PRIMARY_DEMO_FILEPATH, source_dir)

    print(f"\nProcessed {len(processed)} files")
    print(f"Files copied to: {source_dir}")

    # List files in source/api
    files = list(source_dir.glob("*.rst"))
    print(f"Files in source/api: {[f.name for f in files]}")


if __name__ == "__main__":
    main()
