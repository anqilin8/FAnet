# 5_metrics_comparison_pro.py
# 5项指标对比神器（mAP, Accuracy, Dice, 耗时, FPS）
# 运行一次 → 4张顶级论文图 + PDF（投CEA秒过）

import matplotlib.pyplot as plt
import numpy as np
from math import pi
import os
from pathlib import Path

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 数据（直接改你的真实数据） ====================
methods = ['U-Net', 'Psnet', 'WeedNet-X', 'Ours']
map_crop = [91.83, 89.65, 72.14, 98.49]
acc_weed = [65.60, 69.67, 50.21, 90.97]
dice_weed = [0.68, 0.72, 0.59, 0.87]
time_ms = [65.4, 97.1, 48.9, 34.7]  # 耗时越短越好
fps = [15.3, 10.3, 20.5, 29.1]  # FPS越高越好
# =================================================================

x = np.arange(len(methods))
Path("5_metrics").mkdir(exist_ok=True)

# ==================== 图1：三大精度指标柱状图 ====================
fig, ax = plt.subplots(figsize=(12, 8))
bar_width = 0.25
ax.bar(x - bar_width, map_crop, bar_width, label='mAP (Crop %)', color='#1f77b4', edgecolor='black')
ax.bar(x, acc_weed, bar_width, label='Accuracy (Weed %)', color='#ff7f0e', edgecolor='black')
ax.bar(x + bar_width, [d * 100 for d in dice_weed], bar_width, label='Dice (Weed %)', color='#2ca02c',
       edgecolor='black')

ax.set_xlabel('Methods', fontsize=16, fontweight='bold')
ax.set_ylabel('Performance (%)', fontsize=16, fontweight='bold')
ax.set_title('Segmentation Accuracy Comparison', fontsize=20, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods, fontsize=14)
ax.legend(fontsize=14)
ax.grid(True, axis='y', linestyle='--', alpha=0.7)

for i, v in enumerate(zip(map_crop, acc_weed, [d * 100 for d in dice_weed])):
    ax.text(i - bar_width, v[0] + 1, f'{v[0]:.1f}', ha='center', fontsize=12, fontweight='bold')
    ax.text(i, v[1] + 1, f'{v[1]:.1f}', ha='center', fontsize=12, fontweight='bold')
    ax.text(i + bar_width, v[2] + 1, f'{v[2]:.1f}', ha='center', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig("5_metrics/fig1_accuracy_comparison.png", dpi=400, bbox_inches='tight')
plt.savefig("5_metrics/fig1_accuracy_comparison.pdf", bbox_inches='tight')
plt.show()

# ==================== 图2：实时性对比（耗时 + FPS双Y轴） ====================
fig, ax1 = plt.subplots(figsize=(11, 7))
bars = ax1.bar(methods, time_ms, color='#d62728', alpha=0.8, edgecolor='black', label='Time (ms)')
ax1.set_ylabel('Inference Time (ms)', color='#d62728', fontsize=16, fontweight='bold')
ax1.tick_params(axis='y', labelcolor='#d62728')
ax1.set_ylim(0, max(time_ms) * 1.2)

ax2 = ax1.twinx()
line = ax2.plot(methods, fps, 'o-', color='#2ca02c', linewidth=4, markersize=12, label='FPS')
ax2.set_ylabel('FPS', color='#2ca02c', fontsize=16, fontweight='bold')
ax2.tick_params(axis='y', labelcolor='#2ca02c')
ax2.set_ylim(0, max(fps) * 1.3)

ax1.set_title('Real-Time Performance (Lower Time & Higher FPS = Better)', fontsize=18, fontweight='bold')
ax1.set_xlabel('Methods', fontsize=16, fontweight='bold')

# 标注数值
for i, (t, f) in enumerate(zip(time_ms, fps)):
    ax1.text(i, t + 3, f'{t:.1f}ms', ha='center', fontsize=13, fontweight='bold', color='#d62728')
    ax2.text(i, f + 1, f'{f:.1f}', ha='center', fontsize=13, fontweight='bold', color='#2ca02c')

# 图例合并
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc='upper left', fontsize=14)

plt.tight_layout()
plt.savefig("5_metrics/fig2_realtime_comparison.png", dpi=400, bbox_inches='tight')
plt.savefig("5_metrics/fig2_realtime_comparison.pdf", bbox_inches='tight')
plt.show()

# ==================== 图3：精度 vs 实时性散点图（你的杀手锏） ====================
fig, ax = plt.subplots(figsize=(10, 8))
sizes = [200 if m != 'Ours' else 500 for m in methods]
colors = ['red' if m != 'Ours' else 'green' for m in methods]

scatter = ax.scatter(time_ms, dice_weed, s=sizes, c=colors, alpha=0.8, edgecolors='black', linewidth=2)
for i, method in enumerate(methods):
    ax.annotate(method, (time_ms[i], dice_weed[i]),
                xytext=(5, 5), textcoords='offset points', fontsize=14, fontweight='bold')

ax.set_xlabel('Inference Time per Frame (ms)', fontsize=16, fontweight='bold')
ax.set_ylabel('Weed Dice Coefficient', fontsize=16, fontweight='bold')
ax.set_title('Trade-off between Accuracy and Real-Time Performance\n(Ours achieves best balance)',
             fontsize=18, fontweight='bold', pad=20)
ax.grid(True, linestyle='--', alpha=0.7)
ax.invert_xaxis()  # 耗时越短越好，X轴反向

plt.tight_layout()
plt.savefig("5_metrics/fig3_accuracy_vs_speed.png", dpi=400, bbox_inches='tight')
plt.savefig("5_metrics/fig3_accuracy_vs_speed.pdf", bbox_inches='tight')
plt.show()

# ==================== 图4：5维雷达图（每个维度独立归一化） ====================
categories = ['mAP (Crop)', 'Weed Acc', 'Weed Dice', 'FPS', 'Time (Lower Better)']
N = len(categories)

# 每个维度上下界
bounds = [
    (70, 100),  # mAP
    (50, 95),  # Acc
    (0.5, 0.95),  # Dice
    (10, 35),  # FPS (higher better)
    (100, 30)  # Time ms (lower better → 反向归一化)
]

angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

for i, method in enumerate(methods):
    raw_vals = [map_crop[i], acc_weed[i], dice_weed[i], fps[i], time_ms[i]]
    normalized = []
    for j, val in enumerate(raw_vals):
        low, high = bounds[j]
        if j == 4:  # Time越低越好，反向归一化
            val = high + low - val
        normalized.append(100 * (val - low) / (high - low))
    normalized += normalized[:1]

    ax.plot(angles, normalized, 'o-', linewidth=3, label=method,
            color=['#d62728', '#ff7f0e', '#bcbd22', '#2ca02c'][i])
    ax.fill(angles, normalized, alpha=0.25)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=14, fontweight='bold')
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels([], fontsize=12)
ax.grid(True)
ax.set_title("5D Performance Radar Chart\n(Each dimension independently normalized)\n"
             "Proposed method dominates in all metrics",
             fontsize=18, fontweight='bold', pad=40)

ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=14)

plt.tight_layout()
plt.savefig("5_metrics/fig4_5d_radar.png", dpi=400, bbox_inches='tight')
plt.savefig("5_metrics/fig4_5d_radar.pdf", bbox_inches='tight')
plt.show()

print("所有5项指标对比图已生成在 5_metrics 文件夹！直接插论文，审稿人看了直呼专业！")