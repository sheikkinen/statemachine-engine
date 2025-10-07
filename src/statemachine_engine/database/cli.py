#!/usr/bin/env python3
"""
Database CLI for face-changer pipeline

IMPORTANT: Changes via Change Management, see CLAUDE.md

Provides database management and querying capabilities
"""
import argparse
import sys
from pathlib import Path
from tabulate import tabulate
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from statemachine_engine.database.models import get_database, get_job_model, get_machine_event_model, get_machine_state_model, get_realtime_event_model
import socket


def _send_wake_up_socket(target_machine: str) -> bool:
    """Send wake-up signal via Unix socket. Returns True if successful."""
    try:
        socket_path = f'/tmp/statemachine-control-{target_machine}.sock'
        
        # Check if socket exists
        if not Path(socket_path).exists():
            return False
        
        # Send wake-up message
        wake_up_msg = json.dumps({'type': 'wake_up'})
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(wake_up_msg.encode('utf-8'), socket_path)
        sock.close()
        
        return True
        
    except Exception:
        # Silently ignore socket errors (fallback to polling will work)
        return False


def cmd_status(args):
    """Show database status"""
    job_model = get_job_model()
    
    # Overall job counts
    total = job_model.count_jobs()
    pending = job_model.count_jobs('pending')
    processing = job_model.count_jobs('processing')
    completed = job_model.count_jobs('completed')
    failed = job_model.count_jobs('failed')
    
    print(f"Database Status:")
    print(f"  Total jobs: {total}")
    print(f"  Pending: {pending}")
    print(f"  Processing: {processing}")
    print(f"  Completed: {completed}")
    print(f"  Failed: {failed}")
    
    # Job counts by type
    print(f"\nFace Processing Jobs:")
    fp_total = job_model.count_jobs(job_type='face_processing')
    fp_pending = job_model.count_jobs('pending', 'face_processing')
    fp_processing = job_model.count_jobs('processing', 'face_processing')
    fp_completed = job_model.count_jobs('completed', 'face_processing')
    fp_failed = job_model.count_jobs('failed', 'face_processing')
    print(f"  Total: {fp_total}")
    print(f"  Pending: {fp_pending}")
    print(f"  Processing: {fp_processing}")
    print(f"  Completed: {fp_completed}")
    print(f"  Failed: {fp_failed}")
    
    print(f"\nPony-Flux Jobs:")
    pf_total = job_model.count_jobs(job_type='pony_flux')
    pf_pending = job_model.count_jobs('pending', 'pony_flux')
    pf_processing = job_model.count_jobs('processing', 'pony_flux')
    pf_completed = job_model.count_jobs('completed', 'pony_flux')
    pf_failed = job_model.count_jobs('failed', 'pony_flux')
    print(f"  Total: {pf_total}")
    print(f"  Pending: {pf_pending}")
    print(f"  Processing: {pf_processing}")
    print(f"  Completed: {pf_completed}")
    print(f"  Failed: {pf_failed}")

