# cone_model.py
# Affective Cone state management on S^3
# (c) Love-OS Architect Project, 2026. MIT License.

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from typing import Optional, Dict

from psf_zero import (
    PSFZero, PSFZeroParams,
    q_from_axis_angle, q_mul, q_normalize
)

@dataclass
class ConeParams:
    theta_max: float = np.deg2rad(55.0)   # Max opening angle
    theta_tau: float = 0.35               # Theta primary-delay lag constant (sec)
    omega_max: float = np.deg2rad(2*180)  # Max precession velocity [rad/s]
    omega_tau: float = 0.25               # Omega primary-delay lag constant (sec)
    vol_floor: float = 0.0                # Volume floor
    vol_ceil: float = 1.0                 # Volume ceiling
    eps: float = 1e-12

class AffectiveCone:
    """
    Affective Cone = (base axis n, opening θ, precession ω, orientation q)
    - θ, ω follow via primary-delay (low-pass filter)
    - Orientation q is safely updated via PSF-Zero (Δφ cap / ABSTAIN)
    - volume = 1 - cos(θ) represents "Affective Volume"
    """
    def __init__(self,
                 base_axis: np.ndarray = np.array([0., 0., 1.], dtype=float),
                 cone_params: Optional[ConeParams] = None,
                 psf_params: Optional[PSFZeroParams] = None):
        self.p = cone_params or ConeParams()
        self.n = self._normalize3(base_axis)
        self.theta = 0.0   # Current opening angle
        self.omega = 0.0   # Current precession velocity
        self.head = PSFZero(psf_params)  # Handles orientation q safely
        self._target_theta = 0.0
        self._target_omega = 0.0

    @staticmethod
    def _normalize3(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
        v = np.asarray(v, dtype=float)
        n = np.linalg.norm(v)
        if n < eps:
            return np.array([0., 0., 1.], dtype=float)
        return v / n

    @property
    def orientation(self) -> np.ndarray:
        return self.head.orientation

    @property
    def volume(self) -> float:
        # Volume = 1 - cos(θ)
        v = 1.0 - np.cos(self.theta)
        return float(np.clip(v, self.p.vol_floor, self.p.vol_ceil))

    def set_target_from_intensity(self, intensity: float, base_axis: Optional[np.ndarray] = None) -> None:
        """Map intensity [0,1] to target θ/ω."""
        intensity = float(np.clip(intensity, 0.0, 1.0))
        if base_axis is not None:
            self.n = self._normalize3(base_axis)
        self._target_theta = intensity * self.p.theta_max
        self._target_omega = intensity * self.p.omega_max

    def step(self,
             dt: float = 0.1,
             guard_flags: Optional[Dict[str, bool]] = None) -> Dict[str, float]:
        """One update step. Returns cone metrics."""
        dt = max(dt, self.p.eps)

        # Primary-delay tracking for θ, ω
        self.theta += (self._target_theta - self.theta) * (1.0 - np.exp(-dt / self.p.theta_tau))
        self.omega += (self._target_omega - self.omega) * (1.0 - np.exp(-dt / self.p.omega_tau))

        # Precession: Quaternion rotating around base axis n by ω*dt
        q_precess = q_from_axis_angle(self.n, self.omega * dt)
        q_target = q_mul(q_precess, self.orientation)

        # Safe update via PSF-Zero
        metrics = self.head.step(q_target, dt=dt, guard_flags=guard_flags)

        return {
            "theta": float(self.theta),
            "omega": float(self.omega),
            "volume": self.volume,
            "delta_phi": float(metrics["delta_phi"]),
            "abstain": float(metrics["abstain"])
        }

    def tts_params(self) -> Dict[str, float]:
        """Map volume and ω to TTS parameters (pitch, rate, energy)."""
        v = self.volume
        w = np.clip(abs(self.omega) / self.p.omega_max, 0.0, 1.0)

        pitch = 1.0 + 0.25*(v - 0.5) + 0.15*(w - 0.5)
        rate  = 1.0 + 0.30*(w - 0.5) + 0.10*(v - 0.5)
        energy= 1.0 + 0.40*(v - 0.5) + 0.20*(w - 0.5)

        return {
            "pitch": float(np.clip(pitch, 0.6, 1.4)),
            "rate": float(np.clip(rate, 0.6, 1.4)),
            "energy": float(np.clip(energy, 0.6, 1.4))
        }

if __name__ == "__main__":
    cone = AffectiveCone()
    cone.set_target_from_intensity(0.8, base_axis=np.array([1., 0., 0.]))
    for _ in range(10):
        m = cone.step(dt=0.1)
    print("Cone metrics:", m, "\nTTS params:", cone.tts_params())
