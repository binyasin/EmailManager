import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

excel_path = r'C:\Users\DELL LATITUDE 5520\.openclaw\workspace\media\inbound\openclaw-staged-128f5700-4ab0-44fd-9cb3-0f1f08e4dc83\Aug_26_Complete_attempts_data---1b7f1b87-c0ba-4c52-99ba-afad0e043d9f.xlsx'
df = pd.read_excel(excel_path)

# Ensure output directory exists
os.makedirs('media', exist_ok=True)
out_img_path = r'C:\Users\DELL LATITUDE 5520\.openclaw\workspace\media\beautiful_gas_survey_summary.png'

# Create a figure with a 2x2 layout of subplots
# We will use 14x12 size to make it spacious and professional
fig, axs = plt.subplots(2, 2, figsize=(14, 12), facecolor='#f4f6f9')
fig.suptitle('GAS SURVEY & RECOVERY PERFORMANCE REPORT', fontsize=20, fontweight='bold', color='#1a252c', y=0.96)

# Define elegant colors
colors_premise = ['#1d3557', '#457b9d', '#a8dadc', '#e63946']
colors_meter = ['#2a9d8f', '#e9c46a', '#f4a261', '#e76f51']
colors_action = ['#4361ee', '#3f37c9', '#f72585']

# ----------------- Plot 1: Premise Status (Donut Chart) -----------------
premise_counts = df['Premise Status'].value_counts()
axs[0, 0].pie(
    premise_counts, 
    labels=[f"{k}\n({v:,})" for k, v in premise_counts.items()],
    autopct='%1.1f%%', 
    startangle=140, 
    colors=colors_premise,
    wedgeprops={'width': 0.4, 'edgecolor': 'w', 'linewidth': 2},
    textprops={'fontsize': 11, 'color': '#2c3e50', 'weight': 'bold'},
    pctdistance=0.75
)
axs[0, 0].set_title('PREMISE STATUS DISTRIBUTION', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
axs[0, 0].axis('equal')

# ----------------- Plot 2: Meter Status (Horizontal Bar Chart) -----------------
meter_counts = df['Meter Status'].value_counts()
y_pos = np.arange(len(meter_counts))
bars = axs[0, 1].barh(y_pos, meter_counts.values, color='#457b9d', height=0.6, edgecolor='none')
axs[0, 1].set_yticks(y_pos)
axs[0, 1].set_yticklabels([f"{k}  " for k in meter_counts.keys()], fontsize=11, fontweight='bold', color='#2c3e50')
axs[0, 1].invert_yaxis()  # top-down

# Add values to bars
for bar in bars:
    width = bar.get_width()
    axs[0, 1].text(
        width + 150, 
        bar.get_y() + bar.get_height()/2, 
        f'{width:,}', 
        va='center', 
        ha='left', 
        fontsize=11, 
        fontweight='bold', 
        color='#2c3e50'
    )

axs[0, 1].set_title('METER STATUS OVERVIEW', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
axs[0, 1].set_facecolor('#ffffff')
axs[0, 1].spines['top'].set_visible(False)
axs[0, 1].spines['right'].set_visible(False)
axs[0, 1].spines['bottom'].set_visible(False)
axs[0, 1].spines['left'].set_color('#bdc3c7')
axs[0, 1].xaxis.set_visible(False)

# ----------------- Plot 3: Action Performed (Pie Chart) -----------------
action_counts = df['Action Performed'].value_counts()
axs[1, 0].pie(
    action_counts, 
    labels=[f"{k}\n({v:,})" for k, v in action_counts.items()],
    autopct='%1.1f%%', 
    startangle=50, 
    colors=colors_action,
    explode=[0.02 if k != 'Removal' else 0.2 for k in action_counts.keys()],
    textprops={'fontsize': 11, 'color': '#2c3e50', 'weight': 'bold'},
    shadow=False
)
axs[1, 0].set_title('ACTION PERFORMED SUMMARY', fontsize=14, fontweight='bold', color='#2c3e50', pad=15)
axs[1, 0].axis('equal')

# ----------------- Plot 4: Key KPI Dashboard Cards (Text Rendered as Dashboard Card) -----------------
axs[1, 1].axis('off')
# Let's draw a nice card with a solid background and text using FancyBboxPatch
from matplotlib.patches import FancyBboxPatch
card = FancyBboxPatch((0.05, 0.05), 0.9, 0.9, transform=axs[1, 1].transAxes,
                       boxstyle="round,pad=0.03", facecolor='#ffffff', edgecolor='#bdc3c7', linewidth=1)
axs[1, 1].add_patch(card)

total_attempts = len(df)
total_agreed = df['Amount Agreed to Pay Amount'].sum()
total_paid = df['Bill Paid Amount'].sum()

# Add text with formatting
axs[1, 1].text(0.1, 0.85, "KEY PERFORMANCE INDICATORS (KPIs)", fontsize=14, fontweight='bold', color='#1d3557', transform=axs[1, 1].transAxes)

# Total Attempts Card
axs[1, 1].text(0.1, 0.70, "Total Survey Attempts:", fontsize=11, color='#7f8c8d', transform=axs[1, 1].transAxes)
axs[1, 1].text(0.1, 0.62, f"{total_attempts:,} Records", fontsize=18, fontweight='bold', color='#2c3e50', transform=axs[1, 1].transAxes)

# Agreed Amount Card
axs[1, 1].text(0.1, 0.48, "Total Amount Agreed to Pay (Commitment):", fontsize=11, color='#7f8c8d', transform=axs[1, 1].transAxes)
axs[1, 1].text(0.1, 0.40, f"PKR {total_agreed/1e6:.2f} Million (7.33 Crore)", fontsize=18, fontweight='bold', color='#e63946', transform=axs[1, 1].transAxes)

# Paid Amount Card
axs[1, 1].text(0.1, 0.26, "Total Bill Paid Amount (Recovered):", fontsize=11, color='#7f8c8d', transform=axs[1, 1].transAxes)
axs[1, 1].text(0.1, 0.18, f"PKR {total_paid/1e6:.2f} Million (32.55 Lakh)", fontsize=18, fontweight='bold', color='#2a9d8f', transform=axs[1, 1].transAxes)

# Contractor and Region info
axs[1, 1].text(0.1, 0.08, "Contractor: GSMB-SSGC   |   Main Region: Karachi Western", fontsize=9, style='italic', color='#7f8c8d', transform=axs[1, 1].transAxes)

# Add spacing and styling to subplots
plt.subplots_adjust(top=0.88, bottom=0.08, left=0.08, right=0.92, hspace=0.3, wspace=0.3)

# Save the beautifully generated report to disk
plt.savefig(out_img_path, dpi=200, facecolor='#f4f6f9')
print("Successfully generated and saved beautiful dashboard image to:", out_img_path)
