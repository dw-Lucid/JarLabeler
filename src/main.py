import sqlite3
import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black

CLASSIFICATIONS = ["Sativa", "Sativa Hybrid", "Hybrid", "Indica Hybrid", "Indica"]

# Database setup
def init_db():
    os.makedirs('db', exist_ok=True)
    conn = sqlite3.connect('db/jarlabeler.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS brands
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, logo_path TEXT,
                  UNIQUE(name, category))''')
    c.execute('''CREATE TABLE IF NOT EXISTS tiers
                 (id INTEGER PRIMARY KEY, brand_id INTEGER, name TEXT, nametag_bg_path TEXT, pricetag_bg_path TEXT)''')
    conn.commit()
    return conn

class Strain:
    def __init__(self, name, classification, thc_percent, lineage=''):
        self.name = name
        self.classification = classification
        self.thc_percent = thc_percent
        self.lineage = lineage

class LabelGenerator:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.queue = []  # List of dicts: {'strain': Strain, 'brand': dict, 'tier': dict}

    def add_to_queue(self, strain, brand, tier):
        self.queue.append({'strain': strain, 'brand': brand, 'tier': tier})

    def remove_from_queue(self, index):
        if 0 <= index < len(self.queue):
            del self.queue[index]

    def get_queue_summary(self):
        return [f"{item['brand']['category']} - {item['brand']['name']} - {item['tier']['name']} - Strain: {item['strain'].name} ({item['strain'].classification}, THC {item['strain'].thc_percent}%, Lineage: {item['strain'].lineage or 'None'})" for item in self.queue]

    def generate_pdf(self):
        if not self.queue:
            raise ValueError("Queue is empty. Add pairs first.")
        os.makedirs('output', exist_ok=True)
        pdf_path = os.path.join('output', 'labels.pdf')
        pdf = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        margin = 0.5 * inch
        pair_width = width - 2 * margin
        pair_height = 1.25 * inch
        pairs_per_page = 4  # Like template
        x_left = margin
        y_start = height - margin - pair_height

        for i, item in enumerate(self.queue):
            if i > 0 and i % pairs_per_page == 0:
                pdf.showPage()
                y = height - margin - pair_height
            else:
                y = y_start - (i % pairs_per_page) * pair_height * 1.1  # Spacing

            brand = item['brand']
            tier = item['tier']
            strain = item['strain']
            nametag_width = 4 * inch
            pricetag_width = 3 * inch

            # Optional backgrounds
            if tier['nametag_bg_path'] and os.path.exists(tier['nametag_bg_path']):
                pdf.drawImage(tier['nametag_bg_path'], x_left, y - pair_height, width=nametag_width, height=pair_height)
            if tier['pricetag_bg_path'] and os.path.exists(tier['pricetag_bg_path']):
                pdf.drawImage(tier['pricetag_bg_path'], x_left + nametag_width + 0.2 * inch, y - pair_height, width=pricetag_width, height=pair_height)

            # Nametag content
            x_n = x_left + 0.1 * inch
            y_n = y - 0.2 * inch
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                pdf.drawImage(brand['logo_path'], x_n, y_n - 0.5 * inch, width=1 * inch, height=0.5 * inch, mask='auto')
            y_n -= 0.6 * inch

            if brand['category'] == 'MED':
                pdf.setFillColor(black)
                pdf.setFont("Helvetica-Bold", 18)
                pdf.drawString(x_n, y_n, f"{tier['name'].upper()} TIER")
                y_n -= 0.3 * inch

            pdf.setFillColor(black)
            pdf.setFont("Helvetica-Bold", 24)
            pdf.drawString(x_n, y_n, strain.name.upper())
            y_n -= 0.1 * inch

            if brand['category'] == 'REC':
                pdf.line(x_n, y_n, x_n + nametag_width - 0.5 * inch, y_n)
            y_n -= 0.2 * inch

            pdf.setFont("Helvetica", 12)
            if strain.lineage:
                pdf.drawString(x_n, y_n, f"({strain.lineage})")
                y_n -= 0.3 * inch

            pdf.drawString(x_n, y_n, strain.classification)
            y_n -= 0.3 * inch if strain.lineage else 0  # Shift up if no lineage

            pdf.drawString(x_n, y_n, f"THC: {strain.thc_percent}%")

            # Pricetag content
            x_p = x_left + nametag_width + 0.3 * inch
            y_p = y - 0.2 * inch
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(x_p, y_p, brand['name'].upper())
            y_p -= 0.3 * inch

            if brand['category'] == 'MED':
                pdf.setFillColor(black)
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(x_p, y_p, f"{tier['name'].upper()} TIER")
                pdf.line(x_p, y_p - 0.05 * inch, x_p + pricetag_width - 0.5 * inch, y_p - 0.05 * inch)
                y_p -= 0.3 * inch
            pdf.setFillColor(black)

        pdf.save()
        self.queue.clear()  # Reset queue
        if os.name == 'posix':
            os.system(f"open '{pdf_path}'")
        elif os.name == 'nt':
            os.system(f"start '{pdf_path}'")
        return pdf_path

class JarLabelerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JarLabeler")
        self.db_conn = init_db()
        self.gen = LabelGenerator(self.db_conn)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        # Main Generation Tab
        self.gen_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gen_frame, text='Generate Labels')

        tk.Label(self.gen_frame, text="Category").pack()
        self.category_combo = ttk.Combobox(self.gen_frame, values=["REC", "MED"])
        self.category_combo.pack()
        self.category_combo.bind("<<ComboboxSelected>>", self.update_brands)

        tk.Label(self.gen_frame, text="Brand").pack()
        self.brand_combo = ttk.Combobox(self.gen_frame)
        self.brand_combo.pack()
        self.brand_combo.bind("<<ComboboxSelected>>", self.update_tiers)

        tk.Label(self.gen_frame, text="Pricing Tier").pack()
        self.tier_combo = ttk.Combobox(self.gen_frame)
        self.tier_combo.pack()

        tk.Label(self.gen_frame, text="Strain Name").pack()
        self.name_entry = tk.Entry(self.gen_frame)
        self.name_entry.pack()

        tk.Label(self.gen_frame, text="Classification").pack()
        self.class_combo = ttk.Combobox(self.gen_frame, values=CLASSIFICATIONS)
        self.class_combo.pack()

        tk.Label(self.gen_frame, text="Lineage (optional)").pack()
        self.lineage_entry = tk.Entry(self.gen_frame)
        self.lineage_entry.pack()

        tk.Label(self.gen_frame, text="THC %").pack()
        self.thc_entry = tk.Entry(self.gen_frame)
        self.thc_entry.pack()

        tk.Button(self.gen_frame, text="Add Pair to Queue", command=self.add_to_queue).pack()

        # Queue preview section
        self.queue_frame = ttk.LabelFrame(self.gen_frame, text='Label Queue Preview')
        self.queue_frame.pack(fill='x', pady=10)
        self.queue_list = tk.Listbox(self.queue_frame, height=5)
        self.queue_list.pack(fill='x')
        tk.Button(self.queue_frame, text="Delete Selected from Queue", command=self.delete_from_queue).pack()

        tk.Button(self.gen_frame, text="Generate PDF from Queue", command=self.generate_pdf).pack()

        # Configuration Tab
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text='Configuration')

        # Grouped brand lists
        self.rec_frame = ttk.LabelFrame(self.config_frame, text='REC Brands')
        self.rec_frame.grid(row=0, column=0, padx=10, pady=10, sticky='ns')
        self.rec_list = tk.Listbox(self.rec_frame)
        self.rec_list.pack(fill='both', expand=True)
        self.rec_list.bind('<<ListboxSelect>>', lambda e: self.show_brand_details('REC'))
        tk.Button(self.rec_frame, text="Delete Brand", command=self.delete_brand).pack()

        self.med_frame = ttk.LabelFrame(self.config_frame, text='MED Brands')
        self.med_frame.grid(row=0, column=1, padx=10, pady=10, sticky='ns')
        self.med_list = tk.Listbox(self.med_frame)
        self.med_list.pack(fill='both', expand=True)
        self.med_list.bind('<<ListboxSelect>>', lambda e: self.show_brand_details('MED'))
        tk.Button(self.med_frame, text="Delete Brand", command=self.delete_brand).pack()

        # Tiers frame for selected brand
        self.tiers_frame = ttk.LabelFrame(self.config_frame, text='Brand Tiers')
        self.tiers_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky='ns')
        self.tiers_frame.grid_remove()  # Hide until brand selected
        self.tier_list = tk.Listbox(self.tiers_frame)
        self.tier_list.pack(fill='both', expand=True)
        self.tier_list.bind('<<ListboxSelect>>', self.show_tier_details)
        tk.Button(self.tiers_frame, text="Add Tier", command=self.open_add_tier_window).pack()
        tk.Button(self.tiers_frame, text="Edit Tier", command=self.open_edit_tier_window).pack()
        tk.Button(self.tiers_frame, text="Delete Tier", command=self.delete_tier).pack()

        # Sub-frame for selected tier details (hidden initially)
        self.tier_details_frame = ttk.LabelFrame(self.tiers_frame, text='Tier Templates')
        self.tier_details_frame.pack(fill='x', pady=5)
        self.tier_details_frame.pack_forget()  # Hide until tier selected
        self.nametag_path_label = tk.Label(self.tier_details_frame, text="Nametag JPG: None")
        self.nametag_path_label.pack()
        tk.Button(self.tier_details_frame, text="Upload/Replace Nametag JPG", command=self.upload_nametag_for_tier).pack()
        self.pricetag_path_label = tk.Label(self.tier_details_frame, text="Pricetag JPG: None")
        self.pricetag_path_label.pack()
        tk.Button(self.tier_details_frame, text="Upload/Replace Pricetag JPG", command=self.upload_pricetag_for_tier).pack()

        # Create new brand button
        tk.Button(self.config_frame, text="Create New Brand", command=self.open_new_brand_window).grid(row=1, column=0, columnspan=2, pady=10)

        self.selected_brand_id = None
        self.selected_tier_id = None
        self.selected_category = None  # To track for delete
        self.refresh_brand_lists()
        self.refresh_queue_list()  # Initial refresh

    def refresh_brand_lists(self):
        self.rec_list.delete(0, tk.END)
        self.med_list.delete(0, tk.END)
        c = self.db_conn.cursor()
        c.execute("SELECT id, name FROM brands WHERE category='REC'")
        for row in c.fetchall():
            self.rec_list.insert(tk.END, row[1])
        c.execute("SELECT id, name FROM brands WHERE category='MED'")
        for row in c.fetchall():
            self.med_list.insert(tk.END, row[1])

    def show_brand_details(self, category):
        if category == 'REC':
            sel = self.rec_list.curselection()
            listbox = self.rec_list
        else:
            sel = self.med_list.curselection()
            listbox = self.med_list
        if not sel:
            return
        brand_name = listbox.get(sel[0])
        c = self.db_conn.cursor()
        c.execute("SELECT id FROM brands WHERE name=? AND category=?", (brand_name, category))
        self.selected_brand_id = c.fetchone()[0]
        self.selected_category = category  # Track for delete
        self.refresh_tier_list()
        self.tiers_frame.grid()  # Show the frame
        self.tier_details_frame.pack_forget()  # Reset tier details
        self.selected_tier_id = None

    def refresh_tier_list(self):
        self.tier_list.delete(0, tk.END)
        if self.selected_brand_id:
            c = self.db_conn.cursor()
            c.execute("SELECT id, name FROM tiers WHERE brand_id=?", (self.selected_brand_id,))
            for row in c.fetchall():
                self.tier_list.insert(tk.END, row[1])

    def show_tier_details(self, event=None):
        sel = self.tier_list.curselection()
        if not sel:
            return
        tier_name = self.tier_list.get(sel[0])
        c = self.db_conn.cursor()
        c.execute("SELECT id, nametag_bg_path, pricetag_bg_path FROM tiers WHERE brand_id=? AND name=?", 
                  (self.selected_brand_id, tier_name))
        data = c.fetchone()
        self.selected_tier_id = data[0]
        self.nametag_path_label['text'] = f"Nametag JPG: {data[1] or 'None'}"
        self.pricetag_path_label['text'] = f"Pricetag JPG: {data[2] or 'None'}"
        self.tier_details_frame.pack()  # Show sub-frame

    def upload_nametag_for_tier(self):
        if not self.selected_tier_id:
            messagebox.showerror("Error", "Select a tier first.")
            return
        file_path = filedialog.askopenfilename(title="Upload Nametag JPG", filetypes=[("JPG Images", "*.jpg")])
        if file_path:
            dest = os.path.join('templates', os.path.basename(file_path))
            os.makedirs('templates', exist_ok=True)
            cmd = f"cp '{file_path}' '{dest}'" if os.name == 'posix' else f"copy \"{file_path}\" \"{dest}\""
            os.system(cmd)
            c = self.db_conn.cursor()
            c.execute("UPDATE tiers SET nametag_bg_path=? WHERE id=?", (dest, self.selected_tier_id))
            self.db_conn.commit()
            self.nametag_path_label['text'] = f"Nametag JPG: {dest}"
            messagebox.showinfo("Uploaded", f"Nametag updated to {dest}.")

    def upload_pricetag_for_tier(self):
        if not self.selected_tier_id:
            messagebox.showerror("Error", "Select a tier first.")
            return
        file_path = filedialog.askopenfilename(title="Upload Pricetag JPG", filetypes=[("JPG Images", "*.jpg")])
        if file_path:
            dest = os.path.join('templates', os.path.basename(file_path))
            os.makedirs('templates', exist_ok=True)
            cmd = f"cp '{file_path}' '{dest}'" if os.name == 'posix' else f"copy \"{file_path}\" \"{dest}\""
            os.system(cmd)
            c = self.db_conn.cursor()
            c.execute("UPDATE tiers SET pricetag_bg_path=? WHERE id=?", (dest, self.selected_tier_id))
            self.db_conn.commit()
            self.pricetag_path_label['text'] = f"Pricetag JPG: {dest}"
            messagebox.showinfo("Uploaded", f"Pricetag updated to {dest}.")

    def open_new_brand_window(self):
        win = tk.Toplevel(self.root)
        win.title("Create New Brand")

        tk.Label(win, text="Category").pack()
        cat_combo = ttk.Combobox(win, values=["REC", "MED"])
        cat_combo.pack()

        tk.Label(win, text="Brand Name").pack()
        name_entry = tk.Entry(win)
        name_entry.pack()

        logo_path = [None]  # Mutable list for path
        tk.Button(win, text="Upload Logo (optional)", command=lambda: self._upload_and_set(logo_path, logo_label, "Logo")).pack()
        logo_label = tk.Label(win, text="No logo")
        logo_label.pack()

        def save_brand():
            category = cat_combo.get()
            name = name_entry.get()
            if not (category and name):
                messagebox.showerror("Error", "Category and name required.")
                return
            c = self.db_conn.cursor()
            try:
                c.execute("INSERT INTO brands (name, category, logo_path) VALUES (?, ?, ?)",
                          (name, category, logo_path[0]))
                self.db_conn.commit()
                self.refresh_brand_lists()
                self.update_brands()  # Refresh main tab
                messagebox.showinfo("Success", f"Brand {name} created.")
                win.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Brand name must be unique within category.")

        tk.Button(win, text="Save Brand", command=save_brand).pack()

    def open_add_tier_window(self):
        if not self.selected_brand_id:
            messagebox.showerror("Error", "Select a brand first.")
            return
        self._open_tier_window("Add Tier")

    def open_edit_tier_window(self):
        sel = self.tier_list.curselection()
        if not sel or not self.selected_brand_id:
            messagebox.showerror("Error", "Select a tier and brand first.")
            return
        tier_name = self.tier_list.get(sel[0])
        c = self.db_conn.cursor()
        c.execute("SELECT name, nametag_bg_path, pricetag_bg_path FROM tiers WHERE brand_id=? AND name=?", 
                  (self.selected_brand_id, tier_name))
        data = c.fetchone()
        self._open_tier_window("Edit Tier", data)

    def _open_tier_window(self, title, data=None):
        win = tk.Toplevel(self.root)
        win.title(title)

        tk.Label(win, text="Tier Name").pack()
        name_entry = tk.Entry(win)
        name_entry.pack()

        nametag_path = [None]
        tk.Button(win, text="Upload Nametag JPG (optional)", command=lambda: self._upload_and_set(nametag_path, nametag_label, "Nametag JPG")).pack()
        nametag_label = tk.Label(win, text="No nametag")
        nametag_label.pack()

        pricetag_path = [None]
        tk.Button(win, text="Upload Pricetag JPG (optional)", command=lambda: self._upload_and_set(pricetag_path, pricetag_label, "Pricetag JPG")).pack()
        pricetag_label = tk.Label(win, text="No pricetag")
        pricetag_label.pack()

        if data:
            name_entry.insert(0, data[0])
            nametag_path[0] = data[1]
            pricetag_path[0] = data[2]
            nametag_label['text'] = data[1] or "No nametag"
            pricetag_label['text'] = data[2] or "No pricetag"

        def save_tier():
            name = name_entry.get()
            if not name:
                messagebox.showerror("Error", "Tier name required.")
                return
            c = self.db_conn.cursor()
            c.execute("INSERT OR REPLACE INTO tiers (brand_id, name, nametag_bg_path, pricetag_bg_path) VALUES (?, ?, ?, ?)",
                      (self.selected_brand_id, name, nametag_path[0], pricetag_path[0]))
            self.db_conn.commit()
            self.refresh_tier_list()
            self.update_tiers()  # Refresh main tab
            messagebox.showinfo("Success", f"Tier {name} {title.lower()}ed.")
            win.destroy()

        tk.Button(win, text="Save Tier", command=save_tier).pack()

    def _upload_and_set(self, path_list, label, title):
        file_path = filedialog.askopenfilename(title=f"Upload {title}", filetypes=[("JPG Images", "*.jpg")])
        if file_path:
            dest = os.path.join('templates', os.path.basename(file_path))
            os.makedirs('templates', exist_ok=True)
            cmd = f"cp '{file_path}' '{dest}'" if os.name == 'posix' else f"copy \"{file_path}\" \"{dest}\""
            os.system(cmd)
            path_list[0] = dest
            label['text'] = dest

    def update_brands(self, event=None):
        category = self.category_combo.get()
        if category:
            c = self.db_conn.cursor()
            c.execute("SELECT name FROM brands WHERE category=?", (category,))
            brands = [row[0] for row in c.fetchall()]
            self.brand_combo['values'] = brands
            self.brand_combo.set('')
            self.tier_combo.set('')
            self.tier_combo['values'] = []

    def update_tiers(self, event=None):
        brand_name = self.brand_combo.get()
        if brand_name:
            c = self.db_conn.cursor()
            c.execute("SELECT id FROM brands WHERE name=? AND category=?", (brand_name, self.category_combo.get()))
            brand_id_row = c.fetchone()
            if brand_id_row:
                brand_id = brand_id_row[0]
                c.execute("SELECT name FROM tiers WHERE brand_id=?", (brand_id,))
                tiers = [row[0] for row in c.fetchall()]
                self.tier_combo['values'] = tiers
                self.tier_combo.set('')
            else:
                self.tier_combo['values'] = []
                self.tier_combo.set('')

    def add_to_queue(self):
        try:
            category = self.category_combo.get()
            brand_name = self.brand_combo.get()
            tier_name = self.tier_combo.get()
            if not all([category, brand_name, tier_name, self.name_entry.get(), self.class_combo.get(), self.thc_entry.get()]):
                raise ValueError("All required fields must be filled.")
            thc = float(self.thc_entry.get())
            strain = Strain(self.name_entry.get(), self.class_combo.get(), thc, self.lineage_entry.get())

            c = self.db_conn.cursor()
            c.execute("SELECT * FROM brands WHERE name=? AND category=?", (brand_name, category))
            brand_data = c.fetchone()
            if brand_data:
                brand = {'id': brand_data[0], 'name': brand_data[1], 'category': brand_data[2], 'logo_path': brand_data[3]}
            else:
                raise ValueError("Brand not found for selected category.")

            c.execute("SELECT * FROM tiers WHERE brand_id=? AND name=?", (brand['id'], tier_name))
            tier_data = c.fetchone()
            if tier_data:
                tier = {'id': tier_data[0], 'name': tier_data[2], 'nametag_bg_path': tier_data[3], 'pricetag_bg_path': tier_data[4]}
            else:
                raise ValueError("Tier not found for selected brand.")

            self.gen.add_to_queue(strain, brand, tier)
            self.refresh_queue_list()
            messagebox.showinfo("Added", f"Pair added to queue (total: {len(self.gen.queue)})")
            # Clear inputs for next
            self.name_entry.delete(0, tk.END)
            self.lineage_entry.delete(0, tk.END)
            self.thc_entry.delete(0, tk.END)
            self.class_combo.set('')
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def refresh_queue_list(self):
        self.queue_list.delete(0, tk.END)
        for summary in self.gen.get_queue_summary():
            self.queue_list.insert(tk.END, summary)

    def delete_from_queue(self):
        sel = self.queue_list.curselection()
        if not sel:
            messagebox.showerror("Error", "Select a queue item to delete.")
            return
        index = sel[0]
        if messagebox.askyesno("Confirm", "Delete this queue item?"):
            self.gen.remove_from_queue(index)
            self.refresh_queue_list()

    def generate_pdf(self):
        try:
            pdf_path = self.gen.generate_pdf()
            self.refresh_queue_list()  # Clear preview after generation
            messagebox.showinfo("Success", f"PDF generated at {pdf_path}")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def delete_brand(self):
        category = 'REC' if self.rec_list.curselection() else 'MED' if self.med_list.curselection() else None
        if not category:
            messagebox.showerror("Error", "Select a brand to delete.")
            return
        listbox = self.rec_list if category == 'REC' else self.med_list
        sel = listbox.curselection()
        if not sel:
            return
        brand_name = listbox.get(sel[0])
        if messagebox.askyesno("Confirm", f"Delete brand {brand_name} and all its tiers?"):
            c = self.db_conn.cursor()
            c.execute("SELECT id FROM brands WHERE name=? AND category=?", (brand_name, category))
            brand_id = c.fetchone()[0]
            c.execute("DELETE FROM tiers WHERE brand_id=?", (brand_id,))
            c.execute("DELETE FROM brands WHERE id=?", (brand_id,))
            self.db_conn.commit()
            self.refresh_brand_lists()
            self.update_brands()
            self.tiers_frame.grid_remove()
            messagebox.showinfo("Deleted", f"Brand {brand_name} deleted.")

    def delete_tier(self):
        sel = self.tier_list.curselection()
        if not sel or not self.selected_brand_id:
            messagebox.showerror("Error", "Select a tier to delete.")
            return
        tier_name = self.tier_list.get(sel[0])
        if messagebox.askyesno("Confirm", f"Delete tier {tier_name}?"):
            c = self.db_conn.cursor()
            c.execute("DELETE FROM tiers WHERE brand_id=? AND name=?", (self.selected_brand_id, tier_name))
            self.db_conn.commit()
            self.refresh_tier_list()
            self.update_tiers()
            self.tier_details_frame.pack_forget()
            messagebox.showinfo("Deleted", f"Tier {tier_name} deleted.")

if __name__ == "__main__":
    root = tk.Tk()
    app = JarLabelerApp(root)
    root.mainloop()