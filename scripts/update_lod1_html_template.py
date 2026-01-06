#!/usr/bin/env python3
"""
Update the index_lod1_static.html template with newly dumped mesh data.

This script reads binary mesh data files and embeds them as base64 in the HTML template.

Usage:
    python scripts/update_lod1_html_template.py
"""

import base64
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DUMP_DIR = PROJECT_ROOT / "scripts" / "gradio" / "static" / "assets" / "dump_mhr"
TEMPLATE_PATH = PROJECT_ROOT / "scripts" / "gradio" / "templates" / "index_lod1_static.html"


def main():
    # Files to embed
    files = {
        'v_template': 'v_template.bin',
        'faces': 'faces.bin',
        'skinWeights': 'skinWeights.bin',
        'skinIndice': 'skinIndice.bin',
        'j_template': 'j_template.bin',
        'uvs': 'uvs.bin',
        'kintree': 'kintree.bin',
    }

    # Read and encode each file
    encoded = {}
    for key, filename in files.items():
        filepath = DUMP_DIR / filename
        if not filepath.exists():
            print(f"Warning: {filepath} not found")
            continue
        with open(filepath, 'rb') as f:
            data = f.read()
        encoded[key] = base64.b64encode(data).decode('ascii')
        print(f"  {key}: {len(data)} bytes -> {len(encoded[key])} base64 chars")

    # Build the new EMBEDDED_LOD1_DATA block
    js_lines = ['    const EMBEDDED_LOD1_DATA = {']
    for key in files:
        if key in encoded:
            js_lines.append(f'        {key}: "{encoded[key]}",')
    js_lines.append('    };')
    new_data_block = '\n'.join(js_lines)

    # Read the template
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Find and replace the EMBEDDED_LOD1_DATA block
    # Pattern matches from "const EMBEDDED_LOD1_DATA = {" to the closing "};"
    pattern = r'const EMBEDDED_LOD1_DATA = \{[^}]+(?:\{[^}]*\})*[^}]*\};'

    if not re.search(pattern, template_content):
        print("ERROR: Could not find EMBEDDED_LOD1_DATA block in template")
        return 1

    # Replace the block
    new_content = re.sub(pattern, new_data_block.strip(), template_content, count=1)

    # Write back
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\nUpdated {TEMPLATE_PATH}")
    print(f"Template size: {len(new_content)} bytes")

    return 0


if __name__ == "__main__":
    exit(main())
