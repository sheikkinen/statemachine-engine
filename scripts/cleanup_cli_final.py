#!/usr/bin/env python3
"""
Script to remove remaining domain-specific code from database/cli.py
Making it a true generic state machine database CLI
"""

import re

# Read the file
with open('src/statemachine_engine/database/cli.py', 'r') as f:
    content = f.read()

print("Starting comprehensive cleanup...")

# 1. Fix module docstring
content = content.replace(
    'Database CLI for face-changer pipeline',
    'Database CLI for state machine engine'
)
print("✓ Fixed module docstring")

# 2. Fix argparse description
content = content.replace(
    'parser = argparse.ArgumentParser(description="Database CLI for face-changer pipeline")',
    'parser = argparse.ArgumentParser(description="Database CLI for state machine engine")'
)
print("✓ Fixed argparse description")

# 3. Remove face processing job counts from cmd_status
status_removal = r'\n    print\(f"\\nFace Processing Jobs:"\).*?print\(f"  Failed: \{fp_failed\}"\)'
content = re.sub(status_removal, '', content, flags=re.DOTALL)
print("✓ Removed face processing counts from cmd_status")

# 4. Simplify cmd_list_jobs - remove domain-specific formatting
list_jobs_old = r'''    # Format for table display - adjust headers based on job type
    if args\.type == 'pony_flux':
        headers = \['ID', 'Type', 'Status', 'Created', 'Pony Prompt', 'Flux Prompt'\]
        rows = \[\]
        for job in jobs:
            created = job\['created_at'\]\[:19\] if job\['created_at'\] else ''
            pony_prompt = \(job\['pony_prompt'\]\[:25\] \+ '\.\.\.'\) if job\['pony_prompt'\] and len\(job\['pony_prompt'\]\) > 25 else job\['pony_prompt'\]
            flux_prompt = \(job\['flux_prompt'\]\[:25\] \+ '\.\.\.'\) if job\['flux_prompt'\] and len\(job\['flux_prompt'\]\) > 25 else job\['flux_prompt'\]
            rows\.append\(\[job\['job_id'\], job\['job_type'\], job\['status'\], created, pony_prompt, flux_prompt\]\)
    else:
        headers = \['ID', 'Type', 'Status', 'Created', 'Image', 'Prompt'\]
        rows = \[\]
        for job in jobs:
            created = job\['created_at'\]\[:19\] if job\['created_at'\] else ''
            data = job\.get\('data', \{\}\)
            input_image_path = data\.get\('input_image_path', ''\)
            image_path = Path\(input_image_path\)\.name if input_image_path else ''
            user_prompt = data\.get\('user_prompt', ''\)
            prompt = \(user_prompt\[:30\] \+ '\.\.\.'\) if user_prompt and len\(user_prompt\) > 30 else user_prompt
            rows\.append\(\[job\['job_id'\], job\['job_type'\], job\['status'\], created, image_path, prompt\]\)'''

list_jobs_new = '''    # Format for table display
    headers = ['ID', 'Type', 'Status', 'Created', 'Updated']
    rows = []
    for job in jobs:
        created = job['created_at'][:19] if job['created_at'] else ''
        updated = job.get('updated_at', '')[:19] if job.get('updated_at') else ''
        rows.append([job['job_id'], job['job_type'], job['status'], created, updated])'''

content = re.sub(list_jobs_old, list_jobs_new, content, flags=re.DOTALL)
print("✓ Simplified cmd_list_jobs formatting")

# 5. Simplify cmd_job_details - remove domain-specific display
job_details_old = r'''    print\(f"Job Details: \{args\.job_id\}"\)
    print\(f"  Status: \{job\['status'\]\}"\)
    print\(f"  Job Type: \{job\['job_type'\]\}"\)
    
    # Display job-type specific information
    data = job\.get\('data', \{\}\)
    if job\['job_type'\] in \['sdxl_generation', 'pony_flux'\]:
        print\(f"  Pony Prompt: \{data\.get\('pony_prompt', 'N/A'\)\}"\)
        print\(f"  Flux Prompt: \{data\.get\('flux_prompt', 'N/A'\)\}"\)
    else:
        print\(f"  Image: \{data\.get\('input_image_path', 'N/A'\)\}"\)
        print\(f"  Prompt: \{data\.get\('user_prompt', 'N/A'\)\}"\)
    
    print\(f"  Padding Factor: \{data\.get\('padding_factor', 1\.5\)\}"\)
    print\(f"  Mask Padding: \{data\.get\('mask_padding_factor', 1\.2\)\}"\)
    print\(f"  Created: \{job\['created_at'\]\}"\)'''

job_details_new = '''    print(f"Job Details: {args.job_id}")
    print(f"  Status: {job['status']}")
    print(f"  Job Type: {job['job_type']}")
    print(f"  Machine Type: {job.get('machine_type', 'N/A')}")
    print(f"  Created: {job['created_at']}")'''

