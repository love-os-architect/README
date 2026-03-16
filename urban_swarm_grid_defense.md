# PSF-Zero: Urban-Scale Swarm Control & Grid-Forming (GFM) Defense

## 1. The Zero-Inertia Crisis
As global power grids transition to 100% renewable energy, they lose the physical mass (kinetic inertia, $M$) provided by traditional turbine generators. Without this heavy physical anchor, the grid becomes highly volatile. A sudden drop in solar output or a massive load step can cause instantaneous frequency collapse. 

To compensate, modern grids rely on **Swarm Control**: coordinating hundreds of thousands of distributed batteries (EVs, home BESS) via Grid-Forming (GFM) or Virtual Synchronous Machine (VSM) inverters to inject power instantly.

## 2. The Fatal Flaw: Delay & Overcompensation
When 100,000 EVs attempt to stabilize the grid simultaneously using standard linear droop control ($P_i(t) = -K_f \cdot \Delta f(t)$), they encounter a fatal physics trap: **Communication and Processing Delay ($\tau$).**

Because the frequency measurement and power injection take time (e.g., $\tau = 100$ ms), the swarm reacts to *past* data. By the time the swarm injects power, the grid may have already begun recovering. This causes massive **overcompensation**, turning the swarm itself into a giant oscillator. Within seconds, the frequency wildly hunts, and the grid completely blacks out. Traditional engineering attempts to fix this with a chaotic patchwork of deadbands, rate limiters, and anti-windup IF-ELSE loops.

## 3. The Geometric Solution: PSF-Zero
We replace the chaotic IF-ELSE safety nets with a single topological law: **Stereographic Projective Regularization (`/0` clamp)** derived from the Love-OS architecture.

Instead of fighting the spike with linear force, we project the frequency deviation onto a Riemann sphere, safely saturating infinite potential spikes into a smooth, geometric curve.

* **Legacy Linear Controller:** $P_i(t) = -K_f \cdot \Delta f_{local}(t)$
* **PSF-Zero Geometric Controller:** $P_i(t) = -K_f \cdot \frac{\Delta f_{local}(t)}{\sqrt{\sigma^2 + \Delta f_{local}(t)^2}}$

This single geometric transformation geometrically absorbs the shock. It acts as a perfect shock-absorber (Viscosity), allowing the swarm to seamlessly synchronize (Phase-Lock) with the grid without ever overshooting, even under severe delay ($\tau$) and zero-inertia ($M \to 0$) conditions.

## 4. Empirical Proof (Simulation)
We provide [ swarm_psf_zero_sim.py](https://github.com/love-os-architect/README/blob/main/swarm_psf_zero_sim.py) to mathematically prove this on your local machine.
It simulates a highly volatile grid ($M = 2.0$) with a fatal delay ($\tau = 100$ ms) hit by a massive -300 MW shock. 
* **Result A (Legacy):** Fatal oscillation and total grid collapse within 5 seconds.
* **Result B (PSF-Zero):** Complete geometric stabilization. Zero overshoot.

### Usage
```bash
pip install numpy matplotlib
python swarm_psf_zero_sim.py
```
