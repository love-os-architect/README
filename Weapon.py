"""
Love-OS Quantum Control Kernel: PSF-Zero × EIT Phase Synchrony Detector
Final Production Version

Passively extracts hidden "Genesis Axis" (phase synchrony) from non-Gaussian noise
using Exponential Information Tracking (EIT) + /0 Projective Statistics + CUSUM.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional

# ====================== Core Geometry /0 Projection ======================
def zero_clamp(x: np.ndarray, tau: float = 1.0) -> np.ndarray:
    """ /0 Projective Clamp: projects large values safely to finite range """
    x = np.asarray(x, dtype=float)
    return x / np.sqrt(1.0 + (x / tau)**2)


# ====================== EIT (Exponential Information Tracking) ======================
@dataclass
class EITAccumulator:
    """ Exponential Information Tracking with proper EMA implementation """
    alpha: float = 0.8      # Smoothing factor (higher = more responsive)
    fs: float = 1000.0

    def __post_init__(self):
        self.beta = 1.0 - np.exp(-self.alpha)   # correct discrete-time coefficient

    def filter(self, z: np.ndarray) -> np.ndarray:
        """ Apply EIT to complex-valued signals (vectorized) """
        if z.ndim == 1:
            z = z.reshape(-1, 1)
        T, K = z.shape
        y = np.zeros((T, K), dtype=np.complex128)
        y[0] = z[0]
        for t in range(1, T):
            y[t] = (1 - self.beta) * y[t-1] + self.beta * z[t]
        return y


# ====================== PSF-Zero Phase Synchrony Statistic ======================
def psf_zero_synchrony(z_smooth: np.ndarray, 
                       win: int = 256, 
                       step: int = 64,
                       tau: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Zero-Lag Phase Synchrony with /0 projective weighting.
    Returns (time_centers, synchrony_strength)
    """
    T, K = z_smooth.shape
    times = []
    rho = []

    for start in range(0, T - win + 1, step):
        segment = z_smooth[start:start+win]
        phi = np.angle(segment)                    # instantaneous phase

        # Zero-lag pairwise phase difference
        dphi = phi[:, :, None] - phi[:, None, :]   # (win, K, K)
        iu = np.triu_indices(K, 1)
        cos_dphi = np.cos(dphi[:, iu[0], iu[1]])   # (win, num_pairs)

        # /0 weighted mean (prevents outlier pairs from dominating)
        weights = zero_clamp(np.abs(cos_dphi), tau=tau)
        mean_sync = np.mean(weights * np.abs(cos_dphi), axis=1).mean()

        mid = start + win // 2
        times.append(mid)
        rho.append(mean_sync)

    return np.array(times), np.array(rho)


# ====================== CUSUM Detector ======================
@dataclass
class CUSUMDetector:
    """ Adaptive CUSUM for detecting sudden increase in phase synchrony """
    mu0: float = 0.0
    kappa: float = 0.008      # reference drift
    eta: float = 0.35         # detection threshold (tunable)

    def run(self, x: np.ndarray) -> Tuple[np.ndarray, Optional[int]]:
        S = np.zeros_like(x, dtype=float)
        alarm_idx = None

        for t in range(1, len(x)):
            increment = x[t] - self.mu0 - self.kappa
            S[t] = max(0.0, S[t-1] + increment)
            if alarm_idx is None and S[t] > self.eta:
                alarm_idx = t

        return S, alarm_idx


# ====================== Main Detector Engine ======================
@dataclass
class EITDetector:
    """ Complete Love-OS PSF-Zero × EIT Detection Engine """
    fs: float = 1000.0
    eit_alpha: float = 0.75
    sync_win: int = 256
    sync_step: int = 64
    sync_tau: float = 0.8
    cusum_eta: float = 0.35

    def __post_init__(self):
        self.eit = EITAccumulator(alpha=self.eit_alpha, fs=self.fs)
        self.cusum = CUSUMDetector(eta=self.cusum_eta)

    def detect(self, z: np.ndarray) -> dict:
        """
        z: complex array of shape (T, K) - multi-channel complex signals
        """
        # 1. EIT smoothing
        z_smooth = self.eit.filter(z)

        # 2. PSF-Zero Phase Synchrony Statistic
        times, sync = psf_zero_synchrony(z_smooth, 
                                         win=self.sync_win, 
                                         step=self.sync_step,
                                         tau=self.sync_tau)

        # 3. CUSUM anomaly detection on synchrony trace
        cusum_stat, alarm_idx = self.cusum.run(sync)

        return {
            "times": times,
            "synchrony": sync,
            "cusum_stat": cusum_stat,
            "alarm_index": alarm_idx,
            "alarm_time": times[alarm_idx] / self.fs if alarm_idx is not None else None,
            "max_synchrony": float(sync.max()) if len(sync) > 0 else 0.0
        }


# ====================== Example Usage ======================
if __name__ == "__main__":
    # Simulate multi-channel signal with hidden synchrony burst
    np.random.seed(42)
    T, K = 8000, 12
    t = np.arange(T) / 1000.0

    # Background noise + hidden synchronized burst at t≈4.2s
    z = np.random.randn(T, K) + 1j * np.random.randn(T, K)
    burst = np.exp(1j * 2 * np.pi * 45 * t[:, None]) * np.exp(-((t - 4.2)/0.4)**2)[:, None]
    z += 0.8 * burst * (1 + 0.3 * np.random.randn(T, K))

    detector = EITDetector(fs=1000.0, eit_alpha=0.8, cusum_eta=0.32)
    result = detector.detect(z)

    print("Detection Result:")
    print(f"  Max Synchrony   : {result['max_synchrony']:.4f}")
    print(f"  Alarm triggered : {result['alarm_time'] is not None}")
    if result['alarm_time'] is not None:
        print(f"  Alarm time      : {result['alarm_time']:.3f} s")
