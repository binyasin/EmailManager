import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

output_dir = r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\temp_attachments"

# ---- DATA ----
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'July']
reps = ['Abdullah', 'Mustafa', 'Aamir', 'Siraj', 'Kashif', 'Asif']

data = {
    'Abdullah': [75000, 80000, 70000, 85000, 65000, 88000, 85000],
    'Mustafa':  [125000, 130000, 150000, 145000, 152000, 170000, 180000],
    'Aamir':    [25000, 35000, 60000, 45000, 50000, 52000, 58000],
    'Siraj':    [95000, 105000, 110000, 102000, 106000, 125000, 115000],
    'Kashif':   [35000, 33000, 32000, 36000, 33000, 32500, 38000],
    'Asif':     [46000, 39000, 47000, 48300, 50000, 49000, 53000],
}

monthly_totals = [401000, 422000, 469000, 461300, 456000, 516500, 529000]
colors = ['#2196F3', '#FF9800', '#4CAF50', '#E91E63', '#9C27B0', '#00BCD4']

# Totals per rep
rep_totals = {r: sum(data[r]) for r in reps}
total_all = sum(rep_totals.values())

# YTD Targets from spreadsheet
ytd_target = 1200000

# ---- Chart 1: Monthly Trend Lines ----
fig, ax = plt.subplots(figsize=(12, 6))
for i, rep in enumerate(reps):
    ax.plot(months, data[rep], marker='o', linewidth=2, color=colors[i], label=rep, markersize=6)

ax.set_title('Monthly Sales Trend by Representative (Jan-Jul 2026)', fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Sales (PKR)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax.legend(loc='upper left', fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
chart1_path = os.path.join(output_dir, 'chart1_monthly_trend.png')
fig.savefig(chart1_path, dpi=150)
plt.close()
print("Chart 1 saved:", chart1_path)

# ---- Chart 2: Total Sales per Rep with Target Line ----
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(reps, [rep_totals[r] for r in reps], color=colors, edgecolor='white')
ax.axhline(y=ytd_target, color='red', linestyle='--', linewidth=2, label=f'YTD Target: PKR {ytd_target:,.0f}')

for bar, val in zip(bars, [rep_totals[r] for r in reps]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15000,
            f'{val/1000:.0f}K', ha='center', fontsize=9, fontweight='bold')

ax.set_title('YTD Sales by Representative vs Target (Jan-Jul 2026)', fontsize=14, fontweight='bold')
ax.set_ylabel('Total Sales (PKR)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax.legend()
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
chart2_path = os.path.join(output_dir, 'chart2_rep_totals.png')
fig.savefig(chart2_path, dpi=150)
plt.close()
print("Chart 2 saved:", chart2_path)

# ---- Chart 3: Monthly Totals Bar Chart ----
fig, ax = plt.subplots(figsize=(10, 5))
gradient = plt.cm.Blues(np.linspace(0.4, 0.9, len(months)))
bars = ax.bar(months, monthly_totals, color=gradient, edgecolor='white')

for bar, val in zip(bars, monthly_totals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5000,
            f'{val/1000:.0f}K', ha='center', fontsize=10, fontweight='bold')

ax.set_title('Total Monthly Sales (Jan-Jul 2026)', fontsize=14, fontweight='bold')
ax.set_ylabel('Total Sales (PKR)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
chart3_path = os.path.join(output_dir, 'chart3_monthly_totals.png')
fig.savefig(chart3_path, dpi=150)
plt.close()
print("Chart 3 saved:", chart3_path)

# ---- Chart 4: Share of Total Pie ----
fig, ax = plt.subplots(figsize=(8, 8))
wedges, texts, autotexts = ax.pie(
    [rep_totals[r] for r in reps],
    labels=reps,
    colors=colors,
    autopct='%1.1f%%',
    startangle=140,
    explode=(0.02, 0.08, 0.02, 0.05, 0.02, 0.02)
)
for t in autotexts:
    t.set_fontsize(10)
    t.set_fontweight('bold')
ax.set_title('Sales Contribution by Representative (Jan-Jul 2026)', fontsize=14, fontweight='bold')
plt.tight_layout()
chart4_path = os.path.join(output_dir, 'chart4_share_pie.png')
fig.savefig(chart4_path, dpi=150)
plt.close()
print("Chart 4 saved:", chart4_path)

# ---- Chart 5: Performance vs Average ----
avg_monthly = sum(monthly_totals) / len(months)
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(months, monthly_totals, color=['#4CAF50' if v >= avg_monthly else '#FF5722' for v in monthly_totals], edgecolor='white')
ax.axhline(y=avg_monthly, color='blue', linestyle='--', linewidth=2, label=f'Average: PKR {avg_monthly:,.0f}')

for i, val in enumerate(monthly_totals):
    diff = val - avg_monthly
    symbol = '+' if diff >= 0 else ''
    ax.text(i, val + 5000, f'{symbol}{diff/1000:.0f}K', ha='center', fontsize=9,
            color='green' if diff >= 0 else 'red')

ax.set_title('Monthly Performance vs Average (Jan-Jul 2026)', fontsize=14, fontweight='bold')
ax.set_ylabel('Total Sales (PKR)')
ax.set_xticks(range(len(months)))
ax.set_xticklabels(months)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax.legend()
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
chart5_path = os.path.join(output_dir, 'chart5_vs_avg.png')
fig.savefig(chart5_path, dpi=150)
plt.close()
print("Chart 5 saved:", chart5_path)

# ---- Summary Stats ----
print("\n=== SALES SUMMARY ===")
print(f"Total Sales (Jan-Jul): PKR {total_all:,}")
print(f"Monthly Average: PKR {avg_monthly:,.0f}")
print(f"Best Month: {months[monthly_totals.index(max(monthly_totals))]} (PKR {max(monthly_totals):,})")
print(f"Worst Month: {months[monthly_totals.index(min(monthly_totals))]} (PKR {min(monthly_totals):,})")
print(f"Growth (Jan to July): {((monthly_totals[-1] - monthly_totals[0]) / monthly_totals[0] * 100):.1f}%")

top_rep = max(rep_totals, key=rep_totals.get)
print(f"Top Performer: {top_rep} (PKR {rep_totals[top_rep]:,} - {rep_totals[top_rep]/total_all*100:.1f}%)")

bottom_rep = min(rep_totals, key=rep_totals.get)
print(f"Lowest Performer: {bottom_rep} (PKR {rep_totals[bottom_rep]:,} - {rep_totals[bottom_rep]/total_all*100:.1f}%)")

# Aamir specific
aamir_total = rep_totals['Aamir']
aamir_last_month = data['Aamir'][-1]
aamir_first_month = data['Aamir'][0]
print(f"\nAamir Growth: {(aamir_last_month - aamir_first_month) / aamir_first_month * 100:.1f}% (from Jan to July)")

print("\nDone! All charts generated.")
