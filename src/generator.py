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
        
        # Configurable variables for easy formatting/spacing adjustments
        nametag_font_sizes = {
            'tier': 16,      # Tier name size
            'strain': 20,    # Strain name size (bold, underlined)
            'lineage': 12,   # Lineage size
            'class': 12,     # Classification size
            'thc': 12        # THC% size
        }
        pricetag_font_sizes = {
            'brand': 20,     # Brand name size (underlined)
            'tier': 18,      # Tier name size (underlined)
            'prices': 20     # Price lines size
        }
        line_spacing_extra = 0.04 * inch  # Extra vertical space between nametag lines (adjust to tighten/loosen)
        gap_after_logo = 0.015 * inch       # Gap below logo before text starts (adjust for more/less breathing room)
        price_line_extra = 0.06 * inch    # Extra vertical padding per pricetag line
        no_logo_top_margin = 0.1 * inch   # Top margin if no logo (adjust to reduce empty space at top)
        underline_offset = 0.035 * inch    # Vertical offset for underlines (adjust if lines overlap text)
        gap_after_tier_price = 0.08 * inch  # Extra gap after tier name before pricing in pricetag (adjust to increase/decrease specific space)
        
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
                    'Yellow Tier': (1, 0.8, 0),
                    'Orange Tier': (1, 0.65, 0),
                    'Pink Tier': (1, 0.08, 0.58),
                    'Purple Tier': (0.5, 0, 0.5),
                }
                tier_color = color_map.get(tier.get('name'), black)
            text_elements = [
                ("Helvetica-Bold", nametag_font_sizes['tier'], tier['name'], False, tier_color),
                ("Helvetica-BoldOblique", nametag_font_sizes['strain'], strain.name, True), # underline
            ]
            if strain.lineage:
                text_elements.append(("Helvetica", nametag_font_sizes['lineage'], f"({strain.lineage})"))
            text_elements.append(("Helvetica", nametag_font_sizes['class'], strain.classification))
            text_elements.append(("Helvetica-Bold", nametag_font_sizes['thc'], f"THC: {strain.thc_percent:.2f}%"))
            # Estimate total text height
            total_text_height = 0
            for font, size, *_ in text_elements:
                pdf.setFont(font, size)
                total_text_height += pdf._leading + line_spacing_extra
            # Set max logo height so logo + text fits label
            available_height = label_height - 0.1 * inch
            max_logo_height = available_height * 0.45
            max_logo_width = label_width * .7
            logo_height_used = 0 
            elements = []  # List of (type, height, data)
            logo_path = tier.get('nametag_logo_path')
            if logo_path:
                abs_logo_path = os.path.abspath(logo_path)
                if os.path.exists(abs_logo_path):
                    try:
                        logo_img = ImageReader(abs_logo_path)
                        img_w, img_h = logo_img.getSize()
                        aspect = img_w / img_h
                        logo_width = min(max_logo_width, max_logo_height * aspect)
                        logo_height = logo_width / aspect if aspect > 1 else min(max_logo_height, max_logo_width / aspect)
                        elements.append(('logo', logo_height, (logo_img, logo_width)))
                        logo_height_used = logo_height
                    except Exception as e:
                        print(f"Tier logo error: {e}")
            # Add text elements with their heights
            for font, size, text, *extra in text_elements:
                pdf.setFont(font, size)
                elements.append(('text', pdf._leading, (font, size, text, extra)))
            # Calculate even spacing
            total_content_height = sum(h for _, h, _ in elements)
            num_gaps = len(elements) - 1 if elements else 0
            gap_size = (available_height - total_content_height) / (num_gaps + 1) if num_gaps > 0 else 0  # Extra gaps at top/bottom

            if not logo_path:
                y_current = y_top - no_logo_top_margin
            else:
                y_current = y_top - gap_size

            for el_type, el_height, el_data in elements:
                if el_type == 'logo':
                    img, width = el_data
                    logo_x = center_x - width / 2
                    pdf.drawImage(img, logo_x, y_current - el_height, width, el_height, mask='auto')
                else:
                    font, size, text = el_data[:3]
                    underline = el_data[3][0] if el_data[3] else False
                    color = el_data[3][1] if len(el_data[3]) > 1 else black
                    pdf.setFont(font, size)
                    if color != black:
                        pdf.setFillColorRGB(*color)
                    pdf.drawCentredString(center_x, y_current - size, text)  # Align baseline to y_current - size for better positioning
                    pdf.setFillColor(black)
                    if underline:
                        pdf.setLineWidth(2)
                        text_width = pdf.stringWidth(text)
                        underline_y = (y_current - size) - underline_offset
                        pdf.line(center_x - text_width / 2, underline_y, center_x + text_width / 2, underline_y)
                        pdf.setLineWidth(1)
                y_current -= el_height + (gap_after_logo if el_type == 'logo' else gap_size)
            # If no logo, adjust starting y if needed
            if not logo_path:
                y_current = y_top - no_logo_top_margin
            prices = tier.get('prices', {})
            def format_price(weight, price):
                if price:
                    return f"{weight}-${price}"
                return ''
            # Pricetag: evenly distribute elements to fill right half
            p_center_x = x_left + label_width + label_width / 2
            p_top = y - 0.4 * inch
            p_bottom = y - label_height + 0.1 * inch
            # Collect non-empty price lines to avoid wasting space on blanks
            price_lines = [
                ("Helvetica-Bold", pricetag_font_sizes['brand'], brand['name'].upper(), True),
                ("Helvetica-Bold", pricetag_font_sizes['tier'], tier['name'].upper(), True),
            ]
            if brand.get('category') == 'MED':
                p1 = format_price('1g', prices.get('1g'))
                p2 = format_price('3.5g', prices.get('3.5g'))
                p3 = format_price('7g', prices.get('7g'))
                p4 = format_price('14g', prices.get('14g'))
                p5 = format_price('28g', prices.get('28g'))
                p6 = format_price('1lb', prices.get('1lb'))
                if p1 or p2:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], (p1, p2)))
                if p3 or p4:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], (p3, p4)))
                if p5 or p6:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], (p5, p6)))
            else:
                line1 = '   '.join(filter(None, [format_price('1g', prices.get('1g')), format_price('3.5g', prices.get('3.5g'))]))
                if line1:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], line1))
                line2 = '   '.join(filter(None, [format_price('7g', prices.get('7g')), format_price('14g', prices.get('14g'))]))
                if line2:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], line2))
                line3 = format_price('28g', prices.get('28g'))
                if line3:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], line3))
                line4 = format_price('1lb', prices.get('1lb'))
                if line4:
                    price_lines.append(("Helvetica-Bold", pricetag_font_sizes['prices'], line4))
            # Calculate total height for pricetag
            total_price_height = 0
            for font, size, *_ in price_lines:
                pdf.setFont(font, size)
                total_price_height += pdf._leading + price_line_extra
            # Evenly space pricetag elements
            price_gap = (p_top - p_bottom - total_price_height) / (len(price_lines) + 1) if len(price_lines) > 0 else 0
            p_y_current = p_top - price_gap
            col_width = 1.4 * inch  # Adjust as needed for column spacing
            pricetag_left = x_left + label_width + 0.3 * inch  # Left margin for pricetag
            left_x = pricetag_left
            right_x = pricetag_left + col_width
            # Calculate fixed offset for price alignment in MED
            global_offset = 0
            max_right_width = 0
            if brand.get('category') == 'MED':
                price_tuples = [text for font, size, text, *_ in price_lines if isinstance(text, tuple)]
                if price_tuples:
                    pdf.setFont("Helvetica-Bold", pricetag_font_sizes['prices'])
                    max_left_width = max(pdf.stringWidth(left) for left, _ in price_tuples)
                    max_right_width = max(pdf.stringWidth(right) for _, right in price_tuples)
                    effective_width = max(col_width + max_right_width, max_left_width)
                    global_offset = p_center_x - left_x - (effective_width / 2)
            for elem in price_lines:
                font, size, text = elem[:3]
                underline = elem[3] if len(elem) > 3 else False
                pdf.setFont(font, size)
                # Color tier name in pricetag if medical
                if font == "Helvetica-Bold" and size == pricetag_font_sizes['tier'] and not isinstance(text, tuple) and text == tier['name'].upper():
                    if tier_color != black:
                        pdf.setFillColorRGB(*tier_color)
                    else:
                        pdf.setFillColor(black)
                    is_tier = True
                else:
                    pdf.setFillColor(black)
                    is_tier = False
                if isinstance(text, tuple):
                    left_text, right_text = text
                    pdf.drawString(left_x + global_offset, p_y_current, left_text)
                    right_width = pdf.stringWidth(right_text)
                    pdf.drawString((right_x + global_offset + max_right_width) - right_width, p_y_current, right_text)
                else:
                    pdf.drawCentredString(p_center_x, p_y_current, text)
                pdf.setFillColor(black)
                if underline and text and not isinstance(text, tuple):
                    pdf.setLineWidth(2)
                    text_width = pdf.stringWidth(text)
                    underline_y = p_y_current - underline_offset
                    pdf.line(p_center_x - text_width / 2, underline_y, p_center_x + text_width / 2, underline_y)
                    pdf.setLineWidth(1)
                p_y_current -= pdf._leading + price_line_extra + (gap_after_tier_price if is_tier else price_gap)
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