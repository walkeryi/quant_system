import matplotlib.pyplot as plt
import numpy as np

# 设置温度范围 (20°C 到 100°C)
temperature = np.linspace(20, 100, 100)

# 模拟溶解模型 (基于一阶动力学简化的逻辑曲线)
# 1. 氨基酸 (Amino Acids): 低温下就有不错的溶解度，曲线较平缓
amino_acids = 100 / (1 + np.exp(-0.1 * (temperature - 40)))

# 2. 茶多酚 (Tea Polyphenols): 随温度升高稳定增加，90度后斜率变大
polyphenols = 100 / (1 + np.exp(-0.08 * (temperature - 75)))

# 3. 咖啡碱 (Caffeine): 对高温极度敏感，80度是明显的转折点
caffeine = 100 / (1 + np.exp(-0.15 * (temperature - 85)))

# 绘图
plt.figure(figsize=(10, 6))
plt.plot(temperature, amino_acids, label='Amino Acids (Sweet/Fresh)', color='green', linewidth=2)
plt.plot(temperature, polyphenols, label='Polyphenols (Astringent)', color='orange', linewidth=2)
plt.plot(temperature, caffeine, label='Caffeine (Bitter)', color='red', linewidth=2, linestyle='--')

# 标注你之前的操作区（100度煮沸）
plt.axvline(x=100, color='darkred', alpha=0.3, linestyle=':')
plt.text(92, 95, 'Your Boiling Point', color='darkred', fontweight='bold')

# 标注建议的操作区（85-90度）
plt.axvspan(85, 92, alpha=0.2, color='blue', label='Ideal Extraction Zone')

# 图表装饰
plt.title('Simulated Solubility of Tea Components vs Temperature', fontsize=14)
plt.xlabel('Water Temperature (°C)', fontsize=12)
plt.ylabel('Extraction Percentage (%)', fontsize=12)
plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.6)

plt.show()