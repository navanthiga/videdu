import sqlite3
import os

# Check current directory for .db files
db_files = [f for f in os.listdir() if f.endswith('.db')]
print("SQLite databases in directory:", db_files)