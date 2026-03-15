# -*- coding: utf-8 -*-
"""
kuramoto_phase_map.py
Generates the Phase Map for Delayed Stochastic Kuramoto Dynamics (Optical PLL).
"""
import numpy as np
import matplotlib.pyplot as plt

def simulate_kuramoto_delay_fast(N, K, D, tau, tmax, dt, omega_std=0.0, seed=0):
    """Simulates Kuramoto with communication delay using a rolling buffer."""
    rng = np.random.default_rng(seed)
    steps = int(tmax / dt)
    delay_steps = max(1, int(tau / dt))
    
    omega = rng.normal(0.0, omega_std, size=N)
    theta = rng.uniform(-np.pi, np.pi, size=N)
    buffer = np.tile(theta, (delay_steps, 1))
    
    r_trace = []
    
    for k in range(steps):
        theta_delay = buffer[k % delay_steps]
        # Global coupling with delay
        sin_term = np.sin(theta_delay[:, None] - theta[None, :])
        coupling = K * sin_term.mean(axis=0)
        
        # Stochastic noise injection
        dW = rng.normal(0.0, np.sqrt(dt), size=N)
        theta = theta + (omega + coupling) * dt + np.sqrt(2 * D) * dW
        theta = (theta + np.pi) % (2 * np.pi) - np.pi
        
        buffer[k % delay_steps] = theta
        
        # Calculate Order Parameter (r)
        r = np.abs(np.exp(1j * theta).mean())
        r_trace.append(r)
        
    return np.array(r_trace)

def phase_map_fast(K_list, sigma_list, tau, N=32, tmax=1.5, dt=2e-4, Teff=1e-3, seed=0):
    """Sweeps K and Sigma to build the Phase Map grid."""
    print("Simulating Delayed Kuramoto Grid...")
    R = np.zeros((len(K_list), len(sigma_list)))
    for i, K in enumerate(K_list):
        for j, sig in enumerate(sigma_list):
            D = (sig**2) / (2 * Teff) # Map RMS Phase to Diffusion Coefficient
            r_tr = simulate_kuramoto_delay_fast(N, K, D, tau, tmax, dt, seed=seed)
            # Average the steady-state portion
            R[i, j] = r_tr[int(0.5 * len(r_tr)):].mean()
    return R

if __name__ == "__main__":
    # Domain Parameters (Optical Link)
    K_list = np.linspace(0.0, 8.0, 20)           # Loop Gain
    sigma_list = np.linspace(0.05, 0.30, 20)     # RMS Phase Noise [rad]
    tau = 200e-6                                 # 200us Round-trip delay (~40km fiber)
    Teff = 1e-3

    R = phase_map_fast(K_list, sigma_list, tau, N=32, tmax=1.0, dt=2e-4, Teff=Teff, seed=123)

    # Visualization
    Kg, Sg = np.meshgrid(sigma_list, K_list)
    plt.figure(figsize=(8, 6))
    im = plt.pcolormesh(Sg, Kg, R, shading='auto', cmap='viridis', vmin=0, vmax=1)
    cbar = plt.colorbar(im, label='Order parameter $r$')
    
    # r=0.5 Survival Boundary
    cs = plt.contour(Sg, Kg, R, levels=[0.5], colors='w', linewidths=2)
    if len(cs.collections) > 0:
        cs.collections[0].set_linestyle('--')

    plt.xlabel('RMS Phase Noise $\sigma_\phi$ [rad]')
    plt.ylabel('Loop Gain $K$ [arb.]')
    plt.title(f'Love-OS Optical Phase Map (Delay $\\tau$={tau*1e6:.0f} $\mu$s)')
    plt.tight_layout()
    plt.savefig('optical_phase_map_K_sigma.png', dpi=200)
    print("✅ Success! Saved 'optical_phase_map_K_sigma.png'")
