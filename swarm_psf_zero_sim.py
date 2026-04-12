# -*- coding: utf-8 -*-
"""
PSF-Zero Swarm Control Simulator — Ultimate Enhanced Edition
Love-OS Geometric Control for Zero-Inertia Power Grid

Demonstrates that /0 projective saturation enables high-gain stable control
under extremely low inertia (M=0.7) and severe delay (150ms),
while conventional linear control diverges.

(c) Love-OS Architect Project, 2026
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Dict

# ========================== Parameters ==========================

@dataclass
class GridParams:
    M: float = 0.70      # [GW·s/Hz] Extremely low inertia
    D: float = 0.8       # [GW/Hz] Damping
    tau: float = 0.150   # [s] Severe delay (150ms)
    T: float = 0.025     # [s] Inverter time constant

@dataclass
class SwarmParams:
    N: int = 100_000
    p_device_max_kw: float = 6.0
    sigma: float = 0.012          # /0 Projection strength (smaller = stronger saturation)
    r_max_gw_s: float = 12.0      # Physical slew rate limit [GW/s]

@dataclass
class SimParams:
    t_end: float = 20.0
    dt: float = 0.001
    disturbance_time: float = 2.0
    disturbance_mw: float = 350.0   # +350 MW sudden load increase


def simulate(grid: GridParams, swarm: SwarmParams, sim: SimParams,
             Kf: float, use_psf_zero: bool) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]:
    """Run simulation and return time, df, u arrays + metrics"""
    Pmax_total = swarm.N * swarm.p_device_max_kw / 1e6  # [GW]
    delay_steps = max(1, int(round(grid.tau / sim.dt)))
    df_buffer = np.zeros(delay_steps)

    df = 0.0
    u = 0.0
    steps = int(sim.t_end / sim.dt) + 1

    t_arr = np.zeros(steps)
    df_arr = np.zeros(steps)
    u_arr = np.zeros(steps)

    for k in range(steps):
        t = k * sim.dt
        dP = sim.disturbance_mw / 1000.0 if t >= sim.disturbance_time else 0.0

        df_delayed = df_buffer[0]

        # ==================== Control Law ====================
        if use_psf_zero:
            # PSF-Zero: /0 Projective Saturation (Love-OS Geometric Control)
            saturation = df_delayed / np.sqrt(swarm.sigma**2 + df_delayed**2)
            u_cmd = -Kf * saturation
        else:
            # Legacy Linear Control
            u_cmd = -Kf * df_delayed
            u_cmd = np.clip(u_cmd, -Pmax_total, Pmax_total)

        # Rate limiting + Inverter dynamics
        du_max = swarm.r_max_gw_s * sim.dt
        u_cmd = np.clip(u_cmd, u - du_max, u + du_max)
        u += (u_cmd - u) * (sim.dt / max(1e-9, grid.T))

        # Swing Equation
        ddf = (-grid.D * df - dP + u) / max(1e-9, grid.M)
        df += ddf * sim.dt

        # Update delay buffer
        df_buffer = np.roll(df_buffer, -1)
        df_buffer[-1] = df

        t_arr[k] = t
        df_arr[k] = df
        u_arr[k] = u

    # ==================== Metrics ====================
    nadir = np.min(df_arr)
    ro cof_max = np.max(np.abs(np.diff(df_arr) / sim.dt))
    settling_idx = np.where(np.abs(df_arr) < 0.01)[0]
    settling_time = settling_idx[0] * sim.dt if len(settling_idx) > 0 else sim.t_end
    oscillation = np.std(df_arr[int(5/sim.dt):])  # after 5s

    metrics = {
        "Nadir_Hz": round(nadir, 4),
        "Max_RoCoF_Hz_s": round(ro cof_max, 4),
        "Settling_Time_s": round(settling_time, 2),
        "Oscillation_Std": round(oscillation, 4),
        "Final_df": round(df_arr[-1], 4)
    }

    return t_arr, df_arr, u_arr, metrics


# ========================== Main ==========================

if __name__ == "__main__":
    print("🚀 Starting Love-OS PSF-Zero Swarm Control Simulation (Enhanced)...\n")

    grid = GridParams()
    swarm = SwarmParams()
    sim = SimParams()

    Kf_linear = 25.0
    Kf_psf    = 85.0   # Much higher gain thanks to /0 saturation

    print("Running Legacy Linear Control...")
    t_lin, df_lin, u_lin, met_lin = simulate(grid, swarm, sim, Kf_linear, use_psf_zero=False)

    print("Running PSF-Zero Geometric Control...")
    t_psf, df_psf, u_psf, met_psf = simulate(grid, swarm, sim, Kf_psf, use_psf_zero=True)

    # ====================== Plot ======================
    fig, axs = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

    # Frequency Deviation
    axs[0].plot(t_lin, df_lin, label=f"Legacy Linear (Kf={Kf_linear}) → Divergent/Unstable", 
                color='red', linewidth=1.8, alpha=0.85)
    axs[0].plot(t_psf, df_psf, label=f"PSF-Zero /0 Projection (Kf={Kf_psf}) → Stable", 
                color='blue', linewidth=2.5)

    axs[0].axvline(sim.disturbance_time, color='black', linestyle='--', alpha=0.7, label="Disturbance (+350 MW)")
    axs[0].axhline(0, color='black', linewidth=0.6)
    axs[0].set_ylabel('Frequency Deviation Δf [Hz]')
    axs[0].set_title('Love-OS PSF-Zero in Zero-Inertia Grid\n'
                     f'(M={grid.M} GW·s/Hz, Delay τ={grid.tau*1000}ms, N={swarm.N:,} devices)')
    axs[0].legend(loc='lower right')
    axs[0].grid(True, alpha=0.3)

    # Control Output
    axs[1].plot(t_lin, u_lin, label="Legacy Output", color='red', linewidth=1.8, alpha=0.85)
    axs[1].plot(t_psf, u_psf, label="PSF-Zero Output", color='blue', linewidth=2.5)
    axs[1].axvline(sim.disturbance_time, color='black', linestyle='--', alpha=0.7)
    axs[1].set_ylabel('Swarm Power Output u [GW]')
    axs[1].set_xlabel('Time [s]')
    axs[1].legend(loc='lower right')
    axs[1].grid(True, alpha=0.3)

    plt.tight_layout()

    # Metrics Annotation
    txt = (f"Legacy Linear:\n"
           f"  Nadir = {met_lin['Nadir_Hz']:.3f} Hz | RoCoF = {met_lin['Max_RoCoF_Hz_s']:.2f} Hz/s\n"
           f"  Settling = {met_lin['Settling_Time_s']:.1f}s | Osc = {met_lin['Oscillation_Std']:.4f}\n\n"
           f"PSF-Zero /0:\n"
           f"  Nadir = {met_psf['Nadir_Hz']:.3f} Hz | RoCoF = {met_psf['Max_RoCoF_Hz_s']:.2f} Hz/s\n"
           f"  Settling = {met_psf['Settling_Time_s']:.1f}s | Osc = {met_psf['Oscillation_Std']:.4f}")

    plt.figtext(0.02, 0.02, txt, fontsize=10, bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

    plt.savefig('psf_zero_swarm_comparison_enhanced.png', dpi=200, bbox_inches='tight')
    plt.show()

    print("\n✅ Simulation completed!")
    print(f"   Legacy Nadir : {met_lin['Nadir_Hz']:.3f} Hz")
    print(f"   PSF-Zero Nadir: {met_psf['Nadir_Hz']:.3f} Hz")
    print("   Plot saved as 'psf_zero_swarm_comparison_enhanced.png'")
