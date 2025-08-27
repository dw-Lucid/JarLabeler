import os
import subprocess  # For improved PDF opening
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black
from reportlab.lib.utils import ImageReader  # For accurate logo sizing
from models import Strain
from tkinter import messagebox
import json  # For parsing prices

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
            inner_margin = 0.1 * inch  # Border padding
            # Debug prints for logo and prices
            print(f"Logo path for tier '{tier['name']}': {tier.get('nametag_logo_path', 'None')}")
            if tier.get('nametag_logo_path'):
                print(f"Logo file exists: {os.path.exists(tier['nametag_logo_path'])}")
            print(f"Raw prices for tier '{tier['name']}': {tier.get('prices', 'None')}")
            # Nametag full generation
            center_x = x_left + label_width / 2
            y_current = y - inner_margin  # Start inside top border
            available_height = label_height - 0.2 * inch  # Padding
            header_height = 0
            logo_drawn = False
            # Logo (from tier, left-aligned)
            logo_path = tier.get('nametag_logo_path')
            if logo_path:
                try:
                    img = ImageReader(logo_path)
                    img_width, img_height = img.getSize()
                    logo_aspect = img_width / img_height if img_height else 1.0
                    logo_width = min(0.8 * inch, label_width * 0.25)
                    logo_height = logo_width / logo_aspect
                    logo_height = min(logo_height, available_height * 0.2)
                    logo_width = logo_height * logo_aspect
                    logo_x = x_left + inner_margin
                    pdf.drawImage(logo_path, logo_x, y_current - logo_height, width=logo_width, height=logo_height, mask='auto')
                    # Brand name next to logo
                    pdf.setFillColor(black)
                    pdf.setFont("Helvetica-Bold", 14)  # Reduced size
                    brand_text = brand['name']
                    brand_x = logo_x + logo_width + 0.1 * inch
                    brand_width = pdf.stringWidth(brand_text)
                    brand_height = pdf._leading
                    brand_y = y_current - logo_height + (logo_height - brand_height) / 2  # Vertically center
                    pdf.drawString(brand_x, brand_y, brand_text)
                    header_height = max(logo_height, brand_height)
                    logo_drawn = True
                except Exception as e:
                    print(f"Error loading/drawing logo: {e}. Falling back to text-only header.")
            if not logo_drawn:
                # No logo or error: Center brand
                pdf.setFillColor(black)
                pdf.setFont("Helvetica-Bold", 14)
                brand_text = brand['name']
                pdf.drawCentredString(center_x, y_current, brand_text)
                header_height = 0.3 * inch  # Increased for better spacing
            y_current -= header_height + 0.2 * inch  # Increased space after header
            # Tier name (subheader)
            pdf.setFont("Helvetica-Bold", 12)
            tier_text = tier['name']
            pdf.drawCentredString(center_x, y_current, tier_text)
            y_current -= 0.3 * inch  # Increased spacing
            # Strain bold/large
            pdf.setFont("Helvetica-Bold", 18)  # Reduced start size
            strain_text = strain.name
            strain_width = pdf.stringWidth(strain_text)
            max_strain_width = label_width - 2 * inner_margin
            while strain_width > max_strain_width and pdf._fontsize > 10:
                pdf.setFont("Helvetica-Bold", pdf._fontsize - 1)
                strain_width = pdf.stringWidth(strain_text)
            pdf.drawCentredString(center_x, y_current, strain_text)
            # Underline strain
            underline_y = y_current - 0.05 * inch
            pdf.line(center_x - strain_width / 2, underline_y, center_x + strain_width / 2, underline_y)
            y_current -= pdf._leading + 0.2 * inch  # Increased
            # Lineage
            pdf.setFont("Helvetica", 10)
            if strain.lineage:
                lineage_text = f"({strain.lineage})"
                pdf.drawCentredString(center_x, y_current, lineage_text)
                y_current -= 0.2 * inch  # Increased
            # Classification
            pdf.setFont("Helvetica", 12)  # Regular
            pdf.drawCentredString(center_x, y_current, strain.classification)
            y_current -= 0.2 * inch
            # THC
            thc_text = f"THC: {strain.thc_percent:.2f}%"
            pdf.drawCentredString(center_x, y_current, thc_text)
            # Pricetag full generation (always draw headers)
            p_center_x = x_left + label_width + label_width / 2
            p_y_current = y - inner_margin  # Align start with nametag
            pdf.setFillColor(black)
            # Brand header
            pdf.setFont("Helvetica-Bold", 14)  # Match nametag
            brand_text = brand['name']
            brand_width = pdf.stringWidth(brand_text)
            pdf.drawCentredString(p_center_x, p_y_current, brand_text)
            # Underline brand
            underline_y = p_y_current - 0.05 * inch
            pdf.line(p_center_x - brand_width / 2, underline_y, p_center_x + brand_width / 2, underline_y)
            p_y_current -= 0.3 * inch  # Increased
            # Tier subheader
            pdf.setFont("Helvetica-Bold", 12)
            tier_text = tier['name']
            tier_width = pdf.stringWidth(tier_text)
            pdf.drawCentredString(p_center_x, p_y_current, tier_text)
            # Underline tier
            underline_y = p_y_current - 0.05 * inch
            pdf.line(p_center_x - tier_width / 2, underline_y, p_center_x + tier_width / 2, underline_y)
            p_y_current -= 0.3 * inch
            # Prices (bold)
            pdf.setFont("Helvetica-Bold", 14)
            prices_str = tier.get('prices', '{}')
            if isinstance(prices_str, str):
                try:
                    prices = json.loads(prices_str)
                except json.JSONDecodeError as e:
                    print(f"Prices JSON decode error: {e}. Using empty prices.")
                    prices = {}
            else:
                prices = prices_str if isinstance(prices_str, dict) else {}
            def format_price(weight, price):
                if price:
                    return f"{weight}-${price}"
                return ''
            # Draw lines even if empty to reserve space
            line1_left = format_price('1g', prices.get('1g', ''))
            line1_right = format_price('3.5g', prices.get('3.5g', ''))
            line1 = '   '.join(filter(None, [line1_left, line1_right]))  # Triple space
            pdf.drawCentredString(p_center_x, p_y_current, line1 or '')  # Draw even empty
            p_y_current -= 0.25 * inch
            line2_left = format_price('7g', prices.get('7g', ''))
            line2_right = format_price('14g', prices.get('14g', ''))
            line2 = '   '.join(filter(None, [line2_left, line2_right]))
            if line2 or not prices:  # Draw if content or empty prices
                pdf.drawCentredString(p_center_x, p_y_current, line2)
                p_y_current -= 0.25 * inch
            line3 = format_price('28g', prices.get('28g', ''))
            if line3 or not prices:
                pdf.drawCentredString(p_center_x, p_y_current, line3)
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