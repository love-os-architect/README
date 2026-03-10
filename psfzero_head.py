# -*- coding: utf-8 -*-
"""
PSF-Zero regularization head — clamp(/0) + EIT + S^3 shortest-arc (quaternions)
Drop-in for VQE/QAOA/ansatz training and pulse-level control.
"""

from __future__ import annotations
import time, math
import numpy as np
from dataclasses import dataclass

@dataclass
class PSFConfig:
    lam: float = 0.10             # EIT (Exponential decay) lambda
    sigma: float = 1.0            # /0 Projection scale (smaller = faster saturation)
    max_phase_jump: float = math.radians(45)  # Anomaly detection threshold
    max_latency_ms: float = 5000.0            # Max allowed latency per step
    use_cayley: bool = True       # Use Cayley transform for quaternion update

class MetricsCollector:
    """Tracks performance metrics: time, normalizations, and matrix/quaternion calls."""
    def __init__(self): self.reset()
    def reset(self):
        self.time_ms = 0.0
        self.renorm_calls = 0
        self.matmul_calls = 0
        self.quatmul_calls = 0
        self.steps = 0
        
    def add_time(self, dt_ms: float): self.time_ms += dt_ms
    def inc_renorm(self): self.renorm_calls += 1
    def inc_matmul(self, n=1): self.matmul_calls += n
    def inc_quatmul(self, n=1): self.quatmul_calls += n
    def inc_step(self): self.steps += 1
    
    def summary(self):
        return {"time_ms": self.time_ms, "steps": self.steps, "renorm_calls": self.renorm_calls, "quatmul_calls": self.quatmul_calls}

def clamp(delta: float, sigma: float = 1.0) -> float:
    """Projective regularization (/0): Smoothly saturates large angle updates."""
    return delta / math.sqrt(sigma*sigma + delta*delta)

def eit(zbar: complex, phi: float, lam: float = 0.10) -> complex:
    """EIT Phase Tracker: Forgets the past, locks into the 'now'."""
    return (1.0 - lam) * zbar + lam * complex(math.cos(phi), math.sin(phi))

def quat_from_axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    ax = np.asarray(axis, dtype=float)
    n = np.linalg.norm(ax)
    if n == 0.0: return np.array([1.0, 0.0, 0.0, 0.0])
    ax = ax / n
    half = 0.5 * angle
    s = math.sin(half)
    return np.array([math.cos(half), *(s * ax)])

def quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quat_normalize(q: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(q))
    if n == 0.0: return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n

def su2_update_minimal_arc(q: np.ndarray, axis: np.ndarray, dtheta: float, cfg: PSFConfig, mc: MetricsCollector) -> np.ndarray:
    """Shortest-arc update: Applies exp(-i dtheta/2 n·σ) via quaternions."""
    dq = quat_from_axis_angle(axis, dtheta)
    mc.inc_quatmul(1)
    q1 = quat_mul(dq, q)
    if cfg.use_cayley:
        q1 = quat_normalize(q1)
        mc.inc_renorm()
    else:
        q1 = quat_normalize(q1)
    return q1

def abstain_guard(metrics: dict, cfg: PSFConfig) -> dict:
    """Returns ABSTAIN / FALLBACK / CONTINUE based on anomaly detection."""
    if metrics.get("max_phase_jump", 0.0) > cfg.max_phase_jump:
        return {"action": "ABSTAIN", "reason": "excess-phase-jump"}
    if metrics.get("latency_ms", 0.0) > cfg.max_latency_ms:
        return {"action": "FALLBACK", "reason": "latency-exceeded"}
    return {"action": "CONTINUE", "reason": ""}

def psfzero_step(q: np.ndarray, grad_axis: np.ndarray, grad_angle: float, zbar: complex, phi: float, cfg: PSFConfig, mc: MetricsCollector | None = None) -> tuple[np.ndarray, complex, dict]:
    t0 = _now_ms()
    
    # 1) /0 Projection
    dtheta = clamp(grad_angle, cfg.sigma)
    # 2) EIT Phase Tracker
    zbar_new = eit(zbar, phi, cfg.lam)
    # 3) S^3 Shortest-arc update
    mc_target = mc or MetricsCollector()
    q_new = su2_update_minimal_arc(q, grad_axis, dtheta, cfg, mc_target)
    
    dt = _now_ms() - t0
    info = {"latency_ms": dt, "applied_angle": dtheta, "max_phase_jump": abs(dtheta)}
    
    if mc:
        mc.add_time(dt)
        mc.inc_step()
        
    return q_new, zbar_new, info
