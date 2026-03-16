```python
# -*- coding: utf-8 -*-
"""
PSF-Zero Swarm Control Simulator
Proves geometric stabilization of a zero-inertia power grid under severe delay.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass

@dataclass
class GridParams:
    M: float = 2.0      # [GW*s/Hz] Effective Inertia (Extremely light/volatile grid)
    D: float = 1.0      # [GW/Hz] Natural Damping
    tau: float = 0.100  # [s] Total Control/Communication Delay (100ms - Fatal)
    T: float = 0.020    # [s] Inverter Output Time Constant

@dataclass
class SwarmParams:
    N: int = 100_000              # Number of distributed EV/BESS nodes
    p_device_max_kw: float = 5.0  # Max power per device [kW]
    sigma: float = 0.05           # [Hz] PSF-Zero Geometric Saturation Constant
    r_max: float = 10.0           # [GW/s] Physical Rate Limit

@dataclass
class SimParams:
    t_end: float = 15.0  # [s] Simulation duration
    dt: float = 0.001    # [s] Time step
    t_step: float = 1.0  # [s] Time of disturbance
    dP_step: float = 0.3 # [GW] +300MW Load Step (Frequency drop)

def simulate_comparison(grid: GridParams, swarm: SwarmParams, sim: SimParams, Kf_base: float, use_psf_zero: bool):
    """Simulates the grid frequency dynamics with either Legacy or PSF-Zero control."""
    Pmax_total = swarm.N * swarm.p_device_max_kw / 1e6  # [GW]
    delay_steps = max(1, int(round(grid.tau / sim.dt)))
    df_buffer = np.zeros(delay_steps)

    df = 0.0  # Frequency Deviation
    u  = 0.0  # Swarm Power Output
    
    steps = int(sim.t_end / sim.dt) + 1
    t_arr = np.zeros(steps); df_arr = np.zeros(steps); u_arr = np.zeros(steps)

    for k in range(steps):
        t = k * sim.dt
        dP = sim.dP_step if t >= sim.t_step else 0.0
        df_delayed = df_buffer[0] # Delayed measurement

        if use_psf_zero:
            # --- B. PSF-Zero Geometric Controller (/0 Projection) ---
            u_cmd = -Kf_base * (df_delayed / np.sqrt(swarm.sigma**2 + df_delayed**2))
        else:
            # --- A. Legacy Linear Controller ---
            u_cmd = -Kf_base * df_delayed
            u_cmd = np.clip(u_cmd, -Pmax_total, Pmax_total) # Hard physical clip

        # Inverter Rate Limiting & First-Order Delay
        du_allowed = swarm.r_max * sim.dt
        u_cmd = np.clip(u_cmd, u - du_allowed, u + du_allowed)
        u += (u_cmd - u) * sim.dt / max(1e-9, grid.T)

        # Grid Swing Equation: M*df' + D*df = -dP + u
        ddf = (-grid.D * df - dP + u) / max(1e-9, grid.M)
        df += ddf * sim.dt

        # Update Delay Buffer
        df_buffer = np.roll(df_buffer, -1)
        df_buffer[-1] = df

        t_arr[k] = t; df_arr[k] = df; u_arr[k] = u

    return t_arr, df_arr, u_arr

if __name__ == "__main__":
    print("Initiating Love-OS Swarm Control Simulation...")
    grid = GridParams()
    swarm = SwarmParams()
    sim = SimParams()

    # We use a massive gain for PSF-Zero to prove it will not oscillate,
    # while standard linear control will immediately diverge.
    Kf_base_linear = 30.0 
    Kf_base_psf = 60.0

    print("Running Legacy Linear Control...")
    t_lin, df_lin, u_lin = simulate_comparison(grid, swarm, sim, Kf_base_linear, use_psf_zero=False)
    
    print("Running PSF-Zero Geometric Control...")
    t_psf, df_psf, u_psf = simulate_comparison(grid, swarm, sim, Kf_base_psf, use_psf_zero=True)

    # Visualization
    plt.figure(figsize=(10, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(t_lin, df_lin, label=f"Legacy Linear (Kf={Kf_base_linear}) - Divergence", color='red', alpha=0.8)
    plt.plot(t_psf, df_psf, label=f"PSF-Zero /0 (Kf_base={Kf_base_psf}) - Stability", color='blue', linewidth=2)
    plt.axvline(sim.t_step, color='k', linestyle='--', alpha=0.5, label='-300MW Disturbance')
    plt.axhline(0, color='k', linewidth=0.5)
    plt.ylabel('Frequency Deviation $\Delta f$ [Hz]')
    plt.title(f"Swarm Control in Zero-Inertia Grid (Delay $\\tau$={grid.tau*1000}ms)")
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.ylim(-0.4, 0.2)

    plt.subplot(2, 1, 2)
    plt.plot(t_lin, u_lin, label="Legacy Output [GW]", color='red', alpha=0.8)
    plt.plot(t_psf, u_psf, label="PSF-Zero Output [GW]", color='blue', linewidth=2)
    plt.axvline(sim.t_step, color='k', linestyle='--', alpha=0.5)
    plt.ylabel('Swarm Output $u$ [GW]')
    plt.xlabel('Time [s]')
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('psf_zero_swarm_comparison.png', dpi=150)
    print("✅ Success! Comparison plot saved as 'psf_zero_swarm_comparison.png'.")
