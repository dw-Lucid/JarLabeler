from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

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
        pair_width = 7 * inch  # Full pair width
        pair_height = 2.5 * inch  # Full pair height (with some buffer)
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
            # ... PDF drawing logic ...
        pdf.save()
        return pdf_path
