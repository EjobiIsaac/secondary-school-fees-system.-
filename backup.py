import os
import shutil
from datetime import datetime
from database import DB_NAME, log_audit


def create_backup(destination_folder: str, username: str) -> str:
    if not os.path.exists(DB_NAME):
        raise FileNotFoundError("Database file does not exist yet.")
    os.makedirs(destination_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"school_fees_backup_{timestamp}.db"
    dest_path = os.path.join(destination_folder, backup_filename)
    shutil.copy2(DB_NAME, dest_path)
    log_audit(username, "BACKUP_DB", f"Created backup at {dest_path}")
    return dest_path


def restore_backup(backup_filepath: str, admin_username: str):
    if not os.path.exists(backup_filepath):
        raise FileNotFoundError("Selected backup file was not found.")
    shutil.copy2(backup_filepath, DB_NAME)
    log_audit(admin_username, "RESTORE_DB", f"Restored database from {backup_filepath}")
  
