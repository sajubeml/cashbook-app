"""
pdf_generator.py - ReportLab PDF Engine for CashBook Monthly Ledger Statements.
Generates publication-grade, structured statements with opening and closing balances.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.pdfgen import canvas
import database


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render 'Page X of Y' on all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(30, 36, 565, 36)

        # Footer text
        footer_text = f"CashBook Financial Report  |  Generated on {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}"
        self.drawString(30, 24, footer_text)

        # Page numbering right-aligned
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(565, 24, page_str)
        self.restoreState()


def format_currency(val):
    """Format numeric values with thousands separator and two decimal places."""
    return f"{float(val):,.2f}"


def get_default_reports_dir():
    """Determine reports directory dynamically, supporting Android user_data_dir."""
    try:
        from kivy.utils import platform
        if platform == 'android':
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
                rep_dir = os.path.join(app.user_data_dir, "reports")
                os.makedirs(rep_dir, exist_ok=True)
                return rep_dir
    except Exception:
        pass
    rep_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(rep_dir, exist_ok=True)
    return rep_dir


def generate_monthly_pdf(year, month, output_path=None, title="CashBook Ledger Statement", db_path=None):
    """
    Generate a monthly ledger PDF statement using ReportLab.
    Retrieves data using database.get_monthly_ledger_data.
    """
    # Fetch data from database
    ledger_data = database.get_monthly_ledger_data(year, month, db_path=db_path)

    month_name = datetime(year, month, 1).strftime("%B %Y")
    if not output_path:
        reports_dir = get_default_reports_dir()
        filename = f"CashBook_Statement_{year}_{month:02d}.pdf"
        output_path = os.path.join(reports_dir, filename)

    # Document Setup - A4 Portrait with 30pt margins
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=36,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )

    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1  # Centered
    )

    cell_style = ParagraphStyle(
        'BodyCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )

    cell_center_style = ParagraphStyle(
        'BodyCellCenter',
        parent=cell_style,
        alignment=1
    )

    cell_right_style = ParagraphStyle(
        'BodyCellRight',
        parent=cell_style,
        alignment=2
    )

    in_style = ParagraphStyle(
        'CashInCell',
        parent=cell_right_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#059669')  # Emerald Green
    )

    out_style = ParagraphStyle(
        'CashOutCell',
        parent=cell_right_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#DC2626')  # Coral Red
    )

    balance_style = ParagraphStyle(
        'BalanceCell',
        parent=cell_right_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0F172A')
    )

    story = []

    # ==========================================
    # 1. HEADER SECTION
    # ==========================================
    story.append(Paragraph(title.upper(), title_style))
    meta_info = f"<b>Statement Period:</b> {month_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Report Date:</b> {datetime.now().strftime('%d %B %Y')}"
    story.append(Paragraph(meta_info, subtitle_style))
    story.append(Spacer(1, 6))

    # ==========================================
    # 2. FINANCIAL SUMMARY CARDS BOX
    # ==========================================
    summary_data = [
        [
            Paragraph("<font size=8 color='#64748B'>OPENING BALANCE</font><br/><b><font size=11 color='#1E293B'>" + format_currency(ledger_data["opening_balance"]) + "</font></b>", styles['Normal']),
            Paragraph("<font size=8 color='#059669'>TOTAL CASH IN (+)</font><br/><b><font size=11 color='#059669'>" + format_currency(ledger_data["total_in"]) + "</font></b>", styles['Normal']),
            Paragraph("<font size=8 color='#DC2626'>TOTAL CASH OUT (-)</font><br/><b><font size=11 color='#DC2626'>" + format_currency(ledger_data["total_out"]) + "</font></b>", styles['Normal']),
            Paragraph("<font size=8 color='#2563EB'>CLOSING BALANCE</font><br/><b><font size=11 color='#2563EB'>" + format_currency(ledger_data["closing_balance"]) + "</font></b>", styles['Normal'])
        ]
    ]

    summary_table = Table(summary_data, colWidths=[133.75, 133.75, 133.75, 133.75])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 14))

    # ==========================================
    # 3. DETAILED TRANSACTION LEDGER TABLE
    # ==========================================
    # Widths sum = 535 pt (A4 width 595 - 60 margin)
    col_widths = [55, 45, 80, 65, 115, 55, 55, 65]
    headers = [
        Paragraph("Date", header_cell_style),
        Paragraph("Time", header_cell_style),
        Paragraph("Category", header_cell_style),
        Paragraph("Mode", header_cell_style),
        Paragraph("Remarks / Description", header_cell_style),
        Paragraph("Cash In (+)", header_cell_style),
        Paragraph("Cash Out (-)", header_cell_style),
        Paragraph("Balance", header_cell_style),
    ]

    table_data = [headers]

    # Opening balance anchor row
    opening_row = [
        Paragraph("01-" + datetime(year, month, 1).strftime("%b"), cell_center_style),
        Paragraph("-", cell_center_style),
        Paragraph("<b>Opening Balance</b>", cell_style),
        Paragraph("-", cell_center_style),
        Paragraph("Brought forward from previous period", cell_style),
        Paragraph("-", cell_right_style),
        Paragraph("-", cell_right_style),
        Paragraph(format_currency(ledger_data["opening_balance"]), balance_style)
    ]
    table_data.append(opening_row)

    # Transactions rows
    transactions = ledger_data["transactions"]
    for t in transactions:
        is_in = t["type"] == "IN"
        in_amt = format_currency(t["amount"]) if is_in else "-"
        out_amt = "-" if is_in else format_currency(t["amount"])

        # Format date as DD-Mon
        try:
            d_obj = datetime.strptime(t["date"], "%Y-%m-%d")
            formatted_date = d_obj.strftime("%d-%b")
        except Exception:
            formatted_date = t["date"]

        row = [
            Paragraph(formatted_date, cell_center_style),
            Paragraph(t.get("time", "")[:5], cell_center_style),
            Paragraph(t.get("category", "General"), cell_style),
            Paragraph(t.get("payment_mode", "Cash"), cell_center_style),
            Paragraph(t.get("remarks", "") or "-", cell_style),
            Paragraph(in_amt, in_style if is_in else cell_right_style),
            Paragraph(out_amt, out_style if not is_in else cell_right_style),
            Paragraph(format_currency(t["running_balance"]), balance_style)
        ]
        table_data.append(row)

    # Final Totals Row
    totals_row = [
        Paragraph("<b>TOTALS</b>", cell_center_style),
        Paragraph("", cell_style),
        Paragraph(f"<b>{len(transactions)} Entry(s)</b>", cell_style),
        Paragraph("", cell_style),
        Paragraph("<b>Monthly Net Movement: " + format_currency(ledger_data["total_in"] - ledger_data["total_out"]) + "</b>", cell_style),
        Paragraph("<b>" + format_currency(ledger_data["total_in"]) + "</b>", in_style),
        Paragraph("<b>" + format_currency(ledger_data["total_out"]) + "</b>", out_style),
        Paragraph("<b>" + format_currency(ledger_data["closing_balance"]) + "</b>", balance_style)
    ]
    table_data.append(totals_row)

    ledger_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        # Opening balance row styling
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F1F5F9')),
        # Totals row styling
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.2, colors.HexColor('#94A3B8')),
    ]

    # Alternating background for transaction rows
    for i in range(2, len(table_data) - 1):
        if i % 2 == 1:
            t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')))

    ledger_table.setStyle(TableStyle(t_style))
    story.append(ledger_table)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path


if __name__ == "__main__":
    database.init_db()
    pdf_path = generate_monthly_pdf(2026, 9)
    print(f"Statement generated: {pdf_path}")
