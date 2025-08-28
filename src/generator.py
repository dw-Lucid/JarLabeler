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
        label_width = 3.5 * inch
        label_height = 2.25 * inch
        pairs_per_page = 4
        x_left = margin
        y_start = height - margin
        for i, item in enumerate(self.queue):
            if i > 0 and i % pairs_per_page == 0:
                pdf.showPage()
                y = height - margin
            else:
                y = y_start - (i % pairs_per_page) * label_height * 1.05
            brand = item['brand']
            tier = item['tier']
            strain = item['strain']
            # Nametag
            center_x = x_left + label_width / 2
            y_top = y - 0.1 * inch
            # Prepare text elements
            # Determine tier color for medical labels
            tier_color = black
            if brand.get('category') == 'MED':
                color_map = {
                    'Green Tier': (0, 0.5, 0),
                    'Red Tier': (1, 0, 0),
                    'Yellow Tier': (1, 1, 0),
                    'Orange Tier': (1, 0.65, 0),
                    'Pink Tier': (1, 0.08, 0.58),
                    'Purple Tier': (0.5, 0, 0.5),
                }
                tier_color = color_map.get(tier.get('name'), black)
            text_elements = [
                ("Helvetica-Bold", 12, tier['name'].upper(), False, tier_color),
                ("Helvetica-Bold", 18, strain.name.upper(), True), # underline
            ]
            if strain.lineage:
                text_elements.append(("Helvetica", 10, f"({strain.lineage})"))
            text_elements.append(("Helvetica-Bold", 14, strain.classification))
            text_elements.append(("Helvetica-Bold", 14, f"THC: {strain.thc_percent:.2f}%"))
            # Estimate total text height
            total_text_height = 0
            for font, size, *_ in text_elements:
                pdf.setFont(font, size)
                total_text_height += pdf._leading + 0.08 * inch
            # Set max logo height so logo + text fits label
            available_height = label_height - 0.2 * inch
            max_logo_height = available_height * 0.35
            max_logo_width = label_width * 0.6
            logo_height_used = 0
            logo_path = tier.get('nametag_logo_path')
            if logo_path:
                abs_logo_path = os.path.abspath(logo_path)
                if os.path.exists(abs_logo_path):
                    try:
                        logo_img = ImageReader(abs_logo_path)
                        img_w, img_h = logo_img.getSize()
                        aspect = img_w / img_h
                        if aspect > 1:
                            logo_width = max_logo_width
                            logo_height = logo_width / aspect
                        else:
                            logo_height = max_logo_height
                            logo_width = logo_height * aspect
                        # If logo + text exceeds available height, shrink logo
                        if logo_height + total_text_height > available_height:
                            logo_height = available_height - total_text_height
                            logo_width = logo_height * aspect
                        logo_x = center_x - logo_width / 2
                        logo_y = y_top - logo_height
                        pdf.drawImage(logo_img, logo_x, logo_y, logo_width, logo_height, mask='auto')
                        logo_height_used = logo_height + 0.12 * inch
                    except Exception as e:
                        print(f"Tier logo error: {e}")
                else:
                    print(f"Tier logo file not found: {abs_logo_path}")
            else:
                logo_height_used = 0.3 * inch
            # Add extra space between logo and first text line
            gap_after_logo = 0.18 * inch
            y_current = y_top - logo_height_used - gap_after_logo
            for elem in text_elements:
                font, size, text = elem[:3]
                underline = elem[3] if len(elem) > 3 else False
                color = elem[4] if len(elem) > 4 else black
                pdf.setFont(font, size)
                if color != black:
                    pdf.setFillColorRGB(*color)
                pdf.drawCentredString(center_x, y_current, text)
                pdf.setFillColor(black)
                if underline:
                    text_width = pdf.stringWidth(text)
                    underline_y = y_current - 0.05 * inch
                    pdf.line(center_x - text_width / 2, underline_y, center_x + text_width / 2, underline_y)
                y_current -= pdf._leading + 0.08 * inch
            prices = tier.get('prices', {})
            def format_price(weight, price):
                if price:
                    return f"{weight}-${price}"
                return ''
            # Pricetag: evenly distribute elements to fill right half
            p_center_x = x_left + label_width + label_width / 2
            p_top = y - 0.1 * inch
            p_bottom = y - label_height + 0.1 * inch
            price_lines = [
                ("Helvetica-Bold", 18, brand['name'].upper(), True), # underline
                ("Helvetica-Bold", 14, tier['name'].upper(), True), # underline
                ("Helvetica-Bold", 16, '   '.join(filter(None, [format_price('1g', prices.get('1g')), format_price('3.5g', prices.get('3.5g'))]))),
                ("Helvetica-Bold", 16, '   '.join(filter(None, [format_price('7g', prices.get('7g')), format_price('14g', prices.get('14g'))]))),
                ("Helvetica-Bold", 16, format_price('28g', prices.get('28g'))),
            ]
            # Calculate total height for pricetag
            total_price_height = 0
            for font, size, *_ in price_lines:
                pdf.setFont(font, size)
                total_price_height += pdf._leading + 0.08 * inch
            # Evenly space pricetag elements
            price_gap = (p_top - p_bottom - total_price_height) / (len(price_lines) + 1)
            p_y_current = p_top - price_gap
            for elem in price_lines:
                font, size, text = elem[:3]
                underline = elem[3] if len(elem) > 3 else False
                pdf.setFont(font, size)
                # Color tier name in pricetag if medical
                if font == "Helvetica-Bold" and size == 14 and text == tier['name'].upper():
                    pdf.setFillColor(tier_color)
                else:
                    pdf.setFillColor(black)
                pdf.drawCentredString(p_center_x, p_y_current, text)
                pdf.setFillColor(black)
                if underline and text:
                    text_width = pdf.stringWidth(text)
                    underline_y = p_y_current - 0.05 * inch
                    pdf.line(p_center_x - text_width / 2, underline_y, p_center_x + text_width / 2, underline_y)
                p_y_current -= pdf._leading + 0.08 * inch + price_gap
        pdf.save()
        abs_path = os.path.abspath(pdf_path)
        try:
            if os.name == 'posix':
                subprocess.call(['open', abs_path])
            elif os.name == 'nt':
                subprocess.call(['start', abs_path], shell=True)
        except Exception as e:
            messagebox.showerror("Open Failed", f"PDF at {abs_path}; error: {e}. Open manually.")
        return pdf_path
        return pdf_path