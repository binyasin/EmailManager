from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
import os

# Read the resume text
with open('M_Azam_Tailored_Resume_DeputyManager_Planning.txt', 'r', encoding='utf-8') as f:
    resume_text = f.read()

with open('M_Azam_Cover_Letter_DeputyManager_Planning.txt', 'r', encoding='utf-8') as f:
    cover_text = f.read()

# Create PDF document
output_path = os.path.join(os.getcwd(), 'M_Azam_Complete_Application_DeputyManager_Planning.pdf')
doc = SimpleDocTemplate(output_path, pagesize=A4, 
                        leftMargin=0.75*inch, rightMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

# Styles
styles = getSampleStyleSheet()

title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                             fontSize=16, textColor=HexColor('#1D3557'),
                             alignment=1, spaceAfter=6)

subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Normal'],
                                fontSize=10, textColor=HexColor('#555555'),
                                alignment=1, spaceAfter=12)

section_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'],
                               fontSize=11, textColor=HexColor('#1D3557'),
                               spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold')

body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                            fontSize=9.5, textColor=HexColor('#1A252C'),
                            spaceAfter=3, leading=12, fontName='Helvetica')

bullet_style = ParagraphStyle('CustomBullet', parent=styles['Normal'],
                              fontSize=9.5, textColor=HexColor('#1A252C'),
                              spaceAfter=2, leading=12, fontName='Helvetica',
                              leftIndent=18, bulletIndent=6)

cover_section_style = ParagraphStyle('CoverSection', parent=styles['Heading2'],
                                     fontSize=11, textColor=HexColor('#1D3557'),
                                     spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold')

story = []

# ========== RESUME ==========
story.append(Paragraph('MOHAMMAD AZAM ALEEM', title_style))
story.append(Paragraph('Karachi, Pakistan | +92 327 2310 769 | +92 333 3045 707', subtitle_style))
story.append(Paragraph('azam_aleem@hotmail.com | linkedin.com/in/muhammed-azam-aleem-7a35ba18', subtitle_style))
story.append(Spacer(1, 6))

story.append(Paragraph('RESUME — DEPUTY MANAGER PLANNING', ParagraphStyle('ResumeTitle', parent=section_style, alignment=1, fontSize=12)))
story.append(Spacer(1, 8))

# Process resume text
for line in resume_text.split('\n'):
    line = line.strip()
    if not line:
        story.append(Spacer(1, 4))
        continue
    
    if line.startswith('══') or line.startswith('━━') or line.startswith('──'):
        continue
    elif line.startswith('▸') or line.startswith('✅') or line.startswith('•'):
        story.append(Paragraph(f'• {line.lstrip("▸✅• ")}', bullet_style))
    elif line.isupper() and len(line) > 5:
        story.append(Paragraph(line, section_style))
    else:
        story.append(Paragraph(line, body_style))

# Page break
story.append(PageBreak())

# ========== COVER LETTER ==========
story.append(Paragraph('COVER LETTER — DEPUTY MANAGER PLANNING', 
                       ParagraphStyle('CoverTitle', parent=section_style, alignment=1, fontSize=14)))
story.append(Spacer(1, 10))

# Process cover letter text
for line in cover_text.split('\n'):
    line = line.strip()
    if not line:
        story.append(Spacer(1, 4))
        continue
    
    if line.startswith('🔹'):
        story.append(Paragraph(line, cover_section_style))
    elif line.startswith('•') or line.startswith('✅'):
        story.append(Paragraph(f'• {line.lstrip("•✅ ")}', bullet_style))
    else:
        story.append(Paragraph(line, body_style))

# Build PDF
doc.build(story)
print(f"PDF created: {output_path}")