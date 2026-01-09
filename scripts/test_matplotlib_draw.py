import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.figure(figsize=(4, 3))
ax = plt.gca()
ax.add_patch(Rectangle((0.1, 0.1), 0.8, 0.6, facecolor="#004CD4", edgecolor="black"))
ax.text(0.5, 0.5, "Test", ha="center", va="center", color="white", fontsize=16)
ax.axis("off")
plt.savefig("tmp_test_matplotlib.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved")
