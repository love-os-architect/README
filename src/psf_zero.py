# psf_zero.py
# Universal Geometric Head with PSF-Zero triad
# (c) Love-OS Architect Project, 2026. MIT License.

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import Tuple, Optional, Dict

# ---------- Quaternion utilities (right-handed, scalar-first) ----------

def q_normalize(q: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Normalize quaternion [w, x, y, z]."""
    n = np.linalg.norm(q)
    if n < eps:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    return q / n

def q_conj(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array([w, -x, -y, -z], dtype=float)

def q_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ], dtype=float)

def q_from_axis_angle(axis: np.ndarray, angle: float, eps: float = 1e-12) -> np.ndarray:
    """Axis-angle -> quaternion (axis must be 3D)."""
    a = np.asarray(axis, dtype=float)
    n = np.linalg.norm(a)
    if n < eps:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    a = a / n
    half = angle * 0.5
    s = np.sin(half)
    return np.array([np.cos(half), a[0]*s, a[1]*s, a[2]*s], dtype=float)

def q_to_axis_angle(q: np.ndarray, eps: float = 1e-12) -> Tuple[np.ndarray, float]:
    """Quaternion -> (axis, angle in [0, π])."""
    qn = q_normalize(q, eps)
    w, x, y, z = qn
    angle = 2.0 * np.arccos(np.clip(w, -1.0, 1.0))
    s = np.sqrt(max(1.0 - w*w, 0.0))
    if s < eps:
        return np.array([1.0, 0.0, 0.0], dtype=float), 0.0
    return np.array([x/s, y/s, z/s], dtype=float), angle

def q_slerp(q0: np.ndarray, q1: np.ndarray, t: float, eps: float = 1e-12) -> np.ndarray:
    """Shortest-path SLERP between two quaternions."""
    q0 = q_normalize(q0, eps)
    q1 = q_normalize(q1, eps)
    dot = float(np.dot(q0, q1))
    
    # Force shortest path
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    if dot > 1.0 - 1e-8:
        # Nearly identical: linear interpolation
        out = q0 + t * (q1 - q0)
        return q_normalize(out)
        
    theta = np.arccos(np.clip(dot, -1.0, 1.0))
    s0 = np.sin((1.0 - t) * theta) / np.sin(theta)
    s1 = np.sin(t * theta) / np.sin(theta)
    return s0*q0 + s1*q1

# ---------- Riemann /0 clamp (projective/Möbius-like saturator) ----------

def mobius_clamp(z: np.ndarray, radius: float = 1.0, eps: float = 1e-12) -> np.ndarray:
    """
    Clamp vector z∈R^n into a ball of radius by a projective map:
      z' = z / (1 + ||z||^2 / r^2)
    This behaves like stereographic/Riemann saturation, projecting infinity safely.
    """
    z = np.asarray(z, dtype=float)
    n2 = float(np.dot(z, z))
    denom = 1.0 + n2 / (radius*radius + eps)
    return z / denom

# ---------- EIT (Exponential Information Tracking) ----------

@dataclass
class EIT:
    """Exponential tracker for orientation (implemented as SLERP with factor alpha)."""
    alpha: float = 0.25  # 0 < alpha <= 1

    def track(self, q_prev: np.ndarray, q_obs: np.ndarray) -> np.ndarray:
        """Blend previous and observed orientation via SLERP(alpha)."""
        a = np.clip(self.alpha, 0.0, 1.0)
        return q_slerp(q_prev, q_obs, a)

# ---------- PSF-Zero parameters ----------

@dataclass
class PSFZeroParams:
    alpha_eit: float = 0.25                  # EIT smoothing factor
    max_delta_rad: float = np.deg2rad(12.0)  # Per-step rotation cap
    abstain_delta_rad: float = np.deg2rad(70.0)
    clamp_radius: float = 1.0
    eps: float = 1e-12

# ---------- PSF-Zero core engine ----------

class PSFZero:
    """
    Universal Geometric Head:
      - /0 clamp: Projective saturator for unstable increments
      - EIT: Exponential tracking on S^3 via SLERP
      - S^3 minimal arc: Shortest-path rotation with per-step cap
      - ABSTAIN: Triggers if |Δφ| exceeds safety threshold
    """
    def __init__(self, params: Optional[PSFZeroParams] = None):
        self.p = params or PSFZeroParams()
        self.q: np.ndarray = np.array([1., 0., 0., 0.], dtype=float)  # Orientation
        self._last_dt: float = 1.0
        self._last_delta_phi: float = 0.0

    @property
    def orientation(self) -> np.ndarray:
        return self.q

    @staticmethod
    def _shortest_delta(q_from: np.ndarray, q_to: np.ndarray) -> Tuple[np.ndarray, float]:
        """Compute shortest rotation Δq = q_to * conj(q_from), return (axis, angle)."""
        dq = q_mul(q_to, q_conj(q_from))
        if dq[0] < 0.0:
            dq = -dq
        axis, angle = q_to_axis_angle(dq)
        return axis, angle

    def step(self,
             q_target_obs: np.ndarray,
             dt: float = 1.0,
             guard_flags: Optional[Dict[str, bool]] = None) -> Dict[str, float]:
        """
        One update step toward observed target orientation.
        Returns metrics dict: {'delta_phi', 'omega', 'abstain', 'cap_applied'}.
        """
        p = self.p
        self._last_dt = max(dt, p.eps)

        # --- EIT over target (Weak measurement) ---
        q_obs = q_normalize(q_target_obs)
        q_eit = EIT(p.alpha_eit).track(self.q, q_obs)

        # --- S^3 Minimal Arc & Angle Estimation ---
        axis, angle = self._shortest_delta(self.q, q_eit)

        # --- /0 clamp: Projective saturation of infinite gradients ---
        axis = mobius_clamp(axis, radius=p.clamp_radius)

        # --- ABSTAIN check ---
        abstain_guard = bool(guard_flags.get("abstain")) if guard_flags else False
        abstain_geom = angle > p.abstain_delta_rad
        abstain = abstain_guard or abstain_geom

        # --- Per-step cap (Over-rotation prevention) ---
        cap_applied = False
        if angle > p.max_delta_rad:
            cap_applied = True
            t = p.max_delta_rad / (angle + p.eps)
            q_next = q_slerp(self.q, q_eit, t)
            delta_phi = p.max_delta_rad
        else:
            q_next = q_eit
            delta_phi = angle

        self.q = q_normalize(q_next)
        self._last_delta_phi = float(delta_phi)
        omega = float(delta_phi / self._last_dt)

        return {
            "delta_phi": self._last_delta_phi,
            "omega": omega,
            "abstain": float(abstain),
            "cap_applied": float(cap_applied)
        }

if __name__ == "__main__":
    head = PSFZero()
    q_t = q_from_axis_angle(np.array([0, 0, 1.]), np.deg2rad(45))
    metrics = head.step(q_t, dt=0.1)
    print("Metrics:", metrics, "Orientation q:", head.orientation)
