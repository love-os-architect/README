from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import Tuple, Optional, Dict

# ====================== Quaternion Utilities ======================
def q_normalize(q: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(q)
    return q / n if n > eps else np.array([1.0, 0.0, 0.0, 0.0], dtype=float)

def q_conj(q: np.ndarray) -> np.ndarray:
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=float)

def q_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ], dtype=float)

def q_slerp(q0: np.ndarray, q1: np.ndarray, t: float) -> np.ndarray:
    q0 = q_normalize(q0)
    q1 = q_normalize(q1)
    dot = np.dot(q0, q1)
    if dot < 0:
        q1 = -q1
        dot = -dot
    if dot > 0.999999:
        return q_normalize(q0 + t * (q1 - q0))
    theta = np.arccos(np.clip(dot, -1.0, 1.0))
    return np.sin((1-t)*theta)/np.sin(theta) * q0 + np.sin(t*theta)/np.sin(theta) * q1

# ====================== /0 Projective Clamp ======================
def mobius_clamp(z: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """
    Riemann /0 projective saturation.
    Safely dampens infinite gradients by mapping them into a bounded geometric ball.
    """
    z = np.asarray(z, dtype=float)
    n2 = np.dot(z, z)
    return z / (1.0 + n2 / (radius * radius))

# ====================== EIT (Exponential Information Tracking) ======================
@dataclass
class EIT:
    alpha: float = 0.25

    def track(self, q_prev: np.ndarray, q_obs: np.ndarray) -> np.ndarray:
        return q_slerp(q_prev, q_obs, self.alpha)

# ====================== Params & Core Engine ======================
@dataclass
class PSFZeroParams:
    alpha_eit: float = 0.25
    max_delta_rad: float = np.deg2rad(15.0)   # Smooth structural cap
    abstain_delta_rad: float = np.deg2rad(75.0)
    clamp_radius: float = 0.5                 # Tightened for stronger /0 effect

class PSFZero:
    """
    Love-OS Universal Geometric Head 
    — Zero Friction Orientation Control via S^3 Möbius Projection.
    """

    def __init__(self, params: Optional[PSFZeroParams] = None):
        self.p = params or PSFZeroParams()
        self.eit = EIT(self.p.alpha_eit)
        self.q = np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
        self._last_delta_phi = 0.0

    def step(self, q_target_obs: np.ndarray, dt: float = 1.0,
             force_abstain: bool = False) -> Dict[str, float]:

        q_obs = q_normalize(q_target_obs)
        q_eit = self.eit.track(self.q, q_obs)

        # 1. Shortest geodesic difference on S^3
        dq = q_mul(q_eit, q_conj(self.q))
        if dq[0] < 0:
            dq = -dq
            
        angle_raw = 2.0 * np.arccos(np.clip(dq[0], -1.0, 1.0))

        # 2. The /0 Clamp (Projective Saturation) in action
        # Extract the rotational vector part and apply the Möbius clamp
        v_raw = dq[1:]
        v_clamped = mobius_clamp(v_raw, self.p.clamp_radius)

        # Reconstruct the safe rotation quaternion after clamping
        v_norm2 = np.dot(v_clamped, v_clamped)
        w_clamped = np.sqrt(max(0.0, 1.0 - v_norm2))
        dq_clamped = np.array([w_clamped, v_clamped[0], v_clamped[1], v_clamped[2]])
        
        angle_clamped = 2.0 * np.arccos(np.clip(dq_clamped[0], -1.0, 1.0))

        # 3. ABSTAIN (Zero-Time ∞/∞ guard)
        abstain = force_abstain or (angle_clamped > self.p.abstain_delta_rad)

        # 4. Final Safe Step with absolute architectural cap
        if angle_clamped > self.p.max_delta_rad:
            t = self.p.max_delta_rad / (angle_clamped + 1e-12)
            dq_final = q_slerp(np.array([1.0, 0.0, 0.0, 0.0]), dq_clamped, t)
            delta_phi = self.p.max_delta_rad
            cap_applied = True
        else:
            dq_final = dq_clamped
            delta_phi = angle_clamped
            cap_applied = False

        # 5. Apply the synchronized rotation
        self.q = q_normalize(q_mul(dq_final, self.q))
        self._last_delta_phi = float(delta_phi)

        return {
            "delta_phi": delta_phi,
            "omega": delta_phi / max(dt, 1e-12),
            "abstain": float(abstain),
            "cap_applied": float(cap_applied),
            "angle_raw": float(angle_raw),
            "angle_clamped": float(angle_clamped)
        }

    @property
    def orientation(self) -> np.ndarray:
        return self.q.copy()
