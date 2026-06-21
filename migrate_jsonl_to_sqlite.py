import json
import os
import sys
from pathlib import Path

# Add project root to sys.path to ensure imports work from this directory
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schema.audit_repository import AuditRepository

def run_migration():
    jsonl_path = PROJECT_ROOT / "audit_log.jsonl"
    db_path = PROJECT_ROOT / "audit.db"
    
    print("========================================")
    print("NIYAM-AI LOG MIGRATION: JSONL TO SQLITE")
    print("========================================")
    
    if not jsonl_path.exists():
        print(f"[-] Error: Source log file '{jsonl_path}' not found.")
        sys.exit(1)
        
    if db_path.exists():
        print(f"[*] Removing existing SQLite database at '{db_path}' for a clean, ordered import...")
        try:
            db_path.unlink()
        except OSError as e:
            print(f"[-] Warning: Failed to remove '{db_path}': {e}")
            
    repo = AuditRepository(str(db_path))
    
    total_records = 0
    imported_records = 0
    malformed_records = 0
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue
                
            total_records += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[!] Line {line_num}: JSON syntax error: {e}")
                print(f"    Raw content: {line[:100]}...")
                malformed_records += 1
                continue
                
            try:
                # Use recalculate_hashes=False to preserve historical timestamps and hashes
                repo.insert_event(event, recalculate_hashes=False)
                imported_records += 1
            except Exception as e:
                print(f"[!] Line {line_num}: DB Insertion failed: {e}")
                malformed_records += 1
                
    print("\n----------------------------------------")
    print("MIGRATION COMPLETED")
    print("----------------------------------------")
    print(f"Total lines read:      {total_records}")
    print(f"Successfully imported: {imported_records}")
    print(f"Malformed / Failed:    {malformed_records}")
    
    print("\n[*] Verifying cryptographic chain integrity of the migrated database...")
    report = repo.verify_chain()
    print(f"    Chain valid:       {report['valid']}")
    print(f"    Events checked:    {report['events_checked']}")
    print(f"    Broken links:      {report['broken_links']}")
    
    if not report['valid']:
        print("    Anomalies detected:")
        for anomaly in report['anomalies']:
            print(f"      - {anomaly}")
            
if __name__ == '__main__':
    run_migration()
