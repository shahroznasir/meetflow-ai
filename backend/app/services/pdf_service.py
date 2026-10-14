import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.schemas.mom import MeetingMinutesPackage
from app.config import settings

class PDFService:
    @staticmethod
    def generate_mom_pdf(meeting_id: int, mom: MeetingMinutesPackage) -> str:
        """Generates a professional corporate PDF for the Meeting Minutes."""
        filename = f"MoM_Meeting_{meeting_id}.pdf"
        output_path = os.path.join(settings.STORAGE_DIR, settings.PDF_SUBDIR, filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=6
        )

        h2_style = ParagraphStyle(
            'DocH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#0284C7'),
            spaceBefore=14,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=6
        )

        meta_style = ParagraphStyle(
            'DocMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#64748B')
        )

        story = []

        # Header Title
        story.append(Paragraph(mom.meeting_title, title_style))
        story.append(Paragraph(f"<b>Type:</b> {mom.meeting_type} | <b>Date:</b> {mom.date_time or 'Recorded'} | <b>Sentiment:</b> {mom.overall_sentiment}", meta_style))
        story.append(Paragraph(f"<b>Participants:</b> {', '.join(mom.participants) if mom.participants else 'Not specified'}", meta_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=12))

        # Executive Summary
        story.append(Paragraph("Executive Summary", h2_style))
        story.append(Paragraph(mom.executive_summary, body_style))

        # Key Decisions
        if mom.key_decisions:
            story.append(Paragraph("Key Decisions Agreed", h2_style))
            for dec in mom.key_decisions:
                story.append(Paragraph(f"• {dec}", body_style))

        # Action Items Table
        if mom.action_items:
            story.append(Paragraph("Action Items & Deliverables", h2_style))
            
            table_data = [
                [
                    Paragraph("<b>Task</b>", body_style),
                    Paragraph("<b>Assignee</b>", body_style),
                    Paragraph("<b>Due Date</b>", body_style),
                    Paragraph("<b>Priority</b>", body_style)
                ]
            ]

            for item in mom.action_items:
                assignee_text = item.assignee_name
                if item.assignee_email:
                    assignee_text += f"<br/><font size=7 color='#64748b'>({item.assignee_email})</font>"

                table_data.append([
                    Paragraph(item.task, body_style),
                    Paragraph(assignee_text, body_style),
                    Paragraph(item.due_date or "TBD", body_style),
                    Paragraph(f"<b>{item.priority}</b>", body_style)
                ])

            table = Table(table_data, colWidths=[240, 120, 85, 75])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(table)

        # Topics Discussed
        if mom.agenda_topics:
            story.append(Paragraph("Discussion Breakdown", h2_style))
            for topic in mom.agenda_topics:
                story.append(Paragraph(f"<b>{topic.topic}</b>", body_style))
                story.append(Paragraph(topic.summary, body_style))
        # Verbatim Speaker Transcript
        if mom.transcript:
            story.append(Paragraph("Verbatim Speaker Transcript", h2_style))
            for seg in mom.transcript:
                seg_speaker = seg.speaker if hasattr(seg, 'speaker') else seg.get('speaker', 'Speaker')
                seg_time = seg.timestamp if hasattr(seg, 'timestamp') else seg.get('timestamp', '')
                seg_text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
                time_prefix = f"<font color='#64748b'>{seg_time}</font> " if seg_time else ""
                story.append(Paragraph(f"{time_prefix}<b>{seg_speaker}:</b> {seg_text}", body_style))
                story.append(Spacer(1, 2))

        # Build PDF
        doc.build(story)
        return output_path

pdf_service = PDFService()
