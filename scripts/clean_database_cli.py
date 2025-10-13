#!/usr/bin/env python3
"""
Script to remove obsolete pony-flux and domain-specific code from database/cli.py
"""

import re

# Read the file
with open('src/statemachine_engine/database/cli.py', 'r') as f:
    content = f.read()

# Functions to remove (complete function definitions)
functions_to_remove = [
    'get_pony_flux_status_counts',
    'cmd_list_pony_flux_jobs',
    'cmd_pony_flux_details',
    'cmd_cleanup_pony',
    'cmd_update_pony_flux_status',
]

# Remove each function
for func_name in functions_to_remove:
    # Pattern: from "def func_name" to the next "def " or end of file
    pattern = rf'def {func_name}\([^)]*\):.*?(?=\ndef |$)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    print(f"Removed: {func_name}")

# Remove pony-flux specific code from cmd_status
# Remove the "Pony-Flux Jobs:" section
pony_flux_status_pattern = r'\n    print\(f"\\nPony-Flux Jobs:"\).*?print\(f"  Failed: \{pf_failed\}"\)\n'
content = re.sub(pony_flux_status_pattern, '', content, flags=re.DOTALL)
print("Removed: Pony-Flux section from cmd_status")

# Remove domain-specific sections from cmd_job_details
# Remove file checking code
file_check_pattern = r'    # Show pipeline results.*?(?=\ndef )'
content = re.sub(file_check_pattern, '\ndef ', content, flags=re.DOTALL)

# Clean up cmd_machine_status - remove legacy pony-flux counting
pony_machine_status_pattern = r'    # Pony flux jobs \(legacy\).*?print\(f"  Pony Flux \(legacy\):.*?"\)\n\s*\n'
content = re.sub(pony_machine_status_pattern, '\n', content, flags=re.DOTALL)
print("Removed: Legacy pony-flux from cmd_machine_status")

# Clean up cmd_machine_health - remove hardcoded directories
health_dirs_pattern = r"    # Check output directories.*?print\(f\"  \{dir_name\}/: Missing ❌\"\)\n\s*\n\s*print\(\)"
content = re.sub(health_dirs_pattern, '', content, flags=re.DOTALL)
print("Removed: Hardcoded output directories from cmd_machine_health")

# Remove argparse definitions for obsolete commands
parsers_to_remove = [
    ('list-pony-flux', r"    # List pony-flux jobs command\n    list_pf_parser.*?default=20, help='Limit number of results'\)\n\s*\n"),
    ('pony-flux-details', r"    # Pony-flux job details command\n    pf_details_parser.*?help='Pony-flux job ID to show details for'\)\n\s*\n"),
    ('cleanup-pony', r"    # Cleanup pony command\n    cleanup_pony_parser.*?help='Status of pony-flux jobs to clean up.*?'\)\n\s*\n"),
    ('update-pony-flux-status', r"    # Update pony-flux status command\n    update_pf_parser.*?help='New status for the job'\)\n"),
]

for parser_name, pattern in parsers_to_remove:
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    print(f"Removed parser: {parser_name}")

# Remove command handlers from main()
handlers_to_remove = [
    r"        elif args\.command == 'list-pony-flux':\n            cmd_list_pony_flux_jobs\(args\)\n",
    r"        elif args\.command == 'pony-flux-details':\n            cmd_pony_flux_details\(args\)\n",
    r"        elif args\.command == 'cleanup-pony':\n            cmd_cleanup_pony\(args\)\n",
    r"        elif args\.command == 'update-pony-flux-status':\n            return cmd_update_pony_flux_status\(args\)\n",
]

for handler_pattern in handlers_to_remove:
    content = re.sub(handler_pattern, '', content)

print("Removed command handlers from main()")

# Clean up machine_type = 'legacy' from cmd_add_job
content = content.replace(
    "    else:\n        machine_type = 'legacy'",
    "    else:\n        machine_type = args.type"
)
print("Removed: 'legacy' machine_type")

# Write the cleaned file
with open('src/statemachine_engine/database/cli.py', 'w') as f:
    f.write(content)

print("\n✅ Cleanup complete!")
print("Removed:")
print("  - get_pony_flux_status_counts()")
print("  - cmd_list_pony_flux_jobs()")
print("  - cmd_pony_flux_details()")
print("  - cmd_cleanup_pony()")
print("  - cmd_update_pony_flux_status()")
print("  - Pony-flux section from cmd_status()")
print("  - Legacy pony-flux from cmd_machine_status()")
print("  - Hardcoded directories from cmd_machine_health()")
print("  - All obsolete argparse command definitions")
print("  - 'legacy' machine_type")
