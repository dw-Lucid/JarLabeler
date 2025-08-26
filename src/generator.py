from tkinter import messagebox
import os
import subprocess  # For improved PDF opening
# import webbrowser  # Alternative fallback (uncomment if needed)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from PyPDF2 import PdfReader, PdfWriter
from models import Strain

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
            strain = item['strain']
            label_width = 3.5 * inch  # Each label width
            label_height = 2.25 * inch  # Each label height
            inner_margin = 0.2 * inch  # Increased for better overlap avoidance
            # Optional backgrounds (support JPG/PNG/PDF)
            if tier['nametag_bg_path'] and os.path.exists(tier['nametag_bg_path']):
                print(f"Loading nametag template: {tier['nametag_bg_path']}")  # Debug
                if tier['nametag_bg_path'].lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, tier['nametag_bg_path'], x_left, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(tier['nametag_bg_path'], x_left, y - pair_height, width=label_width, height=label_height)
            x_p = x_left + label_width
            if tier['pricetag_bg_path'] and os.path.exists(tier['pricetag_bg_path']):
                print(f"Loading pricetag template: {tier['pricetag_bg_path']}")  # Debug
                if tier['pricetag_bg_path'].lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, tier['pricetag_bg_path'], x_p, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(tier['pricetag_bg_path'], x_p, y - pair_height, width=label_width, height=label_height)
            # Nametag overlays: Dynamic positioning for centering and even spacing, no tier
            center_x = x_left + label_width / 2
            y_bottom = (y - pair_height) + inner_margin  # Bottom of label
            y_top = y - inner_margin - (tier.get('nametag_top_margin', 0.5) * inch)  # Dynamic top margin from DB
            available_height = label_height - 2 * inner_margin - (tier.get('nametag_top_margin', 0.5) * inch)
            # Define elements and their properties
            elements = []
            # Logo (optional)
            logo_height = 0
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_width = min(1.5 * inch, label_width * 0.4)  # Max 40% width
                logo_aspect = 1.0  # Assume square; can calculate if needed
                logo_height = logo_width / logo_aspect
                logo_height = min(logo_height, available_height * 0.3)  # Cap at 30% height
                elements.append(('logo', logo_height))
            # Strain (may wrap or resize)
            strain_font_size = 24
            pdf.setFont("Helvetica-Bold", strain_font_size)
            strain_text = strain.name.upper()
            strain_width = pdf.stringWidth(strain_text)
            max_strain_width = label_width - 2 * inner_margin
            if strain_width > max_strain_width:
                # Reduce font size
                while strain_width > max_strain_width and strain_font_size > 12:
                    strain_font_size -= 1
                    pdf.setFont("Helvetica-Bold", strain_font_size)
                    strain_width = pdf.stringWidth(strain_text)
            strain_height = pdf._leading
            elements.append(('strain', strain_height))
            # Lineage (optional)
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
            # Calculate total content height
            total_content_height = sum(h for _, h in elements) + (len(elements) - 1) * 0.1 * inch  # Spacing between elements
            if logo_height > 0:
                total_content_height += 0.2 * inch  # Extra space after logo
            # Compress spacing if content is tight
            spacing = 0.1 * inch if total_content_height < available_height * 0.8 else 0.05 * inch
            # Adjust for top-down drawing
            y_current = y_top - logo_height  # Start from adjusted top
            # Draw logo
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_x = center_x - (logo_width / 2)
                pdf.drawImage(brand['logo_path'], logo_x, y_current, width=logo_width, height=logo_height, mask='auto')
                y_current -= logo_height + 0.2 * inch  # Space after logo
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
            # Pricetag overlays (none, just background for now; add prices later if needed)
        pdf.save()
        print(f"PDF saved at: {os.path.abspath(pdf_path)}")  # Debug
        if os.path.exists(pdf_path):
            print("File exists and size:", os.path.getsize(pdf_path))
        else:
            print("File not created!")
        self.queue.clear()  # Reset queue
        abs_path = os.path.abspath(pdf_path)
        try:
            if os.name == 'posix':  # Mac/Linux
                subprocess.call(['open', abs_path])
            elif os.name == 'nt':  # Windows
                subprocess.call(['start', abs_path], shell=True)
            # Alternative: Uncomment for webbrowser fallback
            # webbrowser.open(f"file://{abs_path}")
        except Exception as e:
            print(f"Failed to open PDF: {e}")  # Log error
            messagebox.showerror("Open Failed", f"PDF generated at {abs_path}, but couldn't auto-open: {e}. Open manually in Finder/Explorer.")
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