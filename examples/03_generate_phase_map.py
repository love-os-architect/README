# -*- coding: utf-8 -*-
# Love-OS: Quantum Kuramoto Phase Map Generator (Multi-Axis Sweep)
import numpy as np
import itertools as it
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import DensityMatrix, partial_trace
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, thermal_relaxation_error, phase_damping_error, depolarizing_error, ReadoutError

def ring_xy_trotter(n, depth, alpha):
    """nqubits ring; depth m; each step applies RXX & RYY with angle alpha on nearest neighbors."""
    qr = QuantumRegister(n, 'q')
    qc = QuantumCircuit(qr)
    pairs = [(i, (i+1)%n) for i in range(n)]
    for _ in range(depth):
        for i,j in pairs:
            qc.rxx(alpha, i, j)
        for i,j in pairs:
            qc.ryy(alpha, i, j)
    return qc

def build_noise(T1, T2, Tphi=None, gate_time=50e-9, p_depol=0.0):
    """Compose NoiseModel: thermal relaxation (+phase damping optional) + depolarizing."""
    nm = NoiseModel()
    th1q = thermal_relaxation_error(T1, T2, gate_time)
    th2q = thermal_relaxation_error(T1, T2, 2*gate_time).tensor(thermal_relaxation_error(T1, T2, 2*gate_time))
    
    if Tphi is not None:
        pd1q = phase_damping_error(gamma=1.0 - np.exp(-gate_time/Tphi))
        pd2q = phase_damping_error(gamma=1.0 - np.exp(-2*gate_time/Tphi)).tensor(
               phase_damping_error(gamma=1.0 - np.exp(-2*gate_time/Tphi)))
        th1q = th1q.compose(pd1q)
        th2q = th2q.compose(pd2q)
        
    if p_depol > 0:
        dep1 = depolarizing_error(p_depol, 1)
        dep2 = depolarizing_error(p_depol, 2)
        th1q = th1q.compose(dep1)
        th2q = th2q.compose(dep2)
        
    for g in ['rx','ry','rz','id','x','y','z','sx']:
        nm.add_all_qubit_quantum_error(th1q, g)
    for g in ['rxx','ryy','cx']:
        nm.add_all_qubit_quantum_error(th2q, g)
    return nm

def qubit_phase_from_dm(dm, i):
    """1量子 reduced density -> <X>,<Y> -> theta"""
    red = partial_trace(dm, [q for q in range(dm.num_qubits) if q!=i]).data
    X = np.array([[0,1],[1,0]], dtype=complex)
    Y = np.array([[0,-1j],[1j,0]], dtype=complex)
    mx = np.trace(red @ X).real
    my = np.trace(red @ Y).real
    return np.arctan2(my, mx)

def order_parameter_r(dm):
    N = dm.num_qubits
    thetas = [qubit_phase_from_dm(dm, i) for i in range(N)]
    return float(np.abs(np.mean(np.exp(1j*np.array(thetas)))))

def run_phase_map(n=4, depth=5):
    """Run simulations across different noise channels to generate the Phase Map."""
    print(f"Starting Love-OS Quantum Kuramoto Simulation (n={n} qubits)...")
    
    # Sweep Parameters
    K_list = np.linspace(0.1, 1.0, 15)
    T_list = np.linspace(10e-6, 150e-6, 15) # 10us to 150us noise times
    tg = 40e-9
    
    results = []
    
    # 1. Sweep T_phi (Phase Damping)
    print("Simulating T_phi decoherence...")
    for Tphi in T_list:
        noise = build_noise(T1=100e-6, T2=100e-6, Tphi=Tphi, gate_time=tg)
        sim = AerSimulator(method="density_matrix", noise_model=noise)
        for K in K_list:
            qc = ring_xy_trotter(n=n, depth=depth, alpha=K * (tg / 40e-9))
            qc.save_density_matrix()
            dm = DensityMatrix(sim.run(qc, shots=1).result().data(0)['density_matrix'])
            results.append({"Noise_Type": "Tphi", "K": K, "T_us": Tphi*1e6, "r": order_parameter_r(dm)})

    # 2. Sweep T_1 (Amplitude Damping)
    print("Simulating T_1 decoherence...")
    for T1 in T_list:
        noise = build_noise(T1=T1, T2=T1, Tphi=None, gate_time=tg)
        sim = AerSimulator(method="density_matrix", noise_model=noise)
        for K in K_list:
            qc = ring_xy_trotter(n=n, depth=depth, alpha=K * (tg / 40e-9))
            qc.save_density_matrix()
            dm = DensityMatrix(sim.run(qc, shots=1).result().data(0)['density_matrix'])
            results.append({"Noise_Type": "T1", "K": K, "T_us": T1*1e6, "r": order_parameter_r(dm)})

    return pd.DataFrame(results)

def plot_phase_maps(df):
    """Generate the 3-axis heatmap with r=0.5 survival boundaries."""
    print("Generating Phase Map Visualizations...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    cmap = "magma"

    for ax, noise_type, title in zip(axes, ["Tphi", "T1"], ["Phase Damping ($T_\\phi$)", "Amplitude Damping ($T_1$)"]):
        df_sub = df[df["Noise_Type"] == noise_type]
        pivot = df_sub.pivot(index="T_us", columns="K", values="r").sort_index(ascending=False)
        
        sns.heatmap(pivot, cmap=cmap, ax=ax, cbar_kws={'label': 'Order Parameter $r$'}, vmin=0, vmax=1)
        
        # Draw r=0.5 Survival Boundary
        X, Y = np.meshgrid(np.arange(pivot.shape[1]), np.arange(pivot.shape[0]))
        ax.contour(X, Y, pivot.values, levels=[0.5], colors='white', linestyles='dashed', linewidths=2)
        
        ax.set_title(title, fontsize=14, pad=10)
        ax.set_xlabel("Coupling Strength $K$ (Love)", fontsize=12)
        ax.set_ylabel("Noise Time [$\\mu$s] (Friction - Lower is worse)", fontsize=12)
        
        # Clean up ticks
        ax.set_xticks(np.linspace(0, len(pivot.columns)-1, 5))
        ax.set_xticklabels([f"{k:.2f}" for k in np.linspace(pivot.columns.min(), pivot.columns.max(), 5)])
        ax.set_yticks(np.linspace(0, len(pivot.index)-1, 5))
        ax.set_yticklabels([f"{t:.0f}" for t in np.linspace(pivot.index.max(), pivot.index.min(), 5)])

    plt.tight_layout()
    plt.savefig("quantum_kuramoto_multi_axis.png", dpi=200, bbox_inches="tight")
    print("✅ Success! Saved plot as 'quantum_kuramoto_multi_axis.png'")

if __name__ == "__main__":
    df_results = run_phase_map(n=4, depth=5) # 4量子ビット・深さ5（ノートPCでも数分で終わる現実的な設定）
    plot_phase_maps(df_results)
