#!/usr/bin/env python3
"""
Safe Session Cleanup Script
===========================

Identifies and safely removes duplicate student sessions from Supabase.
Prioritizes data safety by:
1. Defaulting to DRY RUN mode (no changes).
2. Requiring manual confirmation.
3. Performing MANDATORY local backups before any deletion.

Usage:
    python3 safe_cleanup.py --student "Norbert"
    python3 safe_cleanup.py --all --force
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("❌ Missing SUPABASE_URL or SUPABASE_KEY")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BACKUP_DIR = "backups/deleted_sessions"

def ensure_backup_dir():
    """Ensure backup directory exists"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"📁 Created backup directory: {BACKUP_DIR}")

def backup_session(session: Dict[str, Any]) -> str:
    """
    Save full session data to local JSON file.
    Returns the path to the backup file.
    """
    ensure_backup_dir()
    
    # Create a safe filename
    date_str = session.get('session_date', 'unknown_date').replace(':', '-').split('.')[0]
    sid = session.get('id')
    filename = f"backup_{date_str}_{sid}.json"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(session, f, indent=2, default=str)
        
    return filepath

def get_student_id(name_query: str) -> str:
    """Find student ID by name (case-insensitive partial match)"""
    res = supabase.table('students').select('id, first_name, username').ilike('first_name', f'%{name_query}%').execute()
    
    if not res.data:
        # Try username
        res = supabase.table('students').select('id, first_name, username').ilike('username', f'%{name_query}%').execute()
    
    if not res.data:
        return None
        
    if len(res.data) > 1:
        logger.warning(f"⚠️ Multiple students found for '{name_query}':")
        for s in res.data:
            logger.warning(f"   - {s['first_name']} ({s['username']})")
        return None
        
    return res.data[0]['id']

def find_duplicates(sessions: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Identify groups of duplicate sessions.
    Returns a list of lists, where each inner list is a group of potential duplicates.
    """
    duplicates = []
    checked_ids = set()
    
    # Sort by date
    sorted_sessions = sorted(sessions, key=lambda x: x['session_date'], reverse=True)
    
    for i in range(len(sorted_sessions)):
        current = sorted_sessions[i]
        if current['id'] in checked_ids:
            continue
            
        current_group = [current]
        current_date = datetime.fromisoformat(current['session_date'].replace('Z', '+00:00'))
        
        for j in range(i + 1, len(sorted_sessions)):
            candidate = sorted_sessions[j]
            if candidate['id'] in checked_ids:
                continue
                
            candidate_date = datetime.fromisoformat(candidate['session_date'].replace('Z', '+00:00'))
            time_diff = abs((current_date - candidate_date).total_seconds())
            
            # CRITERIA 1: Exact File Hash Match (Strongest)
            current_hash = current.get('metrics', {}).get('file_hash')
            candidate_hash = candidate.get('metrics', {}).get('file_hash')
            
            is_hash_match = current_hash and candidate_hash and current_hash == candidate_hash
            
            # CRITERIA 2: Time Proximity + Duration Match (Weak)
            # Starts within 5 minutes of each other
            is_time_match = time_diff < 300 
            
            # Duration within 1% or 5 seconds
            dur1 = current.get('duration_seconds', 0) or 0
            dur2 = candidate.get('duration_seconds', 0) or 0
            dur_diff = abs(dur1 - dur2)
            is_duration_match = dur_diff < 5 or (dur1 > 0 and dur_diff / dur1 < 0.01)
            
            if is_hash_match or (is_time_match and is_duration_match):
                current_group.append(candidate)
                checked_ids.add(candidate['id'])
        
        if len(current_group) > 1:
            duplicates.append(current_group)
            checked_ids.add(current['id'])
            
    return duplicates

def main():
    parser = argparse.ArgumentParser(description="Safely cleanup duplicate sessions")
    parser.add_argument("--student", type=str, help="Name of student to check")
    parser.add_argument("--all", action="store_true", help="Check ALL students")
    parser.add_argument("--force", action="store_true", help="Actually delete data (default is DRY RUN)")
    args = parser.parse_args()
    
    if not args.student and not args.all:
        logger.error("❌ Must specify --student <name> or --all")
        sys.exit(1)
        
    student_ids = []
    
    if args.student:
        sid = get_student_id(args.student)
        if not sid:
            logger.error(f"❌ Student '{args.student}' not found.")
            sys.exit(1)
        student_ids.append(sid)
    else:
        # Fetch all students
        res = supabase.table('students').select('id').execute()
        student_ids = [r['id'] for r in res.data]
        
    logger.info(f"🔍 Checking {len(student_ids)} students...")
    
    total_duplicates_found = 0
    total_deleted = 0
    
    for sid in student_ids:
        # Fetch sessions
        res = supabase.table('student_sessions').select('*').eq('student_id', sid).execute()
        sessions = res.data
        
        if not sessions:
            continue
            
        duplicate_groups = find_duplicates(sessions)
        
        if duplicate_groups:
            logger.info(f"⚠️ Found {len(duplicate_groups)} duplicate groups for student {sid}")
            
            for group in duplicate_groups:
                print("\n------------------------------------------------")
                print(f"Duplicate Group ({len(group)} sessions):")
                
                # Sort group by duration (keep longest) then date (keep newest)
                # Strategy: Keep the one with the most data (duration)
                group.sort(key=lambda x: x.get('duration_seconds', 0), reverse=True)
                
                keeper = group[0]
                to_delete = group[1:]
                
                print(f"✅ KEEP: {keeper['session_date']} | Dur: {keeper['duration_seconds']}s | ID: {keeper['id']}")
                for item in to_delete:
                    print(f"❌ DELETE: {item['session_date']} | Dur: {item['duration_seconds']}s | ID: {item['id']}")
                
                if args.force:
                    confirm = input("   >>> Confirm deletion of marked items? (y/n): ").strip().lower()
                    if confirm == 'y':
                        for item in to_delete:
                            # 1. BACKUP
                            backup_path = backup_session(item)
                            logger.info(f"      💾 Backed up to {backup_path}")
                            
                            # 2. DELETE
                            res = supabase.table('student_sessions').delete().eq('id', item['id']).execute()
                            logger.info(f"      🗑️ Deleted {item['id']}")
                            total_deleted += 1
                    else:
                        logger.info("      Skipped.")
                else:
                    print("   [DRY RUN] No action taken. Use --force to delete.")
                    
            total_duplicates_found += len(duplicate_groups)
            
    print("\n================================================")
    print(f"SUMMARY: Found {total_duplicates_found} duplicate groups.")
    if args.force:
        print(f"ACTION: Deleted {total_deleted} sessions.")
    else:
        print("ACTION: None (Dry Run).")
    print("================================================")

if __name__ == "__main__":
    main()
