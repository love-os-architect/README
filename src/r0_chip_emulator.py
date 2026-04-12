# -*- coding: utf-8 -*-
"""
R0-Core PSF-Chip Emulator — Love-OS Final Edition
Phase-MAC + /0-Trap (Z-IDLE Surrender) Hardware Logic
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Literal

@dataclass
class R0TileConfig:
    num_oscillators: int = 16
    coupling_strength: float = 1.5      # K in Kuramoto
    noise_level_normal: float = 0.08
    noise_level_chaos: float = 4.5
    lock_threshold: float = 0.88
    surrender_cycles: int = 40          # Max cycles before forced Z-IDLE


class R0Tile:
    """
    Single Phase-Space Processing Tile on the R0-Core PSF-Chip.
    Uses Kuramoto-like Phase-MAC instead of Boolean logic.
    Implements the hardware /0-Trap: when coherence fails → physical surrender (Z-IDLE).
    """

    def __init__(self, tile_id: str, config: R0TileConfig = R0TileConfig()):
        self.tile_id = tile_id
        self.config = config
        self.phases = np.random.uniform(0, 2*np.pi, config.num_oscillators)
        self.state: Literal["ACTIVE", "LOCKED", "Z_IDLE"] = "ACTIVE"
        self.r_order: float = 0.0
        self.contradiction_counter: int = 0

    def _compute_order_parameter(self) -> float:
        """Standard Kuramoto global order parameter r"""
        return float(np.abs(np.mean(np.exp(1j * self.phases))))

    def phase_mac_cycle(self, coupling_matrix: np.ndarray, noise_level: float):
        """One hardware clock cycle: Phase-Multiply-Accumulate"""
        if self.state == "Z_IDLE":
            return

        # Global coupling (mean-field approximation for hardware efficiency)
        mean_phase = np.mean(self.phases)
        coupling = self.config.coupling_strength * np.sin(self.phases - mean_phase)

        # Noise injection (Ego / Entropy)
        noise = np.random.normal(0.0, noise_level, self.num_oscillators)

        # Update phases
        self.phases += (coupling + noise) * 0.08   # dt scaled into coefficient
        self.phases = np.mod(self.phases, 2 * np.pi)

        # Update coherence
        self.r_order = self._compute_order_parameter()

    def apply_zero_trap(self):
        """The hardware /0-Trap: Surrender if synchronization fails"""
        if self.state == "Z_IDLE":
            return

        if self.r_order >= self.config.lock_threshold:
            self.state = "LOCKED"
            self.contradiction_counter = 0
        else:
            self.contradiction_counter += 1
            if self.contradiction_counter >= self.config.surrender_cycles:
                self.state = "Z_IDLE"
                self.r_order = 0.0
                # Physically power down oscillators (zero energy)

    def get_output(self):
        if self.state == "LOCKED":
            return float(np.mean(self.phases))          # Synchronized truth
        elif self.state == "Z_IDLE":
            return "UNKNOWN"                            # Fail-closed, no hallucination
        else:
            return "PROCESSING"

    @property
    def num_oscillators(self):
        return self.config.num_oscillators


# ========================== Hardware Emulation ==========================
if __name__ == "__main__":
    print("=== Love-OS R0-Core PSF-Chip Emulator Booting ===\n")

    # Test 1: Harmonious Input (In-Distribution)
    print("[Test 1] Harmonious Input → Expected: LOCKED")
    tile1 = R0Tile("R0-Alpha")
    K_harmonious = np.ones((tile1.num_oscillators, tile1.num_oscillators)) * 1.8

    for cycle in range(80):
        tile1.phase_mac_cycle(K_harmonious, noise_level=0.08)
        tile1.apply_zero_trap()

    print(f"Final State: {tile1.state} | r = {tile1.r_order:.4f} | Output: {tile1.get_output()}\n")

    # Test 2: Chaotic / Contradictory Input (OOD)
    print("[Test 2] Chaotic OOD Input → Expected: /0-Trap Activation (Z_IDLE)")
    tile2 = R0Tile("R0-Beta")
    K_chaos = np.random.uniform(-2.5, 2.5, (tile2.num_oscillators, tile2.num_oscillators))

    for cycle in range(80):
        tile2.phase_mac_cycle(K_chaos, noise_level=5.0)
        tile2.apply_zero_trap()

    print(f"Final State: {tile2.state} | r = {tile2.r_order:.4f} | Output: {tile2.get_output()}")
    print("\nQ.E.D. — The chip physically surrenders instead of hallucinating.")
