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
            y_current = y - 0.1 * inch
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(center_x, y_current, brand['name'])
            y_current -= 0.22 * inch
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawCentredString(center_x, y_current, tier['name'])
            y_current -= 0.22 * inch
            pdf.setFont("Helvetica-Bold", 18)
            strain_text = strain.name
            strain_width = pdf.stringWidth(strain_text)
            max_strain_width = label_width - 0.2 * inch
            while strain_width > max_strain_width and pdf._fontsize > 10:
                pdf.setFont("Helvetica-Bold", pdf._fontsize - 1)
                strain_width = pdf.stringWidth(strain_text)
            pdf.drawCentredString(center_x, y_current, strain_text)
            underline_y = y_current - 0.05 * inch
            pdf.line(center_x - strain_width / 2, underline_y, center_x + strain_width / 2, underline_y)
            y_current -= pdf._leading + 0.18 * inch
            pdf.setFont("Helvetica", 10)
            if strain.lineage:
                pdf.drawCentredString(center_x, y_current, f"({strain.lineage})")
                y_current -= 0.18 * inch
            pdf.setFont("Helvetica", 12)
            pdf.drawCentredString(center_x, y_current, strain.classification)
            y_current -= 0.18 * inch
            pdf.drawCentredString(center_x, y_current, f"THC: {strain.thc_percent:.2f}%")
            # Pricetag
            p_center_x = x_left + label_width + label_width / 2
            p_y_current = y - 0.1 * inch
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawCentredString(p_center_x, p_y_current, brand['name'])
            p_y_current -= 0.22 * inch
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawCentredString(p_center_x, p_y_current, tier['name'])
            p_y_current -= 0.22 * inch
            pdf.setFont("Helvetica-Bold", 14)
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