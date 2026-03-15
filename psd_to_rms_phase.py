```python
# -*- coding: utf-8 -*-
"""
psd_to_rms_phase.py
Extracts RMS phase noise (\sigma_\phi) from physical optical network telemetry.
"""
import numpy as np
import pandas as pd
from scipy import signal

def rms_from_timeseries(csv_path, fmin=1.0, fmax=50e3, fs=None):
    """
    Reads time-series phase data and calculates RMS phase noise via Welch's PSD.
    Expected CSV format: t[s], phi[rad]
    """
    df = pd.read_csv(csv_path)
    t = df.iloc[:, 0].values
    phi = df.iloc[:, 1].values
    
    if fs is None:
        dt = np.median(np.diff(t))
        fs = 1.0 / dt

    # Detrend & Windowed PSD (Welch)
    phi_d = signal.detrend(phi, type='linear')
    nperseg = min(len(phi_d), 2**14)
    f, Pxx = signal.welch(phi_d, fs=fs, window='hann', nperseg=nperseg, noverlap=nperseg//2)

    # Band Integration (Default: 1Hz to 50kHz)
    band = (f >= fmin) & (f <= fmax)
    sigma = np.sqrt(np.trapz(Pxx[band], f[band]))

    return sigma, (f, Pxx)

def rms_from_psd(csv_path, fmin=1.0, fmax=50e3):
    """
    Reads pre-calculated PSD data and calculates RMS phase noise.
    Expected CSV format: f[Hz], S_phi[rad^2/Hz]
    """
    df = pd.read_csv(csv_path)
    f = df.iloc[:, 0].values
    Sphi = df.iloc[:, 1].values
    
    band = (f >= fmin) & (f <= fmax)
    sigma = np.sqrt(np.trapz(Sphi[band], f[band]))
    return sigma

if __name__ == "__main__":
    # Example Usage (Uncomment and replace with actual data files)
    print("Love-OS: Optical PSD to RMS Phase Converter initialized.")
    # sigma_ts, _ = rms_from_timeseries("telemetry_phase.csv", fmin=1.0, fmax=50e3)
    # print(f"Measured RMS Phase (1-50kHz): {np.degrees(sigma_ts):.2f} deg ({sigma_ts:.4e} rad)")
