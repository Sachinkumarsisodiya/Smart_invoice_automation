from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generate_digital_invoice_pdf_bytes(invoice) -> bytes:
    """
    Generates a professional, high-resolution Digital Invoice PDF in memory.
    Used as an automatic fallback when the original physical file is unavailable on disk.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )

    vendor_name = invoice.vendor.name if invoice.vendor else "Unassigned Vendor"
    vendor_email = invoice.vendor.email if (invoice.vendor and invoice.vendor.email) else "N/A"
    vendor_gstin = invoice.vendor.gstin if (invoice.vendor and invoice.vendor.gstin) else "N/A"

    story.append(Paragraph(f"<b>OFFICIAL INVOICE: {invoice.invoice_number}</b>", title_style))
    story.append(Paragraph(f"Issued By: <b>{vendor_name}</b> | Status: <b>{invoice.status}</b> | Payment: <b>{invoice.payment_status}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    meta_data = [
        [
            Paragraph("<b>VENDOR / ISSUER DETAILS:</b>", styles['Normal']),
            Paragraph("<b>INVOICE SUMMARY & DATES:</b>", styles['Normal'])
        ],
        [
            Paragraph(f"<b>Name:</b> {vendor_name}<br/><b>GSTIN:</b> {vendor_gstin}<br/><b>Email:</b> {vendor_email}", styles['Normal']),
            Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}<br/><b>Issue Date:</b> {invoice.invoice_date}<br/><b>Due Date:</b> {invoice.due_date}", styles['Normal'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    items_data = [["Line Item Description", "Qty", "Unit Price (₹)", "Total Amount (₹)"]]
    if invoice.items and len(invoice.items) > 0:
        for item in invoice.items:
            items_data.append([
                Paragraph(item.description or "Line Item", styles['Normal']),
                str(item.quantity),
                f"₹{float(item.unit_price):,.2f}",
                f"₹{float(item.amount):,.2f}"
            ])
    else:
        items_data.append([
            Paragraph(f"Supply of Goods/Services as per invoice #{invoice.invoice_number}", styles['Normal']),
            "1.000",
            f"₹{float(invoice.subtotal or invoice.total_amount):,.2f}",
            f"₹{float(invoice.subtotal or invoice.total_amount):,.2f}"
        ])

    items_table = Table(items_data, colWidths=[240, 50, 120, 130])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    rem_balance = float(invoice.remaining_amount or 0)
    summary_data = [
        ["Subtotal Amount:", f"₹{float(invoice.subtotal or 0):,.2f}"],
        ["Tax Amount (GST):", f"₹{float(invoice.tax_amount or 0):,.2f}"],
        ["Grand Total:", f"₹{float(invoice.total_amount or 0):,.2f}"],
        ["Settled / Paid Amount:", f"₹{float(invoice.paid_amount or 0):,.2f}"],
        ["Remaining Payable Balance:", f"₹{rem_balance:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[360, 180])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,2), (1,2), 'Helvetica-Bold'),
        ('FONTNAME', (0,4), (1,4), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,4), (1,4), colors.HexColor('#DC2626') if rem_balance > 0 else colors.HexColor('#166534')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,2), (1,2), 1, colors.HexColor('#E2E8F0')),
        ('LINEBELOW', (0,4), (1,4), 1.5, colors.HexColor('#94A3B8')),
    ]))
    story.append(summary_table)

    if invoice.notes:
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Notes / Remarks:</b> {invoice.notes}", styles['Normal']))

    story.append(Spacer(1, 25))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=8))
    story.append(Paragraph(
        "<font size=8 color='#64748B'>Official Digital Document generated by SmartInvoice Business Automation Platform. Verified Audit Log Record.</font>",
        styles['Normal']
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
