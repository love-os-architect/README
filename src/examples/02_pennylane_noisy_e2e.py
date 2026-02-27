import pennylane as qml
import numpy as np
from psf_zero_pennylane import PSFHybridOptimizer

n_qubits = 2
dev = qml.device("default.qubit", wires=n_qubits)

@qml.qnode(dev)
def circuit(params):
    (angles_q0, angles_q1, taus) = params
    
    qml.RX(angles_q0[0], wires=0); qml.RY(angles_q0[1], wires=0); qml.RZ(angles_q0[2], wires=0)
    qml.RX(angles_q1[0], wires=1); qml.RY(angles_q1[1], wires=1); qml.RZ(angles_q1[2], wires=1)
    
    for k in range(len(taus)):
        qml.IsingZZ(taus[k], wires=[0,1])
        qml.RX(angles_q0[3+k], wires=0); qml.RY(angles_q0[3+k+1], wires=0); qml.RZ(angles_q0[3+k+2], wires=0)
        qml.RX(angles_q1[3+k], wires=1); qml.RY(angles_q1[3+k+1], wires=1); qml.RZ(angles_q1[3+k+2], wires=1)
        
    return qml.probs(wires=[0,1])

def loss_fn(params):
    # Proxy objective: Maximize return to |00> state
    return 1.0 - circuit(params)[0] 

rng = np.random.default_rng(42)
params = (rng.normal(scale=0.2, size=6), rng.normal(scale=0.2, size=6), rng.normal(scale=0.2, size=1))

print("Starting End-to-End Optimization with PSF-Zero (EIT + /0)...")
opt = PSFHybridOptimizer(stepsize=0.1, alpha_proj=1e-2, lam_phi=0.15, lam_amp=0.2)

for step in range(50):
    params = opt.step(loss_fn, params)
    if (step + 1) % 10 == 0:
        print(f"Step {step+1:02d} | Loss: {loss_fn(params):.6f}")

print("\nOptimization Complete. Phase Synchronized.")
