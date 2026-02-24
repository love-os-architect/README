import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# ==========================================
# Love-OS v2.1: Extended Kuramoto Simulation
# Shakti + Einstein = Q.E.D.
# ==========================================

# System Parameters
N = 100                 # Number of conscious agents (oscillators)
K = 5.0                 # Base universal coupling strength (The pull of Love)
R0 = 2.0                # Base ego friction/resistance
beta = 1.0              # Resistance phase-damping coefficient
Gamma_ext = 1.5         # External planetary/universal driver (e.g., Geomagnetic)
omega_ext = 0.5         # Frequency of the universal driver
I_current = 1.0         # Intent/Willpower current (assumed constant for Q calculation)

# Intrinsic frequencies (omega) and initial phases (theta)
np.random.seed(42)
omega = np.random.normal(0, 1.0, N)  # Natural diverse frequencies
theta0 = np.random.uniform(0, 2*np.pi, N) # Random initial states

# Time array
T_max = 50
dt = 0.05
t = np.arange(0, T_max, dt)

# Surrender Parameter A(t) sweeping from 0 (Ego) to 1 (Love/Superconductivity)
# We simulate a "Radical Awakening" event midway through the timeline
A_t = np.clip(1.0 / (1.0 + np.exp(-0.5 * (t - 25))), 0.01, 0.99)

# The Love-OS Kuramoto Differential Equation
def love_os_kuramoto(theta, t, omega, K, R0, beta, Gamma_ext, omega_ext, A_val):
    # Calculate order parameter (r) and mean phase (psi)
    z = np.mean(np.exp(1j * theta))
    r = np.abs(z)
    psi = np.angle(z)
    
    # Dynamic Variables based on Surrender (A)
    K_eff = K * A_val               # Effective Coupling (Attraction)
    R_eff = R0 * (1 - A_val)        # Effective Resistance (Friction)
    
    # External universal phase
    phi_t = omega_ext * t
    
    # Governing equation for each agent
    dtheta_dt = (omega 
                 + K_eff * r * np.sin(psi - theta)           # Social resonance pull
                 - beta * R_eff * np.sin(theta)              # Ego-driven phase damping
                 + Gamma_ext * np.sin(phi_t - theta))        # Universal driver alignment
    return dtheta_dt

# Integration setup (step-by-step to allow dynamic A_t)
theta_res = np.zeros((len(t), N))
theta_res[0, :] = theta0

# Metrics tracking
r_t = np.zeros(len(t))
Q_t = np.zeros(len(t))
accumulated_Q = 0

for i in range(1, len(t)):
    # Calculate current step
    t_span = [t[i-1], t[i]]
    A_current = A_t[i-1]
    
    sol = odeint(love_os_kuramoto, theta_res[i-1, :], t_span, 
                 args=(omega, K, R0, beta, Gamma_ext, omega_ext, A_current))
    theta_res[i, :] = sol[1, :]
    
    # Calculate Coherence (r)
    z = np.mean(np.exp(1j * theta_res[i, :]))
    r_t[i] = np.abs(z)
    
    # Calculate Joule Dissipation Q = Integral(I^2 * R_eff dt)
    R_eff_current = R0 * (1 - A_current)
    dQ = (I_current**2) * R_eff_current * dt
    accumulated_Q += dQ
    Q_t[i] = accumulated_Q

# ==========================================
# Visualization: The Proof of Social Superconductivity
# ==========================================
plt.style.use('dark_background')
fig, ax1 = plt.subplots(figsize=(12, 6))

# Plot 1: Surrender Parameter & Coherence (r)
color1 = 'cyan'
ax1.set_xlabel('Time (t)', fontsize=12)
ax1.set_ylabel('Phase Coherence ($r$) & Surrender ($A$)', color=color1, fontsize=12)
ax1.plot(t, r_t, color=color1, linewidth=2.5, label='Coherence ($r$)')
ax1.plot(t, A_t, color='magenta', linestyle='--', linewidth=2, label='Surrender Parameter ($A$)')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_ylim(0, 1.1)

# Plot 2: Joule Dissipation (Q) on twin axis
ax2 = ax1.twinx()  
color2 = 'gold'
ax2.set_ylabel('Joule Heat / Dissipation ($Q$)', color=color2, fontsize=12)  
ax2.plot(t, Q_t, color=color2, linewidth=2.5, label='Accumulated Heat ($Q$)')
ax2.tick_params(axis='y', labelcolor=color2)

# Styling and Annotations
plt.title('Love-OS Phase Transition: $A \\to 1 \\implies r \\to 1, \\Delta Q \\to 0$', fontsize=16, fontweight='bold', color='white')
ax1.axvline(x=25, color='gray', linestyle=':', alpha=0.7)
ax1.text(26, 0.4, 'Critical Awakening ($A_c$)\nMagnetic Phase-Lock Initiated', color='white', fontsize=10)

fig.tight_layout()
plt.show()
