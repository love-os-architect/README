# -*- coding: utf-8 -*-
"""
psd_to_rms_phase.py
Love-OS Optical Phase Noise Analyzer — PSF-Zero Edition

Extracts RMS phase noise (σ_φ) from physical optical telemetry while applying
/0 projective regularization to suppress outlier spikes and divergent noise.
"""

import numpy as np
import pandas as pd
from scipy import signal
from dataclasses import dataclass
from typing import Tuple, Optional, Dict

@dataclass
class PhaseNoiseConfig:
    fmin: float = 1.0          # [Hz] Lower integration limit
    fmax: float = 50e3         # [Hz] Upper integration limit
    tau: float = 1.0           # /0 projection strength (smaller = stronger clamping)
    detrend: bool = True
    window: str = 'hann'
    nperseg: Optional[int] = None


def zero_clamp(x: np.ndarray, tau: float = 1.0) -> np.ndarray:
    """ /0 Projective Clamp: safely bounds large values (prevents divergence) """
    x = np.asarray(x, dtype=float)
    return x / np.sqrt(1.0 + (x / tau)**2)


def rms_phase_from_timeseries(csv_path: str, 
                              config: PhaseNoiseConfig = PhaseNoiseConfig()) -> Dict:
    """
    Compute RMS phase noise from raw time-series phase data (t, phi).
    Applies /0 clamping to suppress outlier spikes before PSD integration.
    """
    df = pd.read_csv(csv_path)
    t = df.iloc[:, 0].values
    phi = df.iloc[:, 1].values

    # Estimate sampling frequency
    dt = np.median(np.diff(t))
    fs = 1.0 / dt if dt > 0 else 1e6

    # Detrend
    phi_d = signal.detrend(phi, type='linear') if config.detrend else phi

    # /0 Projective Clamping on raw phase deviations (prevents spike dominance)
    phi_clamped = zero_clamp(phi_d, tau=config.tau)

    # Welch PSD
    nperseg = config.nperseg or min(len(phi_clamped), 2**14)
    f, Pxx = signal.welch(phi_clamped, fs=fs, window=config.window,
                          nperseg=nperseg, noverlap=nperseg//2, scaling='density')

    # Band-limited RMS integration
    band = (f >= config.fmin) & (f <= config.fmax)
    if not np.any(band):
        raise ValueError("No frequency content in the specified band.")

    sigma_rad = np.sqrt(np.trapz(Pxx[band], f[band]))
    sigma_deg = np.degrees(sigma_rad)

    return {
        "rms_rad": float(sigma_rad),
        "rms_deg": float(sigma_deg),
        "fs": float(fs),
        "fmin": config.fmin,
        "fmax": config.fmax,
        "tau": config.tau,
        "n_samples": len(phi),
        "status": "OK"
    }


def rms_phase_from_psd(csv_path: str, 
                       config: PhaseNoiseConfig = PhaseNoiseConfig()) -> Dict:
    """
    Compute RMS phase noise directly from pre-calculated PSD (f, S_phi).
    """
    df = pd.read_csv(csv_path)
    f = df.iloc[:, 0].values
    Sphi = df.iloc[:, 1].values

    band = (f >= config.fmin) & (f <= config.fmax)
    if not np.any(band):
        raise ValueError("No frequency content in the specified band.")

    sigma_rad = np.sqrt(np.trapz(Sphi[band], f[band]))
    sigma_deg = np.degrees(sigma_rad)

    return {
        "rms_rad": float(sigma_rad),
        "rms_deg": float(sigma_deg),
        "fmin": config.fmin,
        "fmax": config.fmax,
        "status": "OK"
    }


if __name__ == "__main__":
    print("Love-OS Optical Phase Noise Analyzer (PSF-Zero Edition)")
    print("=" * 65)

    # Example usage (uncomment and set your file)
    # result = rms_phase_from_timeseries(
    #     "optical_telemetry_phase.csv",
    #     config=PhaseNoiseConfig(fmin=1.0, fmax=100e3, tau=0.8)
    # )

    # print(f"RMS Phase Noise : {result['rms_deg']:.4f} deg  ({result['rms_rad']:.2e} rad)")
    # print(f"Integration band: {result['fmin']:.1f} – {result['fmax']/1e3:.1f} kHz")
    # print(f"/0 Clamp strength (tau): {result['tau']}")

    print("Module loaded successfully. Ready for Genesis Axis extraction.")