def get_pony_flux_status_counts():
    """Get pony-flux job status counts"""
    from database.models import Database
    
    db = Database()
    counts = {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
    
    try:
        with db._get_connection() as conn:
            # Total count
            cursor = conn.execute("SELECT COUNT(*) FROM pony_flux_jobs")
            counts['total'] = cursor.fetchone()[0]
            
            # Status counts
            for status in ['pending', 'processing', 'completed', 'failed']:
                cursor = conn.execute("SELECT COUNT(*) FROM pony_flux_jobs WHERE status = ?", (status,))
                counts[status] = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting pony-flux counts: {e}")
    
    return counts

def cmd_list_pony_flux_jobs(args):
    """List pony-flux jobs"""
    from database.models import Database
    
    db = Database()
    
    try:
        with db._get_connection() as conn:
            query = "SELECT id, pony_prompt, flux_prompt, status, created_at, updated_at FROM pony_flux_jobs"
            params = []
            
            if args.status:
                query += " WHERE status = ?"
                params.append(args.status)
            
            query += " ORDER BY created_at DESC"
            
            if args.limit:
                query += " LIMIT ?"
                params.append(args.limit)
            
            cursor = conn.execute(query, params)
            jobs = cursor.fetchall()
        
        if not jobs:
            print("No pony-flux jobs found")
            return
        
        # Format for table display
        headers = ['ID', 'Status', 'Created', 'Pony Prompt', 'Flux Prompt']
        rows = []
        for job in jobs:
            job_id, pony_prompt, flux_prompt, status, created_at, updated_at = job
            created = created_at[:19] if created_at else ''
            pony_short = (pony_prompt[:25] + '...') if pony_prompt and len(pony_prompt) > 25 else pony_prompt
            flux_short = (flux_prompt[:25] + '...') if flux_prompt and len(flux_prompt) > 25 else flux_prompt
            rows.append([job_id, status, created, pony_short, flux_short])
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        
    except Exception as e:
        print(f"Error listing pony-flux jobs: {e}")

def cmd_pony_flux_details(args):
    """Show detailed pony-flux job information"""
    from database.models import Database
    
    db = Database()
    
    try:
        with db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, pony_prompt, flux_prompt, status, created_at, updated_at, metadata
                FROM pony_flux_jobs WHERE id = ?
            """, (args.job_id,))
            job = cursor.fetchone()
        
        if not job:
            print(f"Pony-flux job {args.job_id} not found")
            return
        
        job_id, pony_prompt, flux_prompt, status, created_at, updated_at, metadata = job
        
        print(f"Pony-Flux Job Details: {job_id}")
        print(f"  Status: {status}")
        print(f"  Pony Prompt: {pony_prompt}")
        print(f"  Flux Prompt: {flux_prompt}")
        print(f"  Created: {created_at}")
        print(f"  Updated: {updated_at}")
        if metadata:
            print(f"  Metadata: {metadata}")
        
        # Check for generated files
        print(f"\nGenerated Files:")
        from pathlib import Path
        
        # Check for pony image
        pony_file = Path(f"0-generated/{job_id}-pony.png")
        if pony_file.exists():
            print(f"  Pony image: {pony_file} ✅")
        else:
            print(f"  Pony image: {pony_file} ❌")
        
        # Check for scaled image
        scaled_file = Path(f"0-scaled/{job_id}-pony_upscaled.png")
        if scaled_file.exists():
            print(f"  Scaled image: {scaled_file} ✅")
        else:
            print(f"  Scaled image: {scaled_file} ❌")
        
        # Check for final result
        final_file = Path(f"6-final/{job_id}-make_this_person_more_attractive.png")
        if final_file.exists():
            print(f"  Final result: {final_file} ✅")
        else:
            print(f"  Final result: {final_file} ❌")
            
    except Exception as e:
        print(f"Error getting pony-flux job details: {e}")

def cmd_list_jobs(args):
    """List jobs"""
    job_model = get_job_model()
    jobs = job_model.list_jobs(status=args.status, job_type=args.type, limit=args.limit)
    
    if not jobs:
        job_type_desc = f" ({args.type})" if args.type else ""
        status_desc = f" with status '{args.status}'" if args.status else ""
        print(f"No jobs{job_type_desc}{status_desc} found")
        return
    
    # Format for table display - adjust headers based on job type
    if args.type == 'pony_flux':
        headers = ['ID', 'Type', 'Status', 'Created', 'Pony Prompt', 'Flux Prompt']
        rows = []
        for job in jobs:
            created = job['created_at'][:19] if job['created_at'] else ''
            pony_prompt = (job['pony_prompt'][:25] + '...') if job['pony_prompt'] and len(job['pony_prompt']) > 25 else job['pony_prompt']
            flux_prompt = (job['flux_prompt'][:25] + '...') if job['flux_prompt'] and len(job['flux_prompt']) > 25 else job['flux_prompt']
            rows.append([job['job_id'], job['job_type'], job['status'], created, pony_prompt, flux_prompt])
    else:
        headers = ['ID', 'Type', 'Status', 'Created', 'Image', 'Prompt']
        rows = []
        for job in jobs:
            created = job['created_at'][:19] if job['created_at'] else ''
            data = job.get('data', {})
            input_image_path = data.get('input_image_path', '')
            image_path = Path(input_image_path).name if input_image_path else ''
            user_prompt = data.get('user_prompt', '')
            prompt = (user_prompt[:30] + '...') if user_prompt and len(user_prompt) > 30 else user_prompt
            rows.append([job['job_id'], job['job_type'], job['status'], created, image_path, prompt])
    
    print(tabulate(rows, headers=headers, tablefmt='grid'))

def cmd_job_details(args):
    """Show detailed job information"""
    job_model = get_job_model()
    pipeline_model = get_pipeline_model()
    
    job = job_model.get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found")
        return
    
    print(f"Job Details: {args.job_id}")
    print(f"  Status: {job['status']}")
    print(f"  Job Type: {job['job_type']}")
    
    # Display job-type specific information
    data = job.get('data', {})
    if job['job_type'] in ['sdxl_generation', 'pony_flux']:
        print(f"  Pony Prompt: {data.get('pony_prompt', 'N/A')}")
        print(f"  Flux Prompt: {data.get('flux_prompt', 'N/A')}")
    else:
        print(f"  Image: {data.get('input_image_path', 'N/A')}")
        print(f"  Prompt: {data.get('user_prompt', 'N/A')}")
    
    print(f"  Padding Factor: {data.get('padding_factor', 1.5)}")
    print(f"  Mask Padding: {data.get('mask_padding_factor', 1.2)}")
    print(f"  Created: {job['created_at']}")
    print(f"  Started: {job['started_at']}")
    print(f"  Completed: {job['completed_at']}")
    if job['error_message']:
        print(f"  Error: {job['error_message']}")
    
    # Show pipeline results
    results = pipeline_model.get_job_results(args.job_id)
    if results:
        print(f"\nPipeline Steps ({len(results)} completed):")
        for result in results:
            print(f"  {result['step_number']}. {result['step_name']} - {result['completed_at'][:19]}")
            if result['face_coordinates']:
                coords = result['face_coordinates']
                print(f"     Face coordinates: {coords}")
            if result['crop_dimensions']:
                dims = result['crop_dimensions']
                print(f"     Crop dimensions: {dims}")
            if result['file_paths']:
                paths = result['file_paths']
                print(f"     Files: {paths}")

def cmd_migrate_queue(args):
    """Migrate existing queue.json to database"""
    job_model = get_job_model()
    queue_file = Path("data/queue.json")
    
    if not queue_file.exists():
        print("No queue.json file found to migrate")
        return
    
    try:
        with open(queue_file) as f:
            queue_data = json.load(f)
        
        migrated = 0
        for item in queue_data.get('jobs', []):
            job_id = item.get('id')
            if job_id and 'input_image' in item:
                # Check if already exists
                existing = job_model.get_job(job_id)
                if not existing:
                    job_model.create_job(
                        job_id=job_id,
                        job_type='face_processing',
                        data={
                            'input_image_path': item['input_image'],
                            'user_prompt': item.get('user_prompt', 'make this person more attractive')
                        }
                    )
                    migrated += 1
        
        print(f"Migrated {migrated} jobs from queue.json to database")
        
        if args.backup:
            import shutil
            shutil.move(queue_file, f"{queue_file}.backup")
            print(f"Backed up queue.json to {queue_file}.backup")
            
    except Exception as e:
        print(f"Migration failed: {e}")

def cmd_cleanup(args):
    """Clean up old jobs"""
    job_model = get_job_model()
    
    if args.status:
        if args.status == 'processing':
            # Special handling for processing jobs - reset to pending instead of deleting
            print("WARNING: Use 'reset-processing' command to reset stuck processing jobs to pending.")
            print("The 'cleanup --status processing' command deletes jobs permanently!")
            return
            
        # Clean up specific status (except processing)
        jobs = job_model.list_jobs(status=args.status, limit=1000)
        if jobs:
            with job_model.db._get_connection() as conn:
                job_ids = [job['job_id'] for job in jobs]
                placeholders = ','.join(['?' for _ in job_ids])
                conn.execute(f"DELETE FROM pipeline_results WHERE job_id IN ({placeholders})", job_ids)
                conn.execute(f"DELETE FROM jobs WHERE job_id IN ({placeholders})", job_ids)
                conn.commit()
            print(f"Cleaned up {len(jobs)} jobs with status '{args.status}'")
        else:
            print(f"No jobs found with status '{args.status}'")
    else:
        print("Please specify --status for cleanup")

def cmd_reset_processing(args):
    """Reset stuck processing jobs to pending status"""
    job_model = get_job_model()
    
    # Find processing jobs that might be stuck (older than 10 minutes or all if --force)
    with job_model.db._get_connection() as conn:
        if args.force:
            # Reset all processing jobs
            cursor = conn.execute("""
                UPDATE jobs 
                SET status = 'pending', started_at = NULL 
                WHERE status = 'processing'
            """)
            count = cursor.rowcount
        else:
            # Only reset jobs older than 10 minutes
            cursor = conn.execute("""
                UPDATE jobs 
                SET status = 'pending', started_at = NULL 
                WHERE status = 'processing' 
                AND started_at < datetime('now', '-10 minutes')
            """)
            count = cursor.rowcount
        
        conn.commit()
    
    if count > 0:
        print(f"Reset {count} processing jobs to pending status")
    else:
        print("No stuck processing jobs found")

def cmd_cleanup_pony(args):
    """Clean up pony-flux jobs"""
    from database.models import Database
    
    db = Database()
    
    if args.status:
        # Clean up pony-flux jobs with specific status
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM pony_flux_jobs WHERE status = ?", (args.status,))
            pony_jobs = cursor.fetchall()
            
            if pony_jobs:
                job_ids = [job[0] for job in pony_jobs]
                placeholders = ','.join(['?' for _ in job_ids])
                
                # Delete from pony_flux_jobs table
                cursor.execute(f"DELETE FROM pony_flux_jobs WHERE id IN ({placeholders})", job_ids)
                
                # Also clean up any related records in other tables
                cursor.execute(f"DELETE FROM pipeline_results WHERE job_id IN ({placeholders})", job_ids)
                cursor.execute(f"DELETE FROM jobs WHERE job_id IN ({placeholders})", job_ids)
                
                conn.commit()
                print(f"Cleaned up {len(job_ids)} pony-flux jobs with status '{args.status}'")
            else:
                print(f"No pony-flux jobs found with status '{args.status}'")
    else:
        # Clean up all pony-flux jobs
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM pony_flux_jobs")
            pony_jobs = cursor.fetchall()
            
            if pony_jobs:
                job_ids = [job[0] for job in pony_jobs]
                placeholders = ','.join(['?' for _ in job_ids])
                
                # Delete from pony_flux_jobs table
                cursor.execute(f"DELETE FROM pony_flux_jobs WHERE id IN ({placeholders})", job_ids)
                
                # Also clean up any related records in other tables
                cursor.execute(f"DELETE FROM pipeline_results WHERE job_id IN ({placeholders})", job_ids)
                cursor.execute(f"DELETE FROM jobs WHERE job_id IN ({placeholders})", job_ids)
                
                conn.commit()
                print(f"Cleaned up {len(job_ids)} pony-flux jobs")
            else:
                print("No pony-flux jobs found")

def cmd_cleanup_events(args):
    """Clean up machine events"""
    event_model = get_machine_event_model()
    
    try:
        if args.status:
            # Clean up events with specific status
            with event_model.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM machine_events WHERE status = ?", (args.status,))
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute("DELETE FROM machine_events WHERE status = ?", (args.status,))
                    conn.commit()
                    print(f"Cleaned up {count} events with status '{args.status}'")
                else:
                    print(f"No events found with status '{args.status}'")
        else:
            # Clean up all events
            with event_model.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM machine_events")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    cursor.execute("DELETE FROM machine_events")
                    conn.commit()
                    print(f"Cleaned up {count} events from the event table")
                else:
                    print("No events found in the event table")
                    
    except Exception as e:
        print(f"❌ Error cleaning up events: {e}")

def cmd_add_job(args):
    """Add a new job to the database"""
    import os
    import json
    
    job_model = get_job_model()
    
    # Validate job type specific requirements
    if args.type == 'face_processing':
        if not args.input_image:
            print("Error: --input-image is required for face_processing jobs")
            return 1
        if not os.path.exists(args.input_image):
            print(f"Error: Input image not found: {args.input_image}")
            return 1
        abs_path = os.path.abspath(args.input_image)
    elif args.type in ['pony_flux', 'sdxl_generation']:
        if not args.pony_prompt or not args.flux_prompt:
            print(f"Error: --pony-prompt and --flux-prompt are required for {args.type} jobs")
            return 1
        abs_path = None
    
    # Set machine type based on job type
    if args.type == 'sdxl_generation':
        machine_type = 'sdxl_generator'
    elif args.type == 'face_processing':
        machine_type = 'face_processor'
    else:
        machine_type = 'legacy'
    
    # Create metadata
    metadata = {
        'workflow': args.type,
        'padding_factor': args.padding_factor,
        'mask_padding_factor': args.mask_padding_factor
    }
    
    # Create the job with JSON data
    try:
        db_id = job_model.create_job(
            job_id=args.job_id,
            job_type=args.type,
            machine_type=machine_type,
            data={
                'input_image_path': abs_path,
                'user_prompt': args.prompt,
                'pony_prompt': args.pony_prompt,
                'flux_prompt': args.flux_prompt,
                'padding_factor': args.padding_factor,
                'mask_padding_factor': args.mask_padding_factor
            },
            metadata=metadata
        )
        print(f"✅ Job created successfully!")
        print(f"   Job ID: {args.job_id}")
        print(f"   Job Type: {args.type}")
        print(f"   Database ID: {db_id}")
        
        if args.type == 'face_processing':
            print(f"   Input Image: {abs_path}")
            print(f"   Prompt: {args.prompt}")
        elif args.type == 'pony_flux':
            print(f"   Pony Prompt: {args.pony_prompt}")
            print(f"   Flux Prompt: {args.flux_prompt}")
        
        print(f"   Padding Factor: {args.padding_factor}")
        print(f"   Mask Padding Factor: {args.mask_padding_factor}")
        return 0
    except Exception as e:
        print(f"❌ Error creating job: {e}")
        return 1

def cmd_update_pony_flux_status(args):
    """Update pony-flux job status"""
    from database.models import Database
    
    db = Database()
    
    try:
        with db._get_connection() as conn:
            # Check if job exists
            cursor = conn.execute("SELECT id FROM pony_flux_jobs WHERE id = ?", (args.job_id,))
            if not cursor.fetchone():
                print(f"Pony-flux job {args.job_id} not found")
                return 1
            
            # Update status and completed timestamp
            if args.status == 'completed':
                conn.execute("""
                    UPDATE pony_flux_jobs 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (args.status, args.job_id))
            else:
                conn.execute("""
                    UPDATE pony_flux_jobs 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (args.status, args.job_id))
            
            conn.commit()
        
        print(f"✅ Updated pony-flux job {args.job_id} status to '{args.status}'")
        return 0
    except Exception as e:
        print(f"❌ Error updating job status: {e}")
        return 1

def cmd_complete_job(args):
    """Mark a job as completed in the database"""
    job_model = get_job_model()
    
    # Check if job exists
    job = job_model.get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found")
        return 1
    
    try:
        job_model.complete_job(args.job_id)
        print(f"✅ Job {args.job_id} marked as completed!")
        return 0
    except Exception as e:
        print(f"❌ Error completing job: {e}")
        return 1

def cmd_fail_job(args):
    """Mark a job as failed in the database"""
    job_model = get_job_model()
    
    # Check if job exists
    job = job_model.get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found")
        return 1
    
    try:
        job_model.fail_job(args.job_id, args.reason)
        print(f"❌ Job {args.job_id} marked as failed!")
        print(f"   Reason: {args.reason}")
        return 0
    except Exception as e:
        print(f"❌ Error failing job: {e}")
        return 1

def cmd_remove_job(args):
    """Remove a job from the database"""
    job_model = get_job_model()
    pipeline_model = get_pipeline_model()
    
    # Check if job exists
    job = job_model.get_job(args.job_id)
    if not job:
        print(f"Job {args.job_id} not found")
        return 1
    
    try:
        # Remove pipeline results first
        with job_model.db._get_connection() as conn:
            conn.execute("DELETE FROM pipeline_results WHERE job_id = ?", (args.job_id,))
            conn.execute("DELETE FROM jobs WHERE job_id = ?", (args.job_id,))
            conn.commit()
        
        print(f"✅ Job {args.job_id} removed successfully!")
        print(f"   Reason: {args.reason or 'No reason specified'}")
        return 0
    except Exception as e:
        print(f"❌ Error removing job: {e}")
        return 1

def cmd_recreate_database(args):
    """Recreate database with fresh schema"""
    import os
    from database.models import Database
    
    db_path = "data/pipeline.db"
    
    # Confirm destructive operation
    if not args.force:
        print("⚠️  WARNING: This will permanently delete ALL job data!")
        print(f"   Database: {db_path}")
        response = input("   Type 'DELETE ALL DATA' to confirm: ")
        if response != "DELETE ALL DATA":
            print("❌ Operation cancelled")
            return 1
    
    try:
        # Remove existing database file
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  Removed existing database: {db_path}")
        
        # Create fresh database with new schema
        db = Database(db_path)
        print(f"✅ Created fresh database with unified schema: {db_path}")
        
        # Verify tables were created
        with db._get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"📋 Tables created: {', '.join(tables)}")
        
        return 0
    except Exception as e:
        print(f"❌ Error recreating database: {e}")
        return 1

def cmd_send_event(args):
    """Send an event to a target state machine"""
    event_model = get_machine_event_model()
    
    try:
        event_id = event_model.send_event(
            target_machine=args.target,
            event_type=args.type,
            job_id=args.job_id,
            payload=args.payload
        )
        
        # Send actual event via Unix socket (fast path) - not just wake_up!
        socket_path = f'/tmp/statemachine-control-{args.target}.sock'
        
        if Path(socket_path).exists():
            try:
                # Send the actual event with payload
                event_msg = json.dumps({
                    'type': args.type,
                    'payload': args.payload or {},
                    'job_id': args.job_id
                })
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                sock.sendto(event_msg.encode('utf-8'), socket_path)
                sock.close()
            except Exception as e:
                # Socket error - machine will fall back to polling
                pass
        
        print(f"✅ Event sent successfully!")
        print(f"   Event ID: {event_id}")
        print(f"   Target: {args.target}")
        print(f"   Type: {args.type}")
        if args.job_id:
            print(f"   Job ID: {args.job_id}")
        if args.payload:
            print(f"   Payload: {args.payload}")
        
        return 0
    except Exception as e:
        print(f"❌ Error sending event: {e}")
        return 1

def cmd_list_events(args):
    """List machine events"""
    event_model = get_machine_event_model()
    
    try:
        events = event_model.list_events(
            target_machine=args.target,
            status=args.status,
            limit=args.limit
        )
        
        if not events:
            filters = []
            if args.target:
                filters.append(f"target '{args.target}'")
            if args.status:
                filters.append(f"status '{args.status}'")
            filter_desc = f" with {' and '.join(filters)}" if filters else ""
            print(f"No events{filter_desc} found")
            return 0
        
        # Format for table display
        headers = ['ID', 'Target', 'Type', 'Job ID', 'Status', 'Created', 'Payload']
        rows = []
        for event in events:
            created = event['created_at'][:19] if event['created_at'] else ''
            payload = (event['payload'][:30] + '...') if event['payload'] and len(event['payload']) > 30 else event['payload']
            rows.append([
                event['id'], 
                event['target_machine'], 
                event['event_type'], 
                event['job_id'] or '', 
                event['status'], 
                created,
                payload or ''
            ])
        
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        return 0
        
    except Exception as e:
        print(f"❌ Error listing events: {e}")
        return 1

def cmd_process_events(args):
    """Show pending events for a machine (used by state machines)"""
    event_model = get_machine_event_model()
    
    try:
        events = event_model.get_pending_events(args.machine)
        
        if not events:
            print(f"No pending events for machine '{args.machine}'")
            return 0
        
        print(f"Pending events for machine '{args.machine}':")
        for event in events:
            print(f"  Event {event['id']}: {event['event_type']}")
            if event['job_id']:
                print(f"    Job ID: {event['job_id']}")
            if event['payload']:
                print(f"    Payload: {event['payload']}")
            print(f"    Created: {event['created_at']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing events: {e}")
        return 1

def cmd_machine_status(args):
    """Show concurrent machine status"""
    import psutil
    import os
    from datetime import datetime
    
    job_model = get_job_model()
    
    print("=== Concurrent Machine Status ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check job distribution by type and machine
    print("📊 Job Distribution:")
    
    # Face processing jobs
    face_pending = len(job_model.list_jobs(job_type='face_processing', status='pending'))
    face_processing = len(job_model.list_jobs(job_type='face_processing', status='processing'))
    face_completed = len(job_model.list_jobs(job_type='face_processing', status='completed'))
    face_failed = len(job_model.list_jobs(job_type='face_processing', status='failed'))
    
    print(f"  Face Processing: {face_pending} pending, {face_processing} processing, {face_completed} completed, {face_failed} failed")
    
    # SDXL generation jobs
    sdxl_pending = len(job_model.list_jobs(job_type='sdxl_generation', status='pending'))
    sdxl_processing = len(job_model.list_jobs(job_type='sdxl_generation', status='processing'))
    sdxl_completed = len(job_model.list_jobs(job_type='sdxl_generation', status='completed'))
    sdxl_failed = len(job_model.list_jobs(job_type='sdxl_generation', status='failed'))
    
    print(f"  SDXL Generation: {sdxl_pending} pending, {sdxl_processing} processing, {sdxl_completed} completed, {sdxl_failed} failed")
    
    # Pony flux jobs (legacy)
    pony_pending = len(job_model.list_jobs(job_type='pony_flux', status='pending'))
    pony_processing = len(job_model.list_jobs(job_type='pony_flux', status='processing'))
    pony_completed = len(job_model.list_jobs(job_type='pony_flux', status='completed'))
    pony_failed = len(job_model.list_jobs(job_type='pony_flux', status='failed'))
    
    print(f"  Pony Flux (legacy): {pony_pending} pending, {pony_processing} processing, {pony_completed} completed, {pony_failed} failed")
    
    print()
    
    # Check machine events
    print("📨 Machine Events:")
    events_model = get_machine_event_model()
    
    if args.machine:
        pending_events = events_model.list_events(target_machine=args.machine, status='pending')
        processed_events = events_model.list_events(target_machine=args.machine, status='processed', limit=5)
        print(f"  {args.machine}: {len(pending_events)} pending, {len(processed_events)} recent processed")
    else:
        # Check for each machine type
        for machine in ['sdxl_generator', 'face_processor']:
            pending_events = events_model.list_events(target_machine=machine, status='pending')
            processed_events = events_model.list_events(target_machine=machine, status='processed', limit=5)
            print(f"  {machine}: {len(pending_events)} pending, {len(processed_events)} recent processed")
    
    print()
    
    # Check running processes
    print("🔄 Process Status:")
    running_machines = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'state_machine/cli.py' in ' '.join(proc.info['cmdline']):
                cmdline = ' '.join(proc.info['cmdline'])
                if 'sdxl_generator' in cmdline:
                    running_machines.append(f"  SDXL Generator (PID: {proc.info['pid']}) ✅")
                elif 'face_processor' in cmdline:
                    running_machines.append(f"  Face Processor (PID: {proc.info['pid']}) ✅")
                elif 'config/' in cmdline:
                    config_name = [part for part in proc.info['cmdline'] if 'config/' in part][0]
                    running_machines.append(f"  {config_name} (PID: {proc.info['pid']}) ✅")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if running_machines:
        print("\n".join(running_machines))
    else:
        print("  No state machines currently running ❌")

def cmd_machine_health(args):
    """Check concurrent machine health"""
    import os
    from datetime import datetime, timedelta
    from pathlib import Path
    
    print("=== Concurrent Machine Health Check ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check log files
    print("📋 Log Files:")
    log_dir = Path("logs")
    
    for log_file in ['sdxl_generator.log', 'face_processor.log', 'pipeline.log']:
        log_path = log_dir / log_file
        if log_path.exists():
            stat = log_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(stat.st_mtime)
            age = datetime.now() - modified
            
            status = "✅" if age < timedelta(minutes=5) else "⚠️" if age < timedelta(hours=1) else "❌"
            print(f"  {log_file}: {size_mb:.1f}MB, modified {age} ago {status}")
        else:
            print(f"  {log_file}: Missing ❌")
    
    print()
    
    # Check output directories
    print("📁 Output Directories:")
    output_dirs = ['0-generated', '0-scaled', '1-portraits', '2-verified', '3-masks', '4-results', '5-resized', '6-final']
    
    for dir_name in output_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            file_count = len(list(dir_path.glob('*')))
            print(f"  {dir_name}/: {file_count} files ✅")
        else:
            print(f"  {dir_name}/: Missing ❌")
    
    print()
    
    # Check database integrity
    print("🗄️ Database Health:")
    try:
        job_model = get_job_model()
        events_model = get_machine_event_model()
        
        # Count jobs by status
        total_jobs = sum(len(job_model.list_jobs(status=status)) for status in ['pending', 'processing', 'completed', 'failed'])
        print(f"  Total jobs: {total_jobs} ✅")
        
        # Count events
        total_events = len(events_model.list_events(limit=1000))
        print(f"  Total events: {total_events} ✅")
        
        # Check for stuck jobs (processing > 1 hour)
        processing_jobs = job_model.list_jobs(status='processing')
        stuck_jobs = []
        for job in processing_jobs:
            if hasattr(job, 'updated_at') and job.updated_at:
                updated = datetime.fromisoformat(job.updated_at.replace('Z', '+00:00'))
                age = datetime.now() - updated.replace(tzinfo=None)
                if age > timedelta(hours=1):
                    stuck_jobs.append(f"    {job.id} (stuck for {age})")
        
        if stuck_jobs:
            print(f"  Stuck jobs: {len(stuck_jobs)} ⚠️")
            for stuck in stuck_jobs:
                print(stuck)
        else:
            print("  No stuck jobs ✅")
            
    except Exception as e:
        print(f"  Database error: {e} ❌")

def cmd_machine_state(args):
    """Show current state of all state machines"""
    machine_state_model = get_machine_state_model()
    
    # Query all machine states
    with machine_state_model.db._get_connection() as conn:
        rows = conn.execute("""
            SELECT 
                machine_name,
                current_state,
                last_activity
            FROM machine_state 
            ORDER BY machine_name
        """).fetchall()
    
    # Convert to dict list
    machines = []
    for row in rows:
        machines.append({
            'machine_name': row['machine_name'],
            'current_state': row['current_state'],
            'last_activity': row['last_activity']
        })
    
    if args.format == 'json':
        print(json.dumps(machines, indent=2))
    else:
        if not machines:
            print("No machine state data found")
            return
        
        headers = ['Machine', 'Current State', 'Last Activity']
        table_data = [[m['machine_name'], m['current_state'], m['last_activity']] 
                     for m in machines]
        print(tabulate(table_data, headers=headers, tablefmt='grid'))

def cmd_controller_log(args):
    """Show controller event processing log"""
    controller_log = get_controller_log_model()
    
    try:
        with controller_log.db._get_connection() as conn:
            query = """
                SELECT 
                    id,
                    job_id, 
                    event_type, 
                    event_id, 
                    action, 
                    details,
                    created_at
                FROM controller_log 
                ORDER BY created_at DESC
            """
            
            if hasattr(args, 'limit') and args.limit:
                query += f" LIMIT {args.limit}"
                
            rows = conn.execute(query).fetchall()
        
        if not rows:
            print("No controller log entries found")
            return
        
        # Format for display
        headers = ['ID', 'Job ID', 'Event Type', 'Event ID', 'Action', 'Details', 'Created At']
        table_data = []
        
        for row in rows:
            # Truncate job_id for better display
            job_id = row['job_id'][:20] + '...' if len(row['job_id']) > 23 else row['job_id']
            details = row['details'] or ''
            if len(details) > 20:
                details = details[:17] + '...'
            
            table_data.append([
                row['id'],
                job_id,
                row['event_type'],
                row['event_id'],
                row['action'],
                details,
                row['created_at']
            ])
        
        print(f"\n📋 Controller Event Processing Log ({len(rows)} entries):")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
    except Exception as e:
        print(f"Error retrieving controller log: {e}")

def cmd_list_errors(args):
    """List error events and failed jobs for UI activity log"""
    from database.models import Database

    db = Database()
    limit = args.limit

    try:
        with db._get_connection() as conn:
            # Query error events and activity logs from machine_events
            error_events_query = """
                SELECT
                    'error_event' as type,
                    event_type as event_name,
                    target_machine as machine,
                    job_id,
                    payload,
                    created_at as timestamp
                FROM machine_events
                WHERE event_type IN ('sdxl_error', 'face_error', 'activity_log')
                ORDER BY created_at DESC
                LIMIT ?
            """

            # Query failed jobs
            failed_jobs_query = """
                SELECT
                    'failed_job' as type,
                    job_type as event_name,
                    machine_type as machine,
                    job_id,
                    error_message as payload,
                    completed_at as timestamp
                FROM jobs
                WHERE status = 'failed' AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT ?
            """

            # Query error-related controller log entries
            controller_errors_query = """
                SELECT
                    'controller_error' as type,
                    event_type as event_name,
                    'controller' as machine,
                    job_id,
                    details as payload,
                    created_at as timestamp
                FROM controller_log
                WHERE event_type IN ('sdxl_error', 'face_error')
                   OR action LIKE '%error%'
                ORDER BY created_at DESC
                LIMIT ?
            """

            # Combine all error sources
            all_errors = []

            # Fetch error events from machine_events (primary source with detailed payloads)
            error_events = conn.execute(error_events_query, (limit,)).fetchall()
            all_errors.extend([dict(row) for row in error_events])

            # Fetch failed jobs
            failed_jobs = conn.execute(failed_jobs_query, (limit,)).fetchall()
            all_errors.extend([dict(row) for row in failed_jobs])

            # Skip controller_log entries - they're duplicates of machine_events without payload details
            # controller_errors = conn.execute(controller_errors_query, (limit,)).fetchall()
            # all_errors.extend([dict(row) for row in controller_errors])

            # Deduplicate by (job_id, event_name, timestamp, payload) to remove duplicates
            # Include payload to avoid deduplicating different activity_log messages with same timestamp
            seen = set()
            unique_errors = []
            for error in all_errors:
                key = (error['job_id'], error['event_name'], error['timestamp'], error['payload'])
                if key not in seen:
                    seen.add(key)
                    unique_errors.append(error)

            # Sort by timestamp descending and limit
            unique_errors.sort(key=lambda x: x['timestamp'] or '', reverse=True)
            unique_errors = unique_errors[:limit]
            all_errors = unique_errors

            if args.format == 'json':
                # Format for API consumption
                formatted_errors = []
                for error in all_errors:
                    payload = error['payload'] or ''
                    message = payload
                    level = 'error'  # Default level

                    # Parse activity_log events to extract message and level
                    if error['event_name'] == 'activity_log':
                        try:
                            parsed = json.loads(payload)
                            message = parsed.get('message', payload)
                            level = parsed.get('level', 'info')
                        except (json.JSONDecodeError, TypeError):
                            message = payload

                    # If message is still empty, use event name
                    if not message:
                        message = f"{error['event_name']} occurred"

                    formatted_errors.append({
                        'type': error['type'],
                        'level': level,
                        'event_name': error['event_name'],
                        'machine': error['machine'],
                        'job_id': error['job_id'],
                        'message': message,
                        'payload': payload,
                        'timestamp': error['timestamp']
                    })
                print(json.dumps(formatted_errors, indent=2))
            else:
                # Human-readable table format
                if not all_errors:
                    print("No errors found")
                    return

                headers = ['Type', 'Event', 'Machine', 'Job ID', 'Message', 'Timestamp']
                table_data = []

                for error in all_errors:
                    message = error['payload'] or f"{error['event_name']} occurred"
                    if len(message) > 40:
                        message = message[:37] + '...'

                    table_data.append([
                        error['type'],
                        error['event_name'],
                        error['machine'],
                        error['job_id'] or 'N/A',
                        message,
                        error['timestamp'][:19] if error['timestamp'] else 'N/A'
                    ])

                print(f"\n❌ Error Events ({len(all_errors)} entries):")
                print(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        print(f"❌ Error retrieving errors: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Database CLI for face-changer pipeline")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show database status')
    
    # List jobs command
    list_parser = subparsers.add_parser('list', help='List jobs')
    list_parser.add_argument('--status', choices=['pending', 'processing', 'completed', 'failed'],
                           help='Filter by status')
    list_parser.add_argument('--type', choices=['face_processing', 'pony_flux', 'sdxl_generation'],
                           help='Filter by job type')
    list_parser.add_argument('--limit', type=int, default=20, help='Limit number of results')
    
    # List pony-flux jobs command
    list_pf_parser = subparsers.add_parser('list-pony-flux', help='List pony-flux jobs')
    list_pf_parser.add_argument('--status', choices=['pending', 'processing', 'completed', 'failed'],
                               help='Filter by status')
    list_pf_parser.add_argument('--limit', type=int, default=20, help='Limit number of results')
    
    # Job details command
    details_parser = subparsers.add_parser('details', help='Show job details')
    details_parser.add_argument('job_id', help='Job ID to show details for')
    
    # Pony-flux job details command
    pf_details_parser = subparsers.add_parser('pony-flux-details', help='Show pony-flux job details')
    pf_details_parser.add_argument('job_id', help='Pony-flux job ID to show details for')
    
    # Migration command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate queue.json to database')
    migrate_parser.add_argument('--backup', action='store_true', help='Backup original queue.json')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old jobs')
    cleanup_parser.add_argument('--status', choices=['pending', 'processing', 'completed', 'failed'],
                               required=True, help='Status of jobs to clean up')
    
    # Reset processing command
    reset_processing_parser = subparsers.add_parser('reset-processing', help='Reset stuck processing jobs to pending')
    reset_processing_parser.add_argument('--force', action='store_true', 
                                       help='Reset all processing jobs regardless of age')
    
    # Cleanup pony command
    cleanup_pony_parser = subparsers.add_parser('cleanup-pony', help='Clean up pony-flux jobs')
    cleanup_pony_parser.add_argument('--status', choices=['pending', 'processing', 'completed', 'failed'],
                                   help='Status of pony-flux jobs to clean up (optional, clears all if not specified)')
    
    # Cleanup events command
    cleanup_events_parser = subparsers.add_parser('cleanup-events', help='Clean up machine events')
    cleanup_events_parser.add_argument('--status', choices=['pending', 'processed'],
                                     help='Status of events to clean up (optional, clears all if not specified)')
    
    # Add job command
    add_job_parser = subparsers.add_parser('add-job', help='Add a new job to the database')
    add_job_parser.add_argument('job_id', help='Unique job identifier')
    add_job_parser.add_argument('--type', choices=['face_processing', 'pony_flux', 'sdxl_generation'], 
                               default='face_processing', help='Job type (default: face_processing)')
    add_job_parser.add_argument('--input-image', help='Path to input image file (required for face_processing)')
    add_job_parser.add_argument('--prompt', default='make this person more attractive', 
                               help='AI prompt for face modification')
    add_job_parser.add_argument('--pony-prompt', help='Pony model prompt (for pony_flux jobs)')
    add_job_parser.add_argument('--flux-prompt', help='Flux model prompt (for pony_flux jobs)')
    add_job_parser.add_argument('--padding-factor', type=float, default=1.5,
                               help='Face crop padding factor (default: 1.5)')
    add_job_parser.add_argument('--mask-padding-factor', type=float, default=1.2,
                               help='Mask padding factor (default: 1.2)')
    
    # Complete job command
    complete_job_parser = subparsers.add_parser('complete-job', help='Mark a job as completed')
    complete_job_parser.add_argument('job_id', help='Job ID to complete')
    
    # Fail job command
    fail_job_parser = subparsers.add_parser('fail-job', help='Mark a job as failed')
    fail_job_parser.add_argument('job_id', help='Job ID to mark as failed')
    fail_job_parser.add_argument('--reason', required=True, help='Reason for failure')
    
    # Remove job command
    remove_job_parser = subparsers.add_parser('remove-job', help='Remove a job from the database')
    remove_job_parser.add_argument('job_id', help='Job ID to remove')
    remove_job_parser.add_argument('--reason', help='Reason for removal (optional)')
    
    # Update pony-flux status command
    update_pf_parser = subparsers.add_parser('update-pony-flux-status', help='Update pony-flux job status')
    update_pf_parser.add_argument('job_id', help='Job ID to update')
    update_pf_parser.add_argument('status', choices=['pending', 'processing', 'completed', 'failed'],
                                 help='New status for the job')
    
    # Recreate database command
    recreate_parser = subparsers.add_parser('recreate-database', help='Recreate database with fresh unified schema (DESTRUCTIVE)')
    recreate_parser.add_argument('--force', action='store_true', 
                               help='Skip confirmation prompt (dangerous!)')
    
    # Send event command
    send_event_parser = subparsers.add_parser('send-event', help='Send an event to a target state machine')
    send_event_parser.add_argument('--target', required=True, 
                                  help='Target machine name (sdxl_generator, face_processor, or all)')
    send_event_parser.add_argument('--type', required=True,
                                  help='Event type (stop, sdxl_job_done, face_job_done, etc.)')
    send_event_parser.add_argument('--job-id', dest='job_id',
                                  help='Related job ID (optional)')
    send_event_parser.add_argument('--payload',
                                  help='JSON payload for the event (optional)')
    
    # List events command
    list_events_parser = subparsers.add_parser('list-events', help='List machine events')
    list_events_parser.add_argument('--target', 
                                   help='Filter by target machine')
    list_events_parser.add_argument('--status', choices=['pending', 'processed'],
                                   help='Filter by event status')
    list_events_parser.add_argument('--limit', type=int, default=20,
                                   help='Limit number of results')
    
    # Process events command (for state machine use)
    process_events_parser = subparsers.add_parser('process-events', help='Show pending events for a machine')
    process_events_parser.add_argument('machine', help='Machine name to check events for')
    
    # Machine status command
    machine_status_parser = subparsers.add_parser('machine-status', help='Show concurrent machine status')
    machine_status_parser.add_argument('--machine', help='Filter by specific machine name')
    
    # Machine health command
    machine_health_parser = subparsers.add_parser('machine-health', help='Check concurrent machine health')
    
    # Machine state command
    machine_state_parser = subparsers.add_parser('machine-state', help='Show current state of all machines')
    machine_state_parser.add_argument('--format', choices=['table', 'json'], default='table',
                                     help='Output format (default: table)')
    
    # Controller log command
    controller_log_parser = subparsers.add_parser('controller-log', help='Show controller event processing log')
    controller_log_parser.add_argument('--limit', type=int, default=20,
                                      help='Limit number of results (default: 20)')

    # List errors command
    list_errors_parser = subparsers.add_parser('list-errors', help='List error events and failed jobs for UI activity log')
    list_errors_parser.add_argument('--limit', type=int, default=50,
                                   help='Limit number of results (default: 50)')
    list_errors_parser.add_argument('--format', choices=['table', 'json'], default='table',
                                   help='Output format (default: table)')

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'status':
            cmd_status(args)
        elif args.command == 'list':
            cmd_list_jobs(args)
        elif args.command == 'list-pony-flux':
            cmd_list_pony_flux_jobs(args)
        elif args.command == 'details':
            cmd_job_details(args)
        elif args.command == 'pony-flux-details':
            cmd_pony_flux_details(args)
        elif args.command == 'migrate':
            cmd_migrate_queue(args)
        elif args.command == 'cleanup':
            cmd_cleanup(args)
        elif args.command == 'reset-processing':
            cmd_reset_processing(args)
        elif args.command == 'cleanup-pony':
            cmd_cleanup_pony(args)
        elif args.command == 'cleanup-events':
            cmd_cleanup_events(args)
        elif args.command == 'add-job':
            return cmd_add_job(args)
        elif args.command == 'complete-job':
            return cmd_complete_job(args)
        elif args.command == 'fail-job':
            return cmd_fail_job(args)
        elif args.command == 'remove-job':
            return cmd_remove_job(args)
        elif args.command == 'update-pony-flux-status':
            return cmd_update_pony_flux_status(args)
        elif args.command == 'recreate-database':
            return cmd_recreate_database(args)
        elif args.command == 'send-event':
            return cmd_send_event(args)
        elif args.command == 'list-events':
            return cmd_list_events(args)
        elif args.command == 'process-events':
            return cmd_process_events(args)
        elif args.command == 'machine-status':
            return cmd_machine_status(args)
        elif args.command == 'machine-health':
            return cmd_machine_health(args)
        elif args.command == 'machine-state':
            return cmd_machine_state(args)
        elif args.command == 'controller-log':
            return cmd_controller_log(args)
        elif args.command == 'list-errors':
            return cmd_list_errors(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()