"""Copy the SQLite database to database/backups/farm_YYYYmmdd_HHMMSS.db (safe to run any time).
Usage: python scripts/backup_db.py"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(BASE, 'database', 'farm.db')

if not os.path.exists(SRC):
    sys.exit('No database found at %s. Nothing to back up.' % SRC)

dest_dir = os.path.join(BASE, 'database', 'backups')
os.makedirs(dest_dir, exist_ok=True)
dest = os.path.join(dest_dir, 'farm_%s.db' % datetime.now().strftime('%Y%m%d_%H%M%S'))

# sqlite3's backup API gives a consistent copy even if the app is running.
src_conn, dst_conn = sqlite3.connect(SRC), sqlite3.connect(dest)
with dst_conn:
    src_conn.backup(dst_conn)
src_conn.close(); dst_conn.close()
print('Backup created:', dest)
