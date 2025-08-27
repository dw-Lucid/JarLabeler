import sqlite3
import os

def init_db():
    os.makedirs('db', exist_ok=True)
    conn = sqlite3.connect('db/jarlabeler.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS brands
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, logo_path TEXT,
                  UNIQUE(name, category))''')
    c.execute('''CREATE TABLE IF NOT EXISTS tiers
                 (id INTEGER PRIMARY KEY, brand_id INTEGER, name TEXT, prices TEXT DEFAULT '{}', nametag_logo_path TEXT)''')
    conn.commit()
    return conn