content = re.sub(job_details_old, job_details_new, content, flags=re.DOTALL)
print("✓ Simplified cmd_job_details")

# 6. Remove cmd_migrate_queue - deprecated legacy feature
migrate_pattern = r'def cmd_migrate_queue\(args\):.*?(?=\ndef )'
content = re.sub(migrate_pattern, '', content, flags=re.DOTALL)
print("✓ Removed cmd_migrate_queue (deprecated)")

# 7. Simplify cmd_add_job - remove domain-specific validation
add_job_validation_old = r'''    # Validate job type specific requirements
    if args\.type == 'face_processing':
        if not args\.input_image:
            print\("Error: --input-image is required for face_processing jobs"\)
            return 1
        if not os\.path\.exists\(args\.input_image\):
            print\(f"Error: Input image not found: \{args\.input_image\}"\)
            return 1
        abs_path = os\.path\.abspath\(args\.input_image\)
    elif args\.type in \['pony_flux', 'sdxl_generation'\]:
        if not args\.pony_prompt or not args\.flux_prompt:
            print\(f"Error: --pony-prompt and --flux-prompt are required for \{args\.type\} jobs"\)
            return 1
        abs_path = None
    
    # Set machine type based on job type
    if args\.type == 'sdxl_generation':
        machine_type = 'sdxl_generator'
    elif args\.type == 'face_processing':
        machine_type = 'face_processor'
    else:
        machine_type = args\.type'''

add_job_validation_new = '''    # Set machine type
    machine_type = args.machine_type or args.type
    
    # Build job data from provided arguments
    abs_path = None
    if args.input_file:
        if not os.path.exists(args.input_file):
            print(f"Error: Input file not found: {args.input_file}")
            return 1
        abs_path = os.path.abspath(args.input_file)'''

content = re.sub(add_job_validation_old, add_job_validation_new, content, flags=re.DOTALL)
print("✓ Simplified cmd_add_job validation")

# 8. Simplify cmd_add_job metadata and data construction
add_job_data_old = r'''    # Create metadata
    metadata = \{
        'workflow': args\.type,
        'padding_factor': args\.padding_factor,
        'mask_padding_factor': args\.mask_padding_factor
    \}
    
    # Create the job with JSON data
    try:
        db_id = job_model\.create_job\(
            job_id=args\.job_id,
            job_type=args\.type,
            machine_type=machine_type,
            data=\{
                'input_image_path': abs_path,
                'user_prompt': args\.prompt,
                'pony_prompt': args\.pony_prompt,
                'flux_prompt': args\.flux_prompt,
                'padding_factor': args\.padding_factor,
                'mask_padding_factor': args\.mask_padding_factor
            \},
            metadata=metadata
        \)'''

add_job_data_new = '''    # Create job data from JSON payload if provided
    job_data = {}
    if args.payload:
        try:
            job_data = json.loads(args.payload)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON payload")
            return 1
    
    # Add input file if provided
    if abs_path:
        job_data['input_file_path'] = abs_path
    
    # Create the job
    try:
        db_id = job_model.create_job(
            job_id=args.job_id,
            job_type=args.type,
            machine_type=machine_type,
            data=job_data,
            metadata={}
        )'''

content = re.sub(add_job_data_old, add_job_data_new, content, flags=re.DOTALL)
print("✓ Simplified cmd_add_job data construction")

# 9. Simplify cmd_add_job output
add_job_output_old = r'''        print\(f"✅ Job created successfully!"\)
        print\(f"   Job ID: \{args\.job_id\}"\)
        print\(f"   Job Type: \{args\.type\}"\)
        print\(f"   Database ID: \{db_id\}"\)
        
        if args\.type == 'face_processing':
            print\(f"   Input Image: \{abs_path\}"\)
            print\(f"   Prompt: \{args\.prompt\}"\)
        elif args\.type == 'pony_flux':
            print\(f"   Pony Prompt: \{args\.pony_prompt\}"\)
            print\(f"   Flux Prompt: \{args\.flux_prompt\}"\)
        
        print\(f"   Padding Factor: \{args\.padding_factor\}"\)
        print\(f"   Mask Padding Factor: \{args\.mask_padding_factor\}"\)'''

add_job_output_new = '''        print(f"✅ Job created successfully!")
        print(f"   Job ID: {args.job_id}")
        print(f"   Job Type: {args.type}")
        print(f"   Machine Type: {machine_type}")
        print(f"   Database ID: {db_id}")'''

content = re.sub(add_job_output_old, add_job_output_new, content, flags=re.DOTALL)
print("✓ Simplified cmd_add_job output")

