import sqlite3
from PIL import Image, ImageDraw, ImageFont  # For image overlays
import os

# Database setup (stores brands, tiers, template paths)
def init_db():
    conn = sqlite3.connect('db/jarlabeler.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS brands
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, nametag_template TEXT, pricetag_template TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tiers
                 (id INTEGER PRIMARY KEY, name TEXT, color TEXT, brand_id INTEGER)''')  # e.g., 'Green', '#00FF00'
    conn.commit()
    return conn

# Class for Strain/Input
class Strain:
    def __init__(self, type_, name, bua, etc, generic, thc_percent):
        self.type = type_  # S/I/H
        self.name = name
        self.bua = bua
        self.etc = etc
        self.generic = generic
        self.thc_percent = thc_percent

# Class for Brand
class Brand:
    def __init__(self, name, category):  # category: 'REC' or 'MED'
        self.name = name
        self.category = category
        self.nametag_template = None  # Path to image/PDF
        self.pricetag_template = None
        self.tiers = {}  # Dict of tier_name: color/path

    def add_tier(self, tier_name, color):
        self.tiers[tier_name] = color

# Label Generator
class LabelGenerator:
    def __init__(self, db_conn):
        self.db_conn = db_conn

    def generate_labels(self, strain, brand_name, tier_name, item_type):
        # Fetch brand from DB
        c = self.db_conn.cursor()
        c.execute("SELECT * FROM brands WHERE name=?", (brand_name,))
        brand_data = c.fetchone()
        if not brand_data:
            raise ValueError("Brand not found. Configure first.")

        brand = Brand(brand_data[1], brand_data[2])
        brand.nametag_template = brand_data[3]
        brand.pricetag_template = brand_data[4]

        # TODO: Fetch tier details

        # Generate nametag (example: overlay text on image template)
        if brand.nametag_template and os.path.exists(brand.nametag_template):
            img = Image.open(brand.nametag_template)
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("arial.ttf", 24)  # Adjust font/size
            draw.text((50, 50), f"{strain.name} - {strain.type}", fill="black", font=font)  # Positions customizable
            draw.text((50, 100), f"THC: {strain.thc_percent}%", fill="black", font=font)
            img.save('output/nametag.png')  # Preview/download

        # Similar for pricetag (add price logic later)

        print("Labels generated: nametag.png, pricetag.png")  # TODO: Preview in GUI

    def configure_brand(self, brand):
        c = self.db_conn.cursor()
        c.execute("INSERT INTO brands (name, category, nametag_template, pricetag_template) VALUES (?, ?, ?, ?)",
                  (brand.name, brand.category, brand.nametag_template, brand.pricetag_template))
        self.db_conn.commit()

# Main (CLI example; add Tkinter GUI next)
if __name__ == "__main__":
    conn = init_db()
    gen = LabelGenerator(conn)

    # Example usage
    strain = Strain("Sativa", "Blue Dream", "BUA123", "Energizing", "Organic", 20.5)
    brand = Brand("ExampleBrand", "REC")
    brand.nametag_template = "templates/rec_green_nametag.png"  # Upload here
    gen.configure_brand(brand)  # Admin config
    gen.generate_labels(strain, "ExampleBrand", "Green", "Flower")  # Generate