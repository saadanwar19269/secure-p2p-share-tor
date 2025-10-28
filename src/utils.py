import os
import hashlib
import json
from typing import Dict, Any

def ensure_dir(directory: str):
    """Ensure directory exists"""
    os.makedirs(directory, exist_ok=True)

def human_readable_size(size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def save_transfer_log(metadata: Dict[str, Any], log_dir: str = "./logs"):
    """Save transfer metadata to log file"""
    ensure_dir(log_dir)
    log_file = os.path.join(log_dir, "transfers.json")
    
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append({
            'timestamp': time.time(),
            'filename': metadata.get('filename'),
            'filesize': metadata.get('filesize'),
            'checksum': metadata.get('checksum'),
            'encrypted': metadata.get('encrypted', False)
        })
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error saving transfer log: {e}")
