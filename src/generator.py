import os
import subprocess  # For improved PDF opening
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from PyPDF2 import PdfReader, PdfWriter
from models import Strain
from tkinter import messagebox

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
        pair_height = 2.25 * inch  # Match label height, reduced buffer for top placement
        pairs_per_page = 4  # Like template (2 rows x 2 columns, but logic is vertical stacking)
        x_left = margin
        y_start = height - margin  # Start higher on page for first pair
        for i, item in enumerate(self.queue):
            if i > 0 and i % pairs_per_page == 0:
                pdf.showPage()
                y = height - margin
            else:
                y = y_start - (i % pairs_per_page) * pair_height * 1.05  # Reduced multiplier for tighter top placement
            brand = item['brand']
            tier = item['tier']
            strain = item['strain']
            label_width = 3.5 * inch  # Each label width
            label_height = 2.25 * inch  # Each label height
            inner_margin = 0.3 * inch  # Increased to avoid overlaps
            # Optional backgrounds
            if tier['nametag_bg_path'] and os.path.exists(tier['nametag_bg_path']):
                print(f"Loading nametag template: {tier['nametag_bg_path']}")
                if tier['nametag_bg_path'].lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, tier['nametag_bg_path'], x_left, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(tier['nametag_bg_path'], x_left, y - pair_height, width=label_width, height=label_height)
            x_p = x_left + label_width
            if tier['pricetag_bg_path'] and os.path.exists(tier['pricetag_bg_path']):
                print(f"Loading pricetag template: {tier['pricetag_bg_path']}")
                if tier['pricetag_bg_path'].lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, tier['pricetag_bg_path'], x_p, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(tier['pricetag_bg_path'], x_p, y - pair_height, width=label_width, height=label_height)
            # Nametag overlays: Dynamic positioning
            center_x = x_left + label_width / 2
            y_bottom = (y - pair_height) + inner_margin
            y_top = y - inner_margin - (tier.get('nametag_top_margin', 0.5) * inch)  # Dynamic skip for template content
            available_height = label_height - 2 * inner_margin - (tier.get('nametag_top_margin', 0.5) * inch)
            elements = []
            # Logo (optional)
            logo_height = 0
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_width = min(1.5 * inch, label_width * 0.4)
                logo_aspect = 1.0
                logo_height = logo_width / logo_aspect
                logo_height = min(logo_height, available_height * 0.3)
                elements.append(('logo', logo_height))
            # Strain
            strain_font_size = 24
            pdf.setFont("Helvetica-Bold", strain_font_size)
            strain_text = strain.name.upper()
            strain_width = pdf.stringWidth(strain_text)
            max_strain_width = label_width - 2 * inner_margin
            if strain_width > max_strain_width:
                while strain_width > max_strain_width and strain_font_size > 12:
                    strain_font_size -= 1
                    pdf.setFont("Helvetica-Bold", strain_font_size)
                    strain_width = pdf.stringWidth(strain_text)
            strain_height = pdf._leading
            elements.append(('strain', strain_height))
            # Lineage
            lineage_height = 0
            if strain.lineage:
                pdf.setFont("Helvetica", 12)
                lineage_text = f"({strain.lineage})"
                lineage_height = pdf._leading
                elements.append(('lineage', lineage_height))
            # Classification
            pdf.setFont("Helvetica", 12)
            class_text = strain.classification
            class_height = pdf._leading
            elements.append(('classification', class_height))
            # THC
            thc_text = f"THC: {strain.thc_percent:g}%"
            thc_height = pdf._leading
            elements.append(('thc', thc_height))
            # Total height and spacing compression
            total_content_height = sum(h for _, h in elements) + (len(elements) - 1) * 0.1 * inch
            if logo_height > 0:
                total_content_height += 0.2 * inch
            spacing = 0.1 * inch if total_content_height < available_height * 0.8 else 0.05 * inch
            y_current = y_top - logo_height
            # Draw logo
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_x = center_x - (logo_width / 2)
                pdf.drawImage(brand['logo_path'], logo_x, y_current, width=logo_width, height=logo_height, mask='auto')
                y_current -= logo_height + 0.2 * inch
            # Draw strain
            pdf.setFont("Helvetica-Bold", strain_font_size)
            pdf.drawCentredString(center_x, y_current, strain_text)
            y_current -= strain_height + spacing
            # Draw lineage
            pdf.setFont("Helvetica", 12)
            if strain.lineage:
                pdf.drawCentredString(center_x, y_current, lineage_text)
                y_current -= lineage_height + spacing
            # Draw classification
            pdf.drawCentredString(center_x, y_current, class_text)
            y_current -= class_height + spacing
            # Draw THC
            pdf.drawCentredString(center_x, y_current, thc_text)
        pdf.save()
        print(f"PDF saved at: {os.path.abspath(pdf_path)}")  # Debug
        if os.path.exists(pdf_path):
            print("File exists and size:", os.path.getsize(pdf_path))
        else:
            print("File not created!")
        self.queue.clear()
        abs_path = os.path.abspath(pdf_path)
        try:
            if os.name == 'posix':
                subprocess.call(['open', abs_path])
            elif os.name == 'nt':
                subprocess.call(['start', abs_path], shell=True)
        except Exception as e:
            print(f"Failed to open PDF: {e}")
            messagebox.showerror("Open Failed", f"PDF at {abs_path}; error: {e}. Open manually.")
        return pdf_path

    def _overlay_pdf_background(self, canvas, pdf_path, x, y, w, h):
        reader = PdfReader(pdf_path)
        page = reader.pages[0]
        writer = PdfWriter()
        writer.add_page(page)
        temp_pdf = "temp.pdf"
        with open(temp_pdf, "wb") as f:
            writer.write(f)
        canvas.drawImage(temp_pdf, x, y, width=w, height=h)
        os.remove(temp_pdf)