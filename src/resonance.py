# src/resonance.py
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Profile:
    name: str
    f_vec: List[float]  # Feature vector (Values/Vibe)
    d: float            # Damping factor (Trust/Resistance)
    E: float = 1.0      # Energy (Signal Strength)

class AttractionEngine:
    """
    Computes physical resonance (attraction) between entities.
    Based on Driven Damped Harmonic Oscillator model.
    """
    
    def __init__(self, my_profile: Profile, weights: Optional[List[float]] = None):
        self.me = my_profile
        self.weights = np.array(weights) if weights else np.ones(len(my_profile.f_vec))

    def compute_score(self, target: Profile) -> float:
        """
        Calculates Resonance Score A (Attraction).
        A = E / sqrt( (f0^2 - f^2)^2 + (d * f)^2 )
        Extended to vector space.
        """
        f0 = np.array(self.me.f_vec)
        f  = np.array(target.f_vec)
        
        # Weighted difference (Frequency Mismatch)
        # Delta ~ (f0^2 - f^2) in scalar analog
        diff = self.weights * (f - f0)
        mismatch_energy = np.sum(diff**2) # Squared Euclidean distance acts like frequency gap
        
        # Effective Damping
        # Damping acts on the target's frequency magnitude
        # Term: (d * f)^2
        f_mag = np.linalg.norm(self.weights * f)
        damping_term = (target.d * f_mag)**2
        
        # Resonance Formula
        # We use a modified form for vector stability:
        # A = E / sqrt( (Mismatch)^2 + Damping )
        denom = np.sqrt(mismatch_energy**2 + damping_term)
        
        return float(target.E / max(denom, 1e-9))

# Usage Example
if __name__ == "__main__":
    me = Profile("Me", [1.0, 1.0, 1.0], d=0.1)
    
    candidates = [
        Profile("Twin Flame", [1.0, 1.0, 1.0], d=0.05, E=1.2), # Perfect match, low friction
        Profile("Karmic",     [1.0, 1.0, 1.0], d=0.8,  E=2.0), # Match, but high friction
        Profile("Stranger",   [0.2, 0.5, 0.1], d=0.1,  E=1.0), # Low friction, no match
    ]
    
    engine = AttractionEngine(me)
    
    for c in candidates:
        print(f"{c.name}: {engine.compute_score(c):.4f}")
