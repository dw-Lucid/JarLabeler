import sqlite3
import os

# From your REC spreadsheet
rec_brands = {
    '710 Labs': ['710 Labs Deli'],
    'Antero': ['Antero Popcorn', 'Antero Premium Buds'],
    'Boulder Built': ['Boulder Built'],
    'Cherry': ['Cherry'],
    'Legacy Grown': ['Popcorn', 'Buds', 'Premium'],
    'Locol Love': ['Locol Love'],
    'Natty Rems': ['Natty Rems'],
    'Petrol': ['Petrol'],
}

# From your MED spreadsheet
med_brands = {
    'Boulder Built': ['Red Tier', 'Yellow Tier', 'Pink Tier'],
    'Canna Club': ['Red Tier'],
    'Cherry': ['Red Tier', 'Purple Tier'],
    'Karmaceuticals': ['Green Tier'],
    'Legacy Grown': ['Red Tier', 'Orange Tier', 'Yellow Tier', 'Green Tier'],
    'Natty Rems': ['Purple Tier'],
    'Leiffa': ['Orange Tier', 'Yellow Tier'],
    'NuHi': ['Red Tier'],
    'Petrol': ['Pink Tier'],
    'Shift': ['Yellow Tier'],
    'Vera': ['Red Tier'],
    'Long Gone Farms': ['Red Tier'],
}

# Database setup
def init_db():
    try:
        os.makedirs('db', exist_ok=True)
        print("Created 'db' folder if missing.")
        conn = sqlite3.connect('db/jarlabeler.db')
        print("Connected to DB file.")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS brands
                     (id INTEGER PRIMARY KEY, name TEXT, category TEXT, logo_path TEXT,
                      UNIQUE(name, category))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tiers
                     (id INTEGER PRIMARY KEY, brand_id INTEGER, name TEXT, nametag_bg_path TEXT, pricetag_bg_path TEXT)''')
        conn.commit()
        print("Tables created/verified.")
        return conn
    except Exception as e:
        print(f"Error in init_db: {e}")
        raise

def seed_db():
    conn = init_db()  # Create tables if not exist
    c = conn.cursor()

    # Seed REC
    for brand, tiers in rec_brands.items():
        try:
            c.execute("INSERT OR IGNORE INTO brands (name, category) VALUES (?, 'REC')", (brand,))
            conn.commit()
            brand_id = c.execute("SELECT id FROM brands WHERE name=? AND category='REC'", (brand,)).fetchone()[0]
            print(f"Inserted/ignored REC brand: {brand} (ID: {brand_id})")
            for tier in tiers:
                c.execute("INSERT OR IGNORE INTO tiers (brand_id, name) VALUES (?, ?)",
                          (brand_id, tier))
                print(f"  - Inserted/ignored tier: {tier}")
        except Exception as e:
            print(f"Error seeding REC {brand}: {e}")
    conn.commit()

    # Seed MED
    for brand, tiers in med_brands.items():
        try:
            c.execute("INSERT OR IGNORE INTO brands (name, category) VALUES (?, 'MED')", (brand,))
            conn.commit()
            brand_id = c.execute("SELECT id FROM brands WHERE name=? AND category='MED'", (brand,)).fetchone()[0]
            print(f"Inserted/ignored MED brand: {brand} (ID: {brand_id})")
            for tier in tiers:
                c.execute("INSERT OR IGNORE INTO tiers (brand_id, name) VALUES (?, ?)",
                          (brand_id, tier))
                print(f"  - Inserted/ignored tier: {tier}")
        except Exception as e:
            print(f"Error seeding MED {brand}: {e}")
    conn.commit()
    print("Seeding complete. Run the app to verify. DB file size: " + str(os.path.getsize('db/jarlabeler.db')) + " bytes")

if __name__ == "__main__":
    seed_db()