### 2. SVG Diagram Generation Script (Python)

Run this Python script to generate the three SVG files (`stereographic.svg`, `hopf_fibration.svg`, `genesis_axis.svg`). You can place them in a `docs/images/` directory and link them in the Markdown.

```python
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# --- Common Settings ---
plt.rcParams['svg.fonttype'] = 'none'

def create_stereographic_svg():
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_axis_off()

    # S^2 Sphere
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi, 60)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x, y, z, color='lightblue', alpha=0.3, edgecolor='none')

    # Complex Plane C
    xx, yy = np.meshgrid(np.linspace(-3, 3, 10), np.linspace(-3, 3, 10))
    zz = np.zeros_like(xx)
    ax.plot_surface(xx, yy, zz, color='lightgray', alpha=0.4)

    # North Pole N
    ax.scatter([0], [0], [1], color='red', s=100, label='North Pole (N) = /0')
    
    # Projection lines
    points_on_plane = [[2, 2, 0], [-2, 1, 0], [0, -2.5, 0]]
    for p in points_on_plane:
        ax.plot([0, p[0]], [0, p[1]], [1, p[2]], 'k--', alpha=0.6)
        ax.scatter([p[0]], [p[1]], [p[2]], color='blue', s=30)

    ax.set_title("1. Stereographic Projection (/0 accepting Infinity)", pad=20)
    plt.tight_layout()
    plt.savefig("stereographic.svg", format='svg', transparent=True)
    plt.close()

def create_hopf_svg():
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_axis_off()

    # Torus rings representing the Hopf link (S^1 fibers)
    t = np.linspace(0, 2*np.pi, 100)
    for phi in [0, np.pi/3, 2*np.pi/3]:
        # Villarceau circles (simplified representation)
        x = np.cos(t) * np.cos(phi) - np.sin(t) * np.sin(phi) * 0.5
        y = np.sin(t) * np.cos(phi) + np.cos(t) * np.sin(phi) * 0.5
        z = np.sin(t) * 0.866
        ax.plot(x, y, z, linewidth=2, label=f'S¹ Fiber {int(np.degrees(phi))}°')

    ax.scatter([0], [0], [-1.5], color='black', s=50)
    ax.text(0, 0, -1.8, r"Projection to Base $S^2$", ha='center')
    for i in range(3):
        ax.plot([0, 0], [0, 0], [-0.8, -1.5], 'k:', alpha=0.3)

    ax.set_title("2. Hopf Fibration (S¹ Fibers mapped to S² Base)", pad=20)
    plt.tight_layout()
    plt.savefig("hopf_fibration.svg", format='svg', transparent=True)
    plt.close()

def create_genesis_axis_svg():
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_axis_off()

    # Sphere wireframe
    u = np.linspace(0, 2 * np.pi, 40)
    v = np.linspace(0, np.pi, 40)
    ax.plot_wireframe(np.outer(np.cos(u), np.sin(v)), 
                      np.outer(np.sin(u), np.sin(v)), 
                      np.outer(np.ones(np.size(u)), np.cos(v)), 
                      color='gray', alpha=0.1)

    # Genesis Axis (Z-axis)
    ax.plot([0, 0], [0, 0], [-1.5, 1.5], 'r-', linewidth=3, label='Genesis Axis')
    ax.scatter([0], [0], [1], color='red', s=100) # N
    ax.text(0.1, 0, 1.1, 'N (/0)', color='red', fontsize=12)
    ax.scatter([0], [0], [0], color='blue', s=50) # Origin
    ax.text(0.1, 0, -0.1, 'Origin', color='blue', fontsize=12)

    # Orbiting phase S^1 (Rectification via EIT)
    t = np.linspace(0, 4*np.pi, 200)
    z = np.linspace(-1, 1, 200)
    x = np.cos(t) * (1 - abs(z)) * 0.8
    y = np.sin(t) * (1 - abs(z)) * 0.8
    ax.plot(x, y, z, 'b-', linewidth=2, alpha=0.7)

    ax.set_title("3. The Genesis Axis & Phase Rotation (EIT/S³)", pad=20)
    plt.tight_layout()
    plt.savefig("genesis_axis.svg", format='svg', transparent=True)
    plt.close()

if __name__ == "__main__":
    create_stereographic_svg()
    create_hopf_svg()
    create_genesis_axis_svg()
    print("SVG diagrams generated successfully.")


```
