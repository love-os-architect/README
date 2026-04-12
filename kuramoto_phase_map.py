# -*- coding: utf-8 -*-
"""
kuramoto_phase_map.py — Love-OS Final Enhanced Edition

Delayed Stochastic Kuramoto Dynamics with PSF-Zero / EIT Influence
Generates the Phase Map (K vs σ_φ) for optical PLL / coherent communication systems.
Visualizes the boundary between synchronization (love) and desynchronization (ego).
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple

# ====================== PSF-Zero Inspired Projection ======================
def zero_clamp(x: np.ndarray, tau: float = 1.0) -> np.ndarray:
    """ /0 Projective Clamp: safely bounds large values """
    x = np.asarray(x, dtype=float)
    return x / np.sqrt(1.0 + (x / tau)**2)


# ====================== Fast Delayed Kuramoto Simulator ======================
@dataclass
class KuramotoConfig:
    N: int = 64
    tau: float = 200e-6      # round-trip delay [s]
    dt: float = 2e-4
    tmax: float = 2.0
    Teff: float = 1e-3       # effective temperature scaling
    seed: int = 42


def simulate_kuramoto(K: float, sigma: float, cfg: KuramotoConfig) -> np.ndarray:
    """Fast vectorized simulation of delayed stochastic Kuramoto model"""
    rng = np.random.default_rng(cfg.seed)
    steps = int(cfg.tmax / cfg.dt)
    delay_steps = max(1, int(cfg.tau / cfg.dt))

    omega = rng.normal(0.0, sigma, size=cfg.N)
    theta = rng.uniform(-np.pi, np.pi, size=cfg.N)

    # Delay buffer
    buffer = np.tile(theta, (delay_steps, 1))
    r_trace = np.zeros(steps)

    for k in range(steps):
        theta_delay = buffer[k % delay_steps]

        # Global coupling with delay
        dtheta = theta_delay[:, None] - theta[None, :]
        coupling = K * np.sin(dtheta).mean(axis=0)

        # Stochastic update with /0-inspired clamping on noise
        dW = rng.normal(0.0, np.sqrt(cfg.dt), size=cfg.N)
        noise = np.sqrt(2 * (sigma**2) / (2 * cfg.Teff)) * dW
        noise = zero_clamp(noise, tau=0.8)   # PSF-Zero style noise suppression

        theta += (omega + coupling) * cfg.dt + noise
        theta = (theta + np.pi) % (2 * np.pi) - np.pi

        # Update delay buffer
        buffer[k % delay_steps] = theta

        # Order parameter r
        r_trace[k] = np.abs(np.exp(1j * theta).mean())

    return r_trace


def generate_phase_map(K_list: np.ndarray, 
                       sigma_list: np.ndarray, 
                       cfg: KuramotoConfig = KuramotoConfig()) -> np.ndarray:
    """Generate 2D phase map: r(K, σ)"""
    print(f"Generating Love-OS Optical Phase Map ({len(K_list)}×{len(sigma_list)} grid)...")
    
    R = np.zeros((len(K_list), len(sigma_list)))

    for i, K in enumerate(K_list):
        for j, sigma in enumerate(sigma_list):
            r_trace = simulate_kuramoto(K, sigma, cfg)
            # Use steady-state average (discard transient)
            R[i, j] = r_trace[int(0.4 * len(r_trace)):].mean()

    return R


# ====================== Visualization ======================
def plot_phase_map(K_list: np.ndarray, 
                   sigma_list: np.ndarray, 
                   R: np.ndarray, 
                   tau: float):
    plt.figure(figsize=(10, 8))

    Kg, Sg = np.meshgrid(sigma_list, K_list)
    im = plt.pcolormesh(Sg, Kg, R, shading='auto', cmap='plasma', vmin=0.0, vmax=1.0)

    cbar = plt.colorbar(im, label='Order Parameter $r$ (Phase Synchrony)')
    cbar.set_label('Order Parameter $r$', rotation=270, labelpad=20)

    # Critical boundary r = 0.5 (synchronization threshold)
    cs = plt.contour(Sg, Kg, R, levels=[0.5], colors='white', linewidths=2.2, linestyles='--')
    plt.clabel(cs, inline=True, fontsize=10, fmt='r=0.5')

    plt.xlabel('RMS Phase Noise $\\sigma_\\phi$ [rad]')
    plt.ylabel('Loop Gain $K$ [arb. units]')
    plt.title(f'Love-OS Optical Phase Map — Delayed Kuramoto Dynamics\n'
              f'(Delay $\\tau$ = {tau*1e6:.0f} $\\mu$s | PSF-Zero Noise Clamping)')

    plt.grid(True, alpha=0.3, linestyle=':')
    plt.tight_layout()
    plt.savefig('love_os_optical_phase_map.png', dpi=220, bbox_inches='tight')
    plt.show()


# ====================== Main ======================
if __name__ == "__main__":
    print("🚀 Love-OS Kuramoto Phase Map Simulator Starting...\n")

    cfg = KuramotoConfig(N=64, tau=200e-6, tmax=2.0, dt=2e-4)

    K_list = np.linspace(0.0, 10.0, 25)
    sigma_list = np.linspace(0.02, 0.35, 25)

    R = generate_phase_map(K_list, sigma_list, cfg)

    plot_phase_map(K_list, sigma_list, R, cfg.tau)

    # Summary
    sync_area = np.mean(R > 0.5) * 100
    print(f"Phase Map Generated Successfully!")
    print(f"Synchronization Area (r > 0.5): {sync_area:.1f}%")
    print(f"Plot saved as: love_os_optical_phase_map.png")
    print("\n→ In Love-OS, high K and low σ_φ correspond to the 'Genesis Axis' region.")
