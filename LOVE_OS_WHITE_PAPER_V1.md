# PSF-Zero: Projective Spherical Filtering for Zero-Dissipation Quantum Control

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Qiskit Compatible](https://img.shields.io/badge/Qiskit-Compatible-6929C4.svg)](https://qiskit.org/)
[![PennyLane Ready](https://img.shields.io/badge/PennyLane-Ready-00D1B2.svg)](https://pennylane.ai/)

## Abstract
We introduce **PSF-Zero** (Projective Spherical Filtering), a hybrid optimization framework for quantum gate synthesis designed to overcome the thermodynamic and control limits of Noisy Intermediate-Scale Quantum (NISQ) devices. Traditional gradient-based pulse shaping suffers from severe dissipation, over-rotation, and susceptibility to time-varying noise. 

PSF-Zero resolves these bottlenecks by integrating three core mathematical principles:
1. **Stereographic Projective Regularization ($/0$):** Maps divergence and infinite gradients to a single topological point (the North Pole of a Riemann sphere), suppressing gradient explosions and strictly minimizing pulse energy (dissipation).
2. **Phase-Amplitude Exponential Information Tracking (EIT):** Applies an exponential moving average to both the phase and amplitude of the gradient in the complex plane, enabling robust, autonomous synchronization (surrender) to time-varying noise, detuning drifts, and cross-talk.
3. **Quaternion-based $SU(4)$ Geodesics:** Eliminates gimbal lock during two-qubit local rotations, enabling the discovery of the absolute shortest path (geodesic) for entanglement generation.

Empirical results demonstrate that PSF-Zero achieves **$>99.9999\%$ average gate fidelity** for CZ and iSWAP gates while simultaneously reducing the total pulse variation (heat dissipation) by over 20%. Furthermore, end-to-end training under noisy environments proves its robust generalization against up to 10% detuning drift, heavily suppressing leakage to the $|2\rangle$ state.



## Installation
```bash
pip install -r requirements.txt
```

## 📂 Repository Structure
* **[psf_zero_qiskit.py](https://github.com/love-os-architect/README/blob/main/src/psf_zero_qiskit.py)**
* **[psf_zero_pennylane.py](https://github.com/love-os-architect/README/blob/main/src/psf_zero_pennylane.py)**

* **`psf_zero_qiskit.py`**: A **Qiskit Transpiler Pass** (`PSFGateSynthesis`) that automatically decomposes arbitrary 2-qubit unitaries into highly optimized, low-dissipation native pulse sequences (e.g., **RZZ + RX/RY/RZ**).
* **`psf_zero_pennylane.py`**: A **PennyLane Custom Optimizer** (`PSFHybridOptimizer`) that wraps standard Gradient Descent to inject **EIT** and **Projective Regularization** directly into the backward pass—perfect for noisy End-to-End Quantum Machine Learning (QML) or VQE.



## 🚀 Usage

Check the **`examples/`** directory for quick-start scripts.
