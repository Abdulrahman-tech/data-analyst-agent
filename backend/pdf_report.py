# pdf_report.py
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Professional light theme colors ──────────────────────────────────────────
PURPLE      = HexColor('#6366f1')
PURPLE_LIGHT= HexColor('#ede9fe')
PURPLE_DARK = HexColor('#4338ca')
AMBER       = HexColor('#d97706')
AMBER_LIGHT = HexColor('#fef3c7')
GREEN       = HexColor('#059669')
GREEN_LIGHT = HexColor('#d1fae5')
RED         = HexColor('#dc2626')
RED_LIGHT   = HexColor('#fee2e2')
GRAY_900    = HexColor('#111827')
GRAY_700    = HexColor('#374151')
GRAY_500    = HexColor('#6b7280')
GRAY_300    = HexColor('#d1d5db')
GRAY_100    = HexColor('#f3f4f6')
GRAY_50     = HexColor('#f9fafb')
WHITE       = white


def build_pdf(session_data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    # ── Styles ────────────────────────────────────────────────────────────────
    s_brand = ParagraphStyle('Brand',
        fontSize=10, textColor=PURPLE, fontName='Helvetica-Bold',
        spaceAfter=1)

    s_title = ParagraphStyle('Title',
        fontSize=26, textColor=GRAY_900, fontName='Helvetica-Bold',
        spaceAfter=3, leading=30)

    s_subtitle = ParagraphStyle('Subtitle',
        fontSize=12, textColor=GRAY_500, fontName='Helvetica',
        spaceAfter=2)

    s_section = ParagraphStyle('Section',
        fontSize=8, textColor=PURPLE, fontName='Helvetica-Bold',
        spaceBefore=6, spaceAfter=3, letterSpacing=1.5)

    s_question = ParagraphStyle('Question',
        fontSize=14, textColor=GRAY_900, fontName='Helvetica-Bold',
        spaceBefore=4, spaceAfter=3, leading=18)

    s_body = ParagraphStyle('Body',
        fontSize=10, textColor=GRAY_700, fontName='Helvetica',
        leading=16, spaceAfter=3)

    s_code = ParagraphStyle('Code',
        fontSize=8, textColor=HexColor('#1e1b4b'), fontName='Courier',
        leading=13, leftIndent=6)

    s_pattern = ParagraphStyle('Pattern',
        fontSize=9, textColor=AMBER, fontName='Helvetica-Bold',
        leading=14, spaceAfter=1)

    s_pattern_body = ParagraphStyle('PatternBody',
        fontSize=9, textColor=GRAY_700, fontName='Helvetica',
        leading=14, spaceAfter=2)

    s_footer = ParagraphStyle('Footer',
        fontSize=8, textColor=GRAY_500, fontName='Helvetica',
        alignment=TA_CENTER)

    s_summary_title = ParagraphStyle('SummaryTitle',
        fontSize=11, textColor=GRAY_900, fontName='Helvetica-Bold',
        spaceAfter=2)

    elements = []

    filename = session_data.get("filename", "Unknown")
    exchanges = session_data.get("exchanges", [])
    now = datetime.now().strftime("%B %d, %Y")

    # ── Cover Page ────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 15*mm))

    # Purple accent bar at top
    elements.append(Table(
        [['']], colWidths=[170*mm], rowHeights=[3*mm]
    ))
    elements[-1].setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PURPLE),
        ('LINEABOVE', (0,0), (-1,-1), 0, PURPLE),
    ]))

    elements.append(Spacer(1, 8*mm))
    elements.append(Paragraph("dataanalyst.agent", s_brand))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph("Data Analysis Report", s_title))
    elements.append(Paragraph(f"Prepared on {now}", s_subtitle))
    elements.append(Spacer(1, 8*mm))

    # Cover meta table
    total_patterns = sum(len(e.get("patterns") or []) for e in exchanges)
    cover_data = [
        ["Dataset", filename],
        ["Questions Analyzed", str(len(exchanges))],
        ["Patterns Detected", str(total_patterns)],
        ["Generated", datetime.now().strftime("%B %d, %Y at %I:%M %p")],
    ]
    cover_table = Table(cover_data, colWidths=[50*mm, 120*mm])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (0,-1), GRAY_500),
        ('TEXTCOLOR', (1,0), (1,-1), GRAY_700),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, GRAY_50]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, GRAY_300),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, GRAY_300),
    ]))
    elements.append(cover_table)
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=PURPLE, spaceAfter=6*mm))

    # ── Executive Summary ─────────────────────────────────────────────────────
    if exchanges:
        elements.append(Paragraph("EXECUTIVE SUMMARY", s_section))
        all_insights = [e.get("insights", "") for e in exchanges if e.get("insights")]
        summary_text = " ".join(all_insights[:2])
        if len(summary_text) > 400:
            summary_text = summary_text[:400] + "..."

        summary_box = Table(
            [[Paragraph(summary_text, s_body)]],
            colWidths=[170*mm]
        )
        summary_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), PURPLE_LIGHT),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, PURPLE),
            ('ROUNDEDCORNERS', [4]),
        ]))
        elements.append(summary_box)
        elements.append(Spacer(1, 6*mm))

    # ── All patterns summary ──────────────────────────────────────────────────
    all_patterns = []
    for e in exchanges:
        for p in (e.get("patterns") or []):
            all_patterns.append(p)

    if all_patterns:
        elements.append(Paragraph("KEY PATTERNS DETECTED", s_section))
        for pattern in all_patterns:
            pattern_box = Table(
                [[Paragraph(f"⚠  {pattern.get('alert', '')}", s_pattern),
                  Paragraph(f"→ {pattern.get('question', '')}", s_pattern_body)]],
                colWidths=[85*mm, 85*mm]
            )
            pattern_box.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), AMBER_LIGHT),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('BOX', (0,0), (-1,-1), 1, HexColor('#fbbf24')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            elements.append(pattern_box)
            elements.append(Spacer(1, 2*mm))
        elements.append(Spacer(1, 4*mm))

    elements.append(HRFlowable(width="100%", thickness=1, color=GRAY_300, spaceAfter=6*mm))

    # ── Detailed Analysis ─────────────────────────────────────────────────────
    elements.append(Paragraph("DETAILED ANALYSIS", s_section))
    elements.append(Spacer(1, 3*mm))

    for i, exchange in enumerate(exchanges, 1):
        block = []

        # Question number badge + question
        q_data = [[
            Paragraph(f"Q{i}", ParagraphStyle('QNum',
                fontSize=11, textColor=WHITE, fontName='Helvetica-Bold',
                alignment=TA_CENTER)),
            Paragraph(exchange.get("query", ""), s_question)
        ]]
        q_table = Table(q_data, colWidths=[12*mm, 158*mm])
        q_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), PURPLE),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (0,0), 3),
            ('LEFTPADDING', (1,0), (1,0), 10),
            ('BACKGROUND', (1,0), (1,0), GRAY_50),
            ('BOX', (0,0), (-1,-1), 1, GRAY_300),
        ]))
        block.append(q_table)
        block.append(Spacer(1, 3*mm))

        # Intent
        if exchange.get("intent"):
            block.append(Paragraph(
                f"<i>Intent: {exchange['intent']}</i>",
                ParagraphStyle('Intent', parent=s_body,
                    fontSize=9, textColor=GRAY_500, leftIndent=4)
            ))
            block.append(Spacer(1, 2*mm))

        # Insights box
        if exchange.get("insights"):
            block.append(Paragraph("INSIGHTS", s_section))
            insights_box = Table(
                [[Paragraph(exchange["insights"], s_body)]],
                colWidths=[170*mm]
            )
            insights_box.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), GREEN_LIGHT),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1, HexColor('#6ee7b7')),
            ]))
            block.append(insights_box)
            block.append(Spacer(1, 3*mm))

        # Output
        if exchange.get("output") and exchange["output"] != "(code ran with no printed output)":
            block.append(Paragraph("OUTPUT", s_section))
            output_lines = exchange["output"].strip().split("\n")[:12]
            output_text = "\n".join(output_lines)
            if len(exchange["output"].split("\n")) > 12:
                output_text += "\n... (truncated)"

            output_box = Table(
                [[Paragraph(output_text.replace("\n", "<br/>"), s_code)]],
                colWidths=[170*mm]
            )
            output_box.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), HexColor('#f0f0ff')),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1, GRAY_300),
            ]))
            block.append(output_box)
            block.append(Spacer(1, 3*mm))

        # Patterns for this exchange
        if exchange.get("patterns"):
            block.append(Paragraph("PATTERNS", s_section))
            for pattern in exchange["patterns"]:
                block.append(Paragraph(f"⚠  {pattern.get('alert', '')}", s_pattern))
                if pattern.get("question"):
                    block.append(Paragraph(f"→ {pattern['question']}", s_pattern_body))
            block.append(Spacer(1, 2*mm))

        # Divider
        if i < len(exchanges):
            block.append(Spacer(1, 4*mm))
            block.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_300))
            block.append(Spacer(1, 4*mm))

        elements.append(KeepTogether(block))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=PURPLE, spaceAfter=3*mm))
    elements.append(Paragraph(
        f"Generated by dataanalyst.agent  •  {now}  •  Confidential",
        s_footer
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.read()