# 10. Remove domain-specific job counts from cmd_machine_status
machine_status_counts = r'''    # Face processing jobs
    face_pending = len\(job_model\.list_jobs\(job_type='face_processing', status='pending'\)\)
    face_processing = len\(job_model\.list_jobs\(job_type='face_processing', status='processing'\)\)
    face_completed = len\(job_model\.list_jobs\(job_type='face_processing', status='completed'\)\)
    face_failed = len\(job_model\.list_jobs\(job_type='face_processing', status='failed'\)\)
    
    print\(f"  Face Processing: \{face_pending\} pending, \{face_processing\} processing, \{face_completed\} completed, \{face_failed\} failed"\)
    
    # SDXL generation jobs
    sdxl_pending = len\(job_model\.list_jobs\(job_type='sdxl_generation', status='pending'\)\)
    sdxl_processing = len\(job_model\.list_jobs\(job_type='sdxl_generation', status='processing'\)\)
    sdxl_completed = len\(job_model\.list_jobs\(job_type='sdxl_generation', status='completed'\)\)
    sdxl_failed = len\(job_model\.list_jobs\(job_type='sdxl_generation', status='failed'\)\)
    
    print\(f"  SDXL Generation: \{sdxl_pending\} pending, \{sdxl_processing\} processing, \{sdxl_completed\} completed, \{sdxl_failed\} failed"\)'''

content = re.sub(machine_status_counts, '    # Job counts by status are shown in the status command\n', content, flags=re.DOTALL)
print("✓ Removed domain-specific counts from cmd_machine_status")

# 11. Update argparse for add-job - make generic
add_job_args_old = r'''    add_job_parser\.add_argument\('job_id', help='Unique job identifier'\)
    add_job_parser\.add_argument\('--type', choices=\['face_processing', 'pony_flux', 'sdxl_generation'\], 
                               default='face_processing', help='Job type \(default: face_processing\)'\)
    add_job_parser\.add_argument\('--input-image', help='Path to input image file \(required for face_processing\)'\)
    add_job_parser\.add_argument\('--prompt', default='make this person more attractive', 
                               help='AI prompt for face modification'\)
    add_job_parser\.add_argument\('--pony-prompt', help='Pony model prompt \(for pony_flux jobs\)'\)
    add_job_parser\.add_argument\('--flux-prompt', help='Flux model prompt \(for pony_flux jobs\)'\)
    add_job_parser\.add_argument\('--padding-factor', type=float, default=1\.5,
                               help='Face crop padding factor \(default: 1\.5\)'\)
    add_job_parser\.add_argument\('--mask-padding-factor', type=float, default=1\.2,
                               help='Mask padding factor \(default: 1\.2\)'\)'''

add_job_args_new = '''    add_job_parser.add_argument('job_id', help='Unique job identifier')
    add_job_parser.add_argument('--type', required=True,
                               help='Job type (string, e.g., processing, generation, etc.)')
    add_job_parser.add_argument('--machine-type',
                               help='Target machine type (defaults to job type)')
    add_job_parser.add_argument('--input-file',
                               help='Path to input file (optional)')
    add_job_parser.add_argument('--payload',
                               help='JSON payload with job-specific data (optional)')'''

content = re.sub(add_job_args_old, add_job_args_new, content, flags=re.DOTALL)
print("✓ Updated add-job arguments to be generic")

# 12. Remove job type choices from list command
list_type_old = r"list_parser\.add_argument\('--type', choices=\['face_processing', 'pony_flux', 'sdxl_generation'\],\s+help='Filter by job type'\)"
list_type_new = "list_parser.add_argument('--type', help='Filter by job type (string)')"
content = re.sub(list_type_old, list_type_new, content)
print("✓ Made list --type generic")

# 13. Remove migrate parser
migrate_parser_pattern = r"    # Migration command\n    migrate_parser = .*?add_argument\('--backup'.*?\)\n\s*\n"
content = re.sub(migrate_parser_pattern, '', content, flags=re.DOTALL)
print("✓ Removed migrate parser")

# 14. Remove migrate command handler
migrate_handler = r"        elif args\.command == 'migrate':\n            cmd_migrate_queue\(args\)\n"
content = re.sub(migrate_handler, '', content)
print("✓ Removed migrate handler")

# Write the cleaned file
with open('src/statemachine_engine/database/cli.py', 'w') as f:
    f.write(content)

print("\n✅ Comprehensive cleanup complete!")
print("\nRemoved:")
print("  - 'face-changer pipeline' references")
print("  - Domain-specific job type validation")
print("  - Hardcoded face_processing, pony_flux, sdxl_generation types")
print("  - Domain-specific prompts and parameters")
print("  - cmd_migrate_queue() - deprecated legacy feature")
print("  - Domain-specific display formatting")
print("  - Domain-specific job counting")
print("\nMade generic:")
print("  - Job types are now freeform strings")
print("  - add-job uses --payload for custom data")
print("  - Simplified display shows only core fields")
