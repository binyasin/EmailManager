import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

reps = ['Abdullah', 'Mustafa', 'Aamir', 'Siraj', 'Kashif', 'Asif']
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul']

monthly = {
    'Abdullah': [75000, 80000, 70000, 85000, 65000, 88000, 85000],
    'Mustafa':  [125000, 130000, 150000, 145000, 152000, 170000, 180000],
    'Aamir':    [25000, 35000, 60000, 45000, 50000, 52000, 58000],
    'Siraj':    [95000, 105000, 110000, 102000, 106000, 125000, 115000],
    'Kashif':   [35000, 33000, 32000, 36000, 33000, 32500, 38000],
    'Asif':     [46000, 39000, 47000, 48300, 50000, 49000, 53000],
}

ytd_target = {'Abdullah': 1200000, 'Mustafa': 1600000, 'Aamir': 1200000,
              'Siraj': 1000000, 'Kashif': 1350000, 'Asif': 1200000}
ytd_sales = {'Abdullah': 1748000, 'Mustafa': 2652000, 'Aamir': 1525000,
             'Siraj': 1758000, 'Kashif': 1589500, 'Asif': 1532300}

colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948']
outdir = r'C:\Users\DELL LATITUDE 5520\.openclaw\workspace\charts'

plt.rcParams['figure.facecolor'] = 'white'

# 1. Grouped bar: monthly sales by rep
fig, ax = plt.subplots(figsize=(11, 6))
x = np.arange(len(months))
width = 0.13
for i, rep in enumerate(reps):
    ax.bar(x + (i - (len(reps)-1)/2) * width, monthly[rep], width, label=rep, color=colors[i])
ax.set_xlabel('Month')
ax.set_ylabel('Sales (PKR)')
ax.set_title('Monthly Sales by Sales Rep (Jan - Jul)')
ax.set_xticks(x)
ax.set_xticklabels(months)
ax.legend(ncol=3, fontsize=9)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(outdir + r'\1_monthly_sales_by_rep.png', dpi=130)
plt.close()

# 2. YTD Sales vs Target grouped bar
fig, ax = plt.subplots(figsize=(9, 6))
x = np.arange(len(reps))
w = 0.35
b1 = ax.bar(x - w/2, [ytd_target[r] for r in reps], w, label='YTD Target', color='#c9c9c9')
b2 = ax.bar(x + w/2, [ytd_sales[r] for r in reps], w, label='YTD Sales', color='#4e79a7')
ax.set_xlabel('Sales Rep')
ax.set_ylabel('Amount (PKR)')
ax.set_title('YTD Sales vs YTD Target by Rep')
ax.set_xticks(x)
ax.set_xticklabels(reps)
ax.legend()
ax.grid(axis='y', alpha=0.3)
for b in b2:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+30000, f'{b.get_height()/1e6:.2f}M', ha='center', va='bottom', fontsize=8)
plt.tight_layout()
plt.savefig(outdir + r'\2_ytd_sales_vs_target.png', dpi=130)
plt.close()

# 3. Line: monthly total trend
totals = [sum(monthly[r][m] for r in reps) for m in range(len(months))]
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(months, totals, marker='o', linewidth=2.5, color='#e15759', markersize=8)
for m, t in zip(months, totals):
    ax.annotate(f'{t/1e3:.0f}K', (m, t), textcoords='offset points', xytext=(0, 10), ha='center', fontsize=9)
ax.set_xlabel('Month')
ax.set_ylabel('Total Sales (PKR)')
ax.set_title('Total Monthly Sales Trend (Jan - Jul)')
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, max(totals)*1.2)
plt.tight_layout()
plt.savefig(outdir + r'\3_monthly_trend.png', dpi=130)
plt.close()

# 4. Pie: YTD sales share by rep
fig, ax = plt.subplots(figsize=(8, 8))
sales_vals = [ytd_sales[r] for r in reps]
ax.pie(sales_vals, labels=reps, colors=colors, autopct='%1.1f%%', startangle=140,
       textprops={'fontsize': 10})
ax.set_title('YTD Sales Share by Rep')
plt.tight_layout()
plt.savefig(outdir + r'\4_ytd_sales_share_pie.png', dpi=130)
plt.close()

# 5. Horizontal bar: % of target achieved
fig, ax = plt.subplots(figsize=(9, 5))
pct = [ytd_sales[r]/ytd_target[r]*100 for r in reps]
bars = ax.barh(reps, pct, color=colors)
ax.axvline(100, color='red', linestyle='--', linewidth=1.5, label='Target (100%)')
for b, p in zip(bars, pct):
    ax.text(b.get_width()+1, b.get_y()+b.get_height()/2, f'{p:.1f}%', va='center', fontsize=9)
ax.set_xlabel('% of Target Achieved')
ax.set_title('% of YTD Target Achieved by Rep')
ax.legend()
ax.grid(axis='x', alpha=0.3)
ax.set_xlim(0, max(pct)*1.15)
plt.tight_layout()
plt.savefig(outdir + r'\5_pct_target_achieved.png', dpi=130)
plt.close()

# 6. Stacked area: monthly contribution
fig, ax = plt.subplots(figsize=(10, 5.5))
y = np.array([monthly[r] for r in reps])
ax.stackplot(months, y, labels=reps, colors=colors, alpha=0.85)
ax.set_xlabel('Month')
ax.set_ylabel('Sales (PKR)')
ax.set_title('Monthly Sales Contribution (Stacked)')
ax.legend(loc='upper left', fontsize=9)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(outdir + r'\6_stacked_area.png', dpi=130)
plt.close()

print('DONE')
print('totals', totals)
