#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Love-OS / PSF-Zero: Fusion Plasma Control Simulation
Demonstrates PSF-Zero acting as a geometric pre-head for a Plasma Control System (PCS).
Generates synthetic MHD spikes, applies PSF-Zero, and plots the A/B comparison.
"""

import os
import csv
import time
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Tuple

# =========================================================
# Core Geometry: Quaternions & S^3 Minimal Arcs
# =========================================================

def q_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ], dtype=float)

def q_conj(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array([w, -x, -y, -z], dtype=float)

def q_norm(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q)
    if n == 0.0:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    return q / n

def q_from_axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    a = np.asarray(axis, float)
    na = np.linalg.norm(a)
    if na == 0.0 or angle == 0.0:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    a = a / na
    h = 0.5 * angle
    s = math.sin(h)
    return q_norm(np.array([math.cos(h), *(s * a)], dtype=float))

# =========================================================
# PSF-Zero Engine: /0 Projection + EIT
# =========================================================

def clamp_delta(delta: float, sigma: float = 1.0) -> float:
    """ /0 Projection: Smooth saturation """
    return delta / math.sqrt(sigma*sigma + delta*delta)

def eit(zbar: complex, phi: float, lam: float = 0.1) -> complex:
    """ EIT: Exponential Information Tracking on S^1 """
    return (1.0 - lam) * zbar + lam * complex(math.cos(phi), math.sin(phi))

@dataclass
class PSFZeroCfg:
    lam: float = 0.12
    sigma: float = 0.9
    max_phase_jump: float = math.radians(60)
    max_latency_ms: float = 1.5

@dataclass
class PSFZeroResult:
    q_next: np.ndarray
    dtheta_applied: float
    zbar_next: complex
    action: str
    reason: str
    latency_ms: float

def psfzero_step(q: np.ndarray, phi: float, zbar: complex,
                 grad_axis: np.ndarray, raw_dtheta: float,
                 cfg: PSFZeroCfg) -> PSFZeroResult:
    t0 = time.perf_counter()
    
    # 1. /0 Projection
    dtheta = clamp_delta(raw_dtheta, cfg.sigma)
    
    # 2. EIT Tracking
    zbar_n = eit(zbar, phi, cfg.lam)
    
    # 3. S^3 Geodesic Update
    axis_n = np.asarray(grad_axis, float)
    n = np.linalg.norm(axis_n)
    axis_u = axis_n / n if n > 0 else np.array([0.0, 0.0, 1.0])
    dq = q_from_axis_angle(axis_u, dtheta)
    q_n = q_norm(q_mul(dq, q))
    
    dt_ms = (time.perf_counter() - t0) * 1000.0
    action = "ABSTAIN" if abs(dtheta) > cfg.max_phase_jump else "CONTINUE"
    reason = "excess-phase-jump" if action == "ABSTAIN" else ""
    
    return PSFZeroResult(q_n, dtheta, zbar_n, action, reason, dt_ms)

# =========================================================
# Fusion PCS Adapter Simulation
# =========================================================

@dataclass
class AdapterCfg:
    dt: float = 1e-3
    omega_phi: float = 2.0
    psf: PSFZeroCfg = PSFZeroCfg()
    coil_angle_gain: float = 1.0
    dtheta_clip: float = math.radians(10)

class FusionAdapter:
    def __init__(self, cfg: AdapterCfg = AdapterCfg()):
        self.cfg = cfg
        self.q = q_from_axis_angle(np.array([1.0, 0.0, 0.0]), math.radians(15.0))
        self.phi = 0.0
        self.zbar = complex(1.0, 0.0)
        self.t = 0.0
        self.last_coil_cmd = 0.0

    @staticmethod
    def sensors_to_stimulus(sensor_dict: Dict[str, float]) -> np.ndarray:
        rad = sensor_dict.get("rad", 0.0)
        bdot = sensor_dict.get("bdot", 0.0)
        eci = sensor_dict.get("eci", 0.0)
        v1 = 0.6*rad + 0.3*bdot - 0.1*eci
        v2 = -0.2*rad + 0.7*bdot + 0.3*eci
        s = max(1e-6, abs(v1) + abs(v2))
        return np.array([v1/s, v2/s], dtype=float)

    def step(self, sensors: Dict[str, float]) -> Dict[str, object]:
        c = self.cfg
        v = self.sensors_to_stimulus(sensors)
        axis = np.array([v[0], v[1], 0.2])
        raw_dtheta = np.clip(0.8 * np.linalg.norm(v), -math.pi, math.pi)
        
        # Apply PSF-Zero Pre-Head
        res = psfzero_step(self.q, self.phi, self.zbar, axis, raw_dtheta, c.psf)
        
        phi_next = (self.phi + c.omega_phi * c.dt) % (2 * math.pi)
        dtheta_safe = float(np.clip(res.dtheta_applied, -c.dtheta_clip, c.dtheta_clip))
        coil_cmd = self.last_coil_cmd + c.coil_angle_gain * dtheta_safe
        
        self.q = res.q_next
        self.zbar = res.zbar_next
        self.phi = phi_next
        self.t += c.dt
        self.last_coil_cmd = coil_cmd
        
        return {
            "t": self.t, "raw_dtheta": raw_dtheta, "applied_dtheta": res.dtheta_applied,
            "coil_cmd": coil_cmd, "latency_ms": res.latency_ms
        }

# =========================================================
# Synthetic Data Generation & Execution
# =========================================================

def synthetic_sensors(t: float) -> Dict[str, float]:
    """ Generates base waves with sudden, explosive spikes mimicking ELM/NTM. """
    rad = 0.8 * math.sin(2.1 * t) + 0.2 * math.cos(0.7 * t)
    bdot = 0.6 * math.cos(1.6 * t) + 0.4 * math.sin(1.1 * t)
    eci = 0.5 * math.sin(0.9 * t + 0.4)
    
    # Inject massive spikes
    if int(10.0 * t) % 37 == 0: rad += 2.5
    if int(8.0 * t) % 41 == 0: bdot += 1.8
    if int(12.0 * t) % 53 == 0: eci -= 1.6
    
    rng = np.random.default_rng(42)
    rad += 0.05 * rng.standard_normal()
    bdot += 0.05 * rng.standard_normal()
    eci += 0.05 * rng.standard_normal()
    return {"rad": rad, "bdot": bdot, "eci": eci}

def run_simulation(seconds=10.0, dt=1e-3):
    steps = int(seconds / dt)
    
    # PSF-Zero ON
    cfg_on = AdapterCfg(dt=dt)
    adp_on = FusionAdapter(cfg_on)
    rows_on = []
    
    # PSF-Zero OFF (Baseline Legacy Control)
    cfg_off = AdapterCfg(dt=dt, psf=PSFZeroCfg(lam=0.0, sigma=1e9)) 
    adp_off = FusionAdapter(cfg_off)
    rows_off = []

    for _ in range(steps):
        s_on = synthetic_sensors(adp_on.t)
        rows_on.append(adp_on.step(s_on))
        
        s_off = synthetic_sensors(adp_off.t)
        v = adp_off.sensors_to_stimulus(s_off)
        axis = np.array([v[0], v[1], 0.2])
        raw_dtheta = np.clip(0.8 * np.linalg.norm(v), -math.pi, math.pi)
        
        dq = q_from_axis_angle(axis / np.linalg.norm(axis), raw_dtheta)
        adp_off.q = q_norm(q_mul(dq, adp_off.q))
        adp_off.t += adp_off.cfg.dt
        adp_off.last_coil_cmd += adp_off.cfg.coil_angle_gain * raw_dtheta
        rows_off.append({"t": adp_off.t, "coil_cmd": adp_off.last_coil_cmd})

    df_on = pd.DataFrame(rows_on)
    df_off = pd.DataFrame(rows_off)
    return df_on, df_off

# =========================================================
# Plotting & Metrics
# =========================================================

def plot_results(df_on: pd.DataFrame, df_off: pd.DataFrame):
    os.makedirs("figures", exist_ok=True)
    
    plt.figure(figsize=(11, 4.5))
    plt.plot(df_off["t"], df_off["coil_cmd"], color="#c44e52", lw=1.6, label="OFF (Legacy Control)")
    plt.plot(df_on["t"], df_on["coil_cmd"], color="#4c72b0", lw=1.8, label="ON (PSF-Zero Pre-Head)")
    plt.xlabel("Time [s]")
    plt.ylabel("Coil Command Amplitude [arb.]")
    plt.title("PSF-Zero Disruption Prevention: Geometric Saturation of MHD Spikes")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig("figures/fusion_pcs_comparison.png", dpi=160)
    print("Graph generated: figures/fusion_pcs_comparison.png")

if __name__ == "__main__":
    print("Starting Fusion PCS Simulation...")
    df_on, df_off = run_simulation()
    
    peak_on = df_on["coil_cmd"].abs().max()
    peak_off = df_off["coil_cmd"].abs().max()
    print(f"Metrics -> Peak Amplitude OFF: {peak_off:.1f}")
    print(f"Metrics -> Peak Amplitude ON : {peak_on:.1f} (Reduced by {(1 - peak_on/peak_off)*100:.1f}%)")
    
    plot_results(df_on, df_off)
    print("Simulation Complete. Q.E.D.")
