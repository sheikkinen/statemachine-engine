#!/usr/bin/env python3
"""FSM Generator CLI

Generates state machine diagrams from YAML configs in two formats:

LEGACY FORMAT (Markdown):
- Main flow with composite states, error flow, stop flow
- States/events tables, configuration summary
- Output: docs/fsm-diagrams/{machine_name}/{machine_name}_fsm.md

MODERN FORMAT (.mermaid files):
- main.mermaid: High-level composite boundaries
- {composite}.mermaid: Detailed internal views
- metadata.json: Relationships and navigation
- Output: docs/fsm-diagrams/{machine_name}/

ARGUMENTS:
    yaml_file           YAML config file path
    output_file         (Optional) Custom Markdown output path
    --output-dir        Modern format directory (default: docs/fsm-diagrams)
    --old-format-only   Generate only Markdown
    --new-format-only   Generate only .mermaid files

USAGE:
    python -m fsm_generator.cli config/machine.yaml
    ./fsm-generate config/machine.yaml --new-format-only

TECHNICAL:
- Handles direct execution via __package__ manipulation
- Auto-creates output directories
- Imports from diagrams: load_yaml, generate_markdown, generate_diagram_files
"""

import sys
import os
import argparse
from pathlib import Path

# Handle direct execution - add parent directory to path
if __name__ == '__main__' and __package__ is None:
    script_dir = Path(__file__).resolve().parent
    src_dir = script_dir.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    __package__ = 'fsm_generator'

# Import all functions from diagrams module (which contains the full original code)
from .diagrams import (
    load_yaml,
    generate_markdown,
    generate_diagram_files
)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate FSM diagrams from YAML configuration')
    parser.add_argument('yaml_file', help='Path to YAML configuration file')
    parser.add_argument('output_file', nargs='?', help='Output Markdown file (optional, for backward compatibility)')
    parser.add_argument('--output-dir', default='docs/fsm-diagrams', help='Output directory for new format (default: docs/fsm-diagrams)')
    parser.add_argument('--old-format-only', action='store_true', help='Generate only old Markdown format')
    parser.add_argument('--new-format-only', action='store_true', help='Generate only new .mermaid format')
    
    args = parser.parse_args()
    yaml_path = args.yaml_file
    
    # Load configuration
    config = load_yaml(yaml_path)
    
    # Generate old format (Markdown with embedded Mermaid)
    if not args.new_format_only:
        if args.output_file:
            output_path = args.output_file
        else:
            # Use machine_name from metadata, fallback to filename
            machine_name = config.get('metadata', {}).get('machine_name')
            if not machine_name:
                # Fallback to YAML filename
                machine_name = Path(yaml_path).stem
            # Place markdown within fsm-diagrams folder
            output_path = f"{args.output_dir}/{machine_name}/{machine_name}_fsm.md"
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and write Markdown
        markdown = generate_markdown(config, yaml_path)
        try:
            with open(output_path, 'w') as f:
                f.write(markdown)
            print(f"✅ Generated Markdown: {output_path}")
        except Exception as e:
            print(f"Error writing output file {output_path}: {e}")
            sys.exit(1)
    
    # Generate new format (separate .mermaid files + metadata.json)
    if not args.old_format_only:
        print(f"\n📁 Generating new format in {args.output_dir}/...")
        generate_diagram_files(config, yaml_path, args.output_dir)
        print("")


if __name__ == '__main__':
    main()
