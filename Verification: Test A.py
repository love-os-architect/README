import numpy as np
import matplotlib.pyplot as plt

# --- Physical Constants (SI Units) ---
G = 6.67430e-11  # Gravitational Constant
M = 5.972e24     # Mass of Earth
R_earth = 6.371e6 # Radius of Earth
c = 2.99792458e8 # Speed of Light

def calculate_love_os_parameters(altitude):
    """
    Calculates the Love-OS Phase Angle (theta) and the Time Shadow (cos theta).
    Accounts for both Gravitational (GR) and Kinematic (SR) effects.
    """
    r = R_earth + altitude
    
    # 1. Gravitational Potential Term (General Relativity)
    # g00 = 1 - 2GM/rc^2
    g00 = 1 - (2 * G * M) / (r * c**2)
    
    # 2. Orbital Velocity Term (Special Relativity)
    # v = sqrt(GM/r) for a circular orbit
    v_sq = (G * M) / r
    velocity_factor = 1 - (v_sq / c**2)
    
    # 3. Combined Lapse Factor (The Shadow Length)
    # cos(theta) = sqrt(g00 * velocity_factor)
    cos_theta = np.sqrt(g00 * velocity_factor)
    
    # 4. Phase Angle theta (Radians -> Degrees)
    theta_rad = np.arccos(cos_theta)
    theta_deg = np.degrees(theta_rad)
    
    return cos_theta, theta_deg

# --- Run Simulation ---
altitudes = np.linspace(0, 25000000, 500) # From surface to 25,000km
cos_thetas = []
thetas = []

for alt in altitudes:
    ct, th = calculate_love_os_parameters(alt)
    cos_thetas.append(ct)
    thetas.append(th)

# Precise calculation for GPS Orbit (approx. 20,200 km)
gps_alt = 20200000
gps_cos, gps_theta = calculate_love_os_parameters(gps_alt)
ground_cos, ground_theta = calculate_love_os_parameters(0)

# Calculate daily drift in microseconds
diff_sec_per_day = (gps_cos - ground_cos) * 86400
micro_sec_per_day = diff_sec_per_day * 1e6

# --- Visualization ---
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Altitude (km)')
ax1.set_ylabel('Love-OS Phase Angle θ (degrees)', color=color)
ax1.plot(altitudes/1000, thetas, color=color, linewidth=2, label='Phase Angle θ')
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, which='both', linestyle='--', alpha=0.5)

ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('Shadow of Time (cos θ)', color=color)
ax2.plot(altitudes/1000, cos_thetas, color=color, linestyle='--', alpha=0.7, label='Time Projection (cos θ)')
ax2.tick_params(axis='y', labelcolor=color)

# Plotting the GPS Point
ax1.plot(gps_alt/1000, gps_theta, 'ko')
ax1.annotate(f'GPS Orbit\nθ ≈ {gps_theta:.6f}°', xy=(gps_alt/1000, gps_theta), 
             xytext=(gps_alt/1000 - 8000, gps_theta + 0.0005),
             arrowprops=dict(facecolor='black', shrink=0.05))

plt.title('Love-OS Simulation: Phase Tilt vs Altitude\n(Verification of cos θ ≡ √g₀₀)')
fig.tight_layout()
plt.show()

print(f"--- Verification Result ---")
print(f"Ground Phase θ: {ground_theta:.8f}°")
print(f"GPS Orbit Phase θ: {gps_theta:.8f}°")
print(f"Phase Delta: {gps_theta - ground_theta:.8f}°")
print(f"Calculated Net Drift: {micro_sec_per_day:.2f} μs/day")
print(f"(Standard GR expectation: ~38 μs/day)")
