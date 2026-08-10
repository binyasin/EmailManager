from fpdf import FPDF
import os

# Read the resume text
with open('M_Azam_Tailored_Resume_DeputyManager_Planning.txt', 'r', encoding='utf-8') as f:
    resume_text = f.read()

with open('M_Azam_Cover_Letter_DeputyManager_Planning.txt', 'r', encoding='utf-8') as f:
    cover_text = f.read()

# Create PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font('Helvetica', 'B', 16)
pdf.cell(0, 10, 'MOHAMMAD AZAM ALEEM', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.set_font('Helvetica', '', 10)
pdf.cell(0, 6, 'Karachi, Pakistan | +92 327 2310 769 | +92 333 3045 707', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.cell(0, 6, 'azam_aleem@hotmail.com | linkedin.com/in/muhammed-azam-aleem-7a35ba18', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.ln(5)

# Add resume content
pdf.set_font('Helvetica', 'B', 12)
pdf.cell(0, 8, 'RESUME - DEPUTY MANAGER PLANNING', new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

# Use multi_cell with proper width
for line in resume_text.split('\n'):
    line = line.strip()
    if not line:
        pdf.ln(3)
        continue
    
    if line.startswith('══') or line.startswith('━━') or line.startswith('──'):
        continue
    elif line.startswith('▸') or line.startswith('✅'):
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, line)
    elif line.isupper() and len(line) > 5:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.multi_cell(0, 6, line)
    else:
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, line)

# Cover letter on new page
pdf.add_page()
pdf.set_font('Helvetica', 'B', 14)
pdf.cell(0, 10, 'COVER LETTER - DEPUTY MANAGER PLANNING', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.ln(5)

for line in cover_text.split('\n'):
    line = line.strip()
    if not line:
        pdf.ln(3)
        continue
    
    if line.startswith('🔹'):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.multi_cell(0, 5, line)
    elif line.startswith('•') or line.startswith('✅'):
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, line)
    else:
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, line)

# Save
output_path = os.path.join(os.getcwd(), 'M_Azam_Complete_Application_DeputyManager_Planning.pdf')
pdf.output(output_path)
print(f"PDF created: {output_path}")