import os
import subprocess  # For improved PDF opening
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, red
from PyPDF2 import PdfReader, PdfWriter
from models import Strain
from tkinter import messagebox
import pytesseract
from PIL import Image, ImageOps  # From Pillow
from pdf2image import convert_from_path  # For PDF to image conversion

pytesseract.pytesseract.tesseract_cmd = '/opt/local/bin/tesseract'  # MacPorts path

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
        pair_height = 2.25 * inch  # Match label height
        pairs_per_page = 4
        x_left = margin
        y_start = height - margin  # Start higher
        for i, item in enumerate(self.queue):
            if i > 0 and i % pairs_per_page == 0:
                pdf.showPage()
                y = height - margin
            else:
                y = y_start - (i % pairs_per_page) * pair_height * 1.05
            brand = item['brand']
            tier = item['tier']
            strain = item['strain']
            label_width = 3.5 * inch
            label_height = 2.25 * inch
            inner_margin = 0.4 * inch  # Increased to avoid overlaps
            # Backgrounds...
            nametag_bg_path = tier['nametag_bg_path']
            if nametag_bg_path and os.path.exists(nametag_bg_path):
                print(f"Loading nametag template: {nametag_bg_path}")
                if nametag_bg_path.lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, nametag_bg_path, x_left, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(nametag_bg_path, x_left, y - pair_height, width=label_width, height=label_height)
            x_p = x_left + label_width
            pricetag_bg_path = tier['pricetag_bg_path']
            if pricetag_bg_path and os.path.exists(pricetag_bg_path):
                print(f"Loading pricetag template: {pricetag_bg_path}")
                if pricetag_bg_path.lower().endswith('.pdf'):
                    self._overlay_pdf_background(pdf, pricetag_bg_path, x_p, y - pair_height, label_width, label_height)
                else:
                    pdf.drawImage(pricetag_bg_path, x_p, y - pair_height, width=label_width, height=label_height)
            # Nametag overlays
            center_x = x_left + label_width / 2
            y_bottom = (y - pair_height) + inner_margin
            # Use OCR to get dynamic top skip based on template content
            template_bottom_y = self._get_template_bottom_y(nametag_bg_path, label_height) if nametag_bg_path else 0
            y_top = y - inner_margin - max(tier.get('nametag_top_margin', 0.6) * inch, template_bottom_y + 0.5 * inch)  # Increased buffer
            available_height = label_height - 2 * inner_margin - max(tier.get('nametag_top_margin', 0.6) * inch, template_bottom_y) - 0.2 * inch  # Safety border padding
            elements = []
            logo_height = 0
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_width = min(1.5 * inch, label_width * 0.4)
                logo_aspect = 1.0
                logo_height = logo_width / logo_aspect
                logo_height = min(logo_height, available_height * 0.3)
                elements.append(('logo', logo_height))
            strain_font_size = 24
            pdf.setFont("Helvetica-Bold", strain_font_size)
            strain_text = strain.name.upper()
            strain_width = pdf.stringWidth(strain_text)
            max_strain_width = label_width - 2 * inner_margin
            while strain_width > max_strain_width and strain_font_size > 10:  # Lower min font to fit border
                strain_font_size -= 1
                pdf.setFont("Helvetica-Bold", strain_font_size)
                strain_width = pdf.stringWidth(strain_text)
            strain_height = pdf._leading
            elements.append(('strain', strain_height))
            lineage_height = 0
            if strain.lineage:
                pdf.setFont("Helvetica", 12)
                lineage_text = f"({strain.lineage})"
                lineage_height = pdf._leading
                elements.append(('lineage', lineage_height))
            pdf.setFont("Helvetica", 12)
            class_text = strain.classification
            class_height = pdf._leading
            elements.append(('classification', class_height))
            thc_text = f"THC: {strain.thc_percent:.2f}%"  # Fixed to 2 decimals like desired
            thc_height = pdf._leading
            elements.append(('thc', thc_height))
            total_content_height = sum(h for _, h in elements) + (len(elements) - 1) * 0.1 * inch
            if logo_height > 0:
                total_content_height += 0.2 * inch
            spacing = 0.1 * inch if total_content_height < available_height * 0.8 else 0.03 * inch  # Aggressive compression to fit border
            y_current = y_top - logo_height - 0.3 * inch  # Extra skip
            if brand['logo_path'] and os.path.exists(brand['logo_path']):
                logo_x = center_x - (logo_width / 2)
                pdf.drawImage(brand['logo_path'], logo_x, y_current, width=logo_width, height=logo_height, mask='auto')
                y_current -= logo_height + 0.2 * inch
            pdf.setFont("Helvetica-Bold", strain_font_size)
            pdf.drawCentredString(center_x, y_current, strain_text)
            y_current -= strain_height + spacing
            pdf.setFont("Helvetica", 12)
            if strain.lineage:
                pdf.drawCentredString(center_x, y_current, lineage_text)
                y_current -= lineage_height + spacing
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(center_x, y_current, class_text)
            y_current -= class_height + spacing
            pdf.drawCentredString(center_x, y_current, thc_text)
            # Pricetag overlays (add pricing; assume tier has 'prices' dict from ui, e.g., {'1g': '$2', '3.5g': '$5', ...}
            if pricetag_bg_path:
                p_center_x = x_p + label_width / 2
                p_y_current = y - inner_margin - 0.3 * inch  # Start below template header
                pdf.setFont("Helvetica-Bold", 14)
                pdf.setFillColor(red)
                pdf.drawCentredString(p_center_x, p_y_current, "NuHi")
                p_y_current -= 0.2 * inch
                pdf.drawCentredString(p_center_x, p_y_current, "RED Tier:")
                p_y_current -= 0.2 * inch
                pdf.setFillColor(black)
                pdf.setFont("Helvetica", 12)
                prices_left = ["1g $2", "7g $10", "28g $40"]
                prices_right = ["3.5g $5", "14g $20", "1LB - $600"]
                p_left_x = x_p + label_width / 4
                p_right_x = x_p + label_width * 3 / 4
                for left, right in zip(prices_left, prices_right):
                    pdf.drawCentredString(p_left_x, p_y_current, left)
                    pdf.drawCentredString(p_right_x, p_y_current, right)
                    p_y_current -= 0.15 * inch  # Tight spacing
        pdf.save()
        print(f"PDF saved at: {os.path.abspath(pdf_path)}")
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

    def _get_template_bottom_y(self, bg_path, label_height):
        """Use OCR to detect max bottom y of template content (in inches)."""
        try:
            # Load image (PNG/JPG or convert PDF to image)
            if bg_path.lower().endswith('.pdf'):
                img = convert_from_path(bg_path)[0]  # First page as image
            else:
                img = Image.open(bg_path)
            # Pre-process for better visual detection (grayscale, threshold to binary for edges)
            img = ImageOps.grayscale(img)
            img = img.point(lambda x: 0 if x < 128 else 255, '1')  # Binary threshold
            # Use pytesseract to get bounding boxes
            data = pytesseract.image_to_boxes(img, output_type=pytesseract.Output.DICT)
            if not data['bottom']:
                return 0  # No text detected
            max_bottom = max(data['bottom'])
            # Convert to inches (assume img height = label_height * 72 dpi for PDF scale)
            dpi = 72  # Standard PDF DPI
            max_bottom_inches = max_bottom / dpi
            print(f"Detected template bottom y: {max_bottom_inches}")  # Debug to console for testing
            return max_bottom_inches
        except Exception as e:
            print(f"OCR failed for {bg_path}: {e}")
            return 0  # Fallback

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