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
            brand = item['brand']
            tier = item['tier']
            strain = item['strain']
            # Nametag
            center_x = x_left + label_width / 2
            # Dynamically size logo to fit label and leave space for text
            max_logo_width = label_width * 0.7
            max_logo_height = label_height * 0.35
            logo_height_used = 0
            y_top = y - 0.1 * inch
            logo_path = tier.get('nametag_logo_path')
            if logo_path:
                abs_logo_path = os.path.abspath(logo_path)
                if os.path.exists(abs_logo_path):
                    try:
                        logo_img = ImageReader(abs_logo_path)
                        # Get actual image size
                        img_w, img_h = logo_img.getSize()
                        aspect = img_w / img_h
                        if img_w > img_h:
                            logo_width = min(max_logo_width, img_w * (max_logo_height / img_h))
                            logo_height = logo_width / aspect
                        else:
                            logo_height = min(max_logo_height, img_h * (max_logo_width / img_w))
                            logo_width = logo_height * aspect
                        # Center logo at top
                        pdf.drawImage(logo_img, center_x - logo_width/2, y_top - logo_height, logo_width, logo_height, mask='auto')
                        logo_height_used = logo_height + 0.12 * inch
                    except Exception as e:
                        print(f"Tier logo error: {e}")
                else:
                    print(f"Tier logo file not found: {abs_logo_path}")
            # Calculate available space for text
            y_current = y_top - logo_height_used
            text_elements = []
            text_elements.append(("Helvetica-Bold", 13, tier['name']))
            text_elements.append(("Helvetica-BoldOblique", 18, strain.name, True))  # underline
            if strain.lineage:
                text_elements.append(("Helvetica", 10, f"({strain.lineage})"))
            text_elements.append(("Helvetica-Bold", 14, strain.classification))
            text_elements.append(("Helvetica-Bold", 14, f"THC: {strain.thc_percent:.2f}%"))
            # Calculate total text height
            total_text_height = 0
            for font, size, *_ in text_elements:
                pdf.setFont(font, size)
                total_text_height += pdf._leading + 0.08 * inch
            # Center text block vertically in remaining space
            y_text_start = y_current - total_text_height / 2 + 0.2 * inch
            y_current = y_text_start
            for elem in text_elements:
                font, size, text = elem[:3]
                underline = elem[3] if len(elem) > 3 else False
                pdf.setFont(font, size)
                pdf.drawCentredString(center_x, y_current, text)
                if underline:
                    text_width = pdf.stringWidth(text)
                    underline_y = y_current - 0.05 * inch
                    pdf.setLineWidth(2)
                    pdf.line(center_x - text_width / 2, underline_y, center_x + text_width / 2, underline_y)
                    pdf.setLineWidth(1)
                y_current -= pdf._leading + 0.08 * inch
            # Pricetag
            p_center_x = x_left + label_width + label_width / 2
            p_y_current = y - 0.1 * inch
            # Brand name: bold, underline
            pdf.setFont("Helvetica-Bold", 20)
            brand_text = brand['name']
            pdf.drawCentredString(p_center_x, p_y_current, brand_text)
            underline_y = p_y_current - 0.05 * inch
            brand_width = pdf.stringWidth(brand_text)
            pdf.setLineWidth(2)
            pdf.line(p_center_x - brand_width / 2, underline_y, p_center_x + brand_width / 2, underline_y)
            pdf.setLineWidth(1)
            p_y_current -= 0.28 * inch
            # Tier name: bold, underline
            pdf.setFont("Helvetica-Bold", 16)
            tier_text = tier['name']
            pdf.drawCentredString(p_center_x, p_y_current, tier_text)
            underline_y = p_y_current - 0.05 * inch
            tier_width = pdf.stringWidth(tier_text)
            pdf.setLineWidth(1.5)
            pdf.line(p_center_x - tier_width / 2, underline_y, p_center_x + tier_width / 2, underline_y)
            pdf.setLineWidth(1)
            p_y_current -= 0.22 * inch
            # Prices: bold, arranged in two rows
            pdf.setFont("Helvetica-Bold", 16)
            prices = tier.get('prices', {})
            def format_price(weight, price):
                if price:
                    return f"{weight}-${price}"
                return ''
            line1 = '   '.join(filter(None, [format_price('1g', prices.get('1g', '')), format_price('3.5g', prices.get('3.5g', ''))]))
            pdf.drawCentredString(p_center_x, p_y_current, line1)
            p_y_current -= 0.25 * inch
            line2 = '   '.join(filter(None, [format_price('7g', prices.get('7g', '')), format_price('14g', prices.get('14g', ''))]))
            pdf.drawCentredString(p_center_x, p_y_current, line2)
            p_y_current -= 0.25 * inch
            line3 = format_price('28g', prices.get('28g', ''))
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
        try:
            if os.name == 'posix':
                subprocess.call(['open', abs_path])
            elif os.name == 'nt':
                subprocess.call(['start', abs_path], shell=True)
        except Exception as e:
            print(f"Failed to open PDF: {e}")
            messagebox.showerror("Open Failed", f"PDF at {abs_path}; error: {e}. Open manually.")
        return pdf_path
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