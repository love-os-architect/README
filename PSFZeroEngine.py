import numpy as np
from scipy.signal import hilbert

class PSFZeroEngine:
    """
    The heart of the Y-Axis Revolution.
    Integrates Phase-Space Filtering (PSF-Zero) with Exponential Integration (EIT).
    """
    def __init__(self, fs, alpha_inv=0.3):
        self.fs = fs
        self.alpha = 1.0 / max(alpha_inv, 1e-6)
        self.state = None

    def eit_step(self, z):
        """Exponentially Weighted Integration (EIT)"""
        if self.state is None:
            self.state = z
        else:
            dt = 1.0 / self.fs
            self.state = self.state + (z - self.state) * (1 - np.exp(-self.alpha * dt))
        return self.state

    def compute_rho_zero(self, signals):
        """
        Calculates the Zero-Lag Phase Synchrony (PSF-Zero).
        'signals' should be a multi-channel array (Samples x Channels).
        """
        # 1. Convert to Complex Analytic Signal (Hilbert Transform)
        z = hilbert(signals, axis=0)
        
        # 2. Apply EIT to smooth the essence
        z_smooth = np.array([self.eit_step(row) for row in z])
        
        # 3. Extract Phase and Compute Global Synchrony (rho-hat)
        phases = np.angle(z_smooth)
        k = phases.shape[1]
        
        # Calculate pair-wise phase consistency
        rho_sum = 0
        count = 0
        for i in range(k):
            for j in range(i + 1, k):
                # The core logic: how much do their phases 'align' despite the noise?
                rho_sum += np.cos(phases[:, i] - phases[:, j])
                count += 1
        
        rho_hat = rho_sum / count
        return rho_hat

# Example Usage:
# fs = 4000 (4kHz)
# signals = (10000 samples, 8 channels of NV-Center data)
# engine = PSFZeroEngine(fs)
# result = engine.compute_rho_zero(signals)
