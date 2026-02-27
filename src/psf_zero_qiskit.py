from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, RXGate, RYGate, RZGate, UnitaryGate
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import TransformationPass
from qiskit.converters import circuit_to_dag

# ------------------------------------------------------------
# === Core Math: /0 Projective Regularization, H/TV, PS Grad ===
# ------------------------------------------------------------

def projective_reg(vec: np.ndarray) -> float:
    """ Projective Regularization: Maps infinite divergence to a point. """
    u = vec / np.sqrt(1.0 + vec**2)
    return float(np.sum(u**2))

def projective_grad(vec: np.ndarray) -> np.ndarray:
    """ Analytic gradient of the projective regularizer. """
    return 2.0 * vec / (1.0 + vec**2)**2

def L1_total(params_angles: np.ndarray, taus: np.ndarray) -> float:
    """ Total pulse energy (Dissipation H). """
    return float(np.sum(np.abs(params_angles)) + np.sum(np.abs(taus)))

def TV_total(params_angles: np.ndarray, taus: np.ndarray) -> float:
    """ Total Variation (TV) to penalize abrupt pulse changes (reduces leakage). """
    tv = 0.0
    for q in range(2):
        for c in range(3):
            tv += np.sum(np.abs(np.diff(params_angles[:, q, c])))
    tv += np.sum(np.abs(np.diff(taus)))
    return float(tv)

def Rz(theta): return np.array([[np.exp(-1j*theta/2), 0], [0, np.exp(1j*theta/2)]], dtype=complex)
def Rx(theta): 
    c, s = np.cos(theta/2), -1j*np.sin(theta/2)
    return np.array([[c, s], [s, c]], dtype=complex)
def Ry(theta): 
    c, s = np.cos(theta/2), np.sin(theta/2)
    return np.array([[c, -s], [s, c]], dtype=complex)

def kron(*ops):
    M = np.array([[1]], dtype=complex)
    for op in ops: M = np.kron(M, op)
    return M

def Uzz(tau):
    """ Entangler: exp(-i tau/2 Z⊗Z) """
    ph = np.exp(-1j * 0.5 * tau)
    phc = np.conj(ph)
    return np.diag([ph, phc, phc, ph])

def local_block(block_params):
    (ax0, ay0, az0) = block_params[0]
    (ax1, ay1, az1) = block_params[1]
    U0 = Rz(az0) @ Ry(ay0) @ Rx(ax0)
    U1 = Rz(az1) @ Ry(ay1) @ Rx(ax1)
    return kron(U0, U1)

def compose_circuit_unitary(params_angles, taus):
    U = local_block(params_angles[0])
    for k in range(len(taus)):
        U = Uzz(taus[k]) @ U
        U = local_block(params_angles[k+1]) @ U
    return U

def F_avg(U, V):
    """ Average gate fidelity between two unitaries in SU(4). """
    d = U.shape[0]
    return float((np.abs(np.trace(U.conj().T @ V))**2 + d) / (d*(d+1)))

PS = np.pi/2 # Parameter-Shift constant

@dataclass
class PSFHyper:
    m: int = 3                  # number of entanglers
    iters: int = 150
    lr: float = 0.2
    alpha_proj: float = 1e-2    # /0 regularization strength
    beta_H: float = 5e-3        # L1 dissipation penalty
    beta_TV: float = 5e-3       # Smoothness penalty
    seed: int = 42

class PSFHybridSynthesizer:
    """ Synthesizes a 2-qubit unitary into a low-dissipation native circuit. """
    def __init__(self, hyper: PSFHyper):
        self.h = hyper
        rng = np.random.default_rng(hyper.seed)
        self.params_angles = rng.normal(scale=0.2, size=(hyper.m+1, 2, 3))
        self.taus = rng.normal(scale=0.2, size=hyper.m)

    def _flat(self) -> np.ndarray:
        return np.concatenate([self.params_angles.flatten(), self.taus.flatten()])

    def _set_flat(self, vec: np.ndarray):
        nb = (self.h.m+1)*2*3
        self.params_angles = vec[:nb].reshape(self.h.m+1, 2, 3)
        self.taus = vec[nb:]

    def _ps_grad(self, U_target) -> np.ndarray:
        base = self._flat().copy()
        nb_angles = (self.h.m+1)*2*3
        grad = np.zeros_like(base)

        # Parameter-Shift for fidelity (Analytic gradient)
        for b in range(self.h.m+1):
            for q in range(2):
                for c in range(3):
                    idx = b*2*3 + q*3 + c
                    v = base.copy(); v[idx] += PS; self._set_flat(v)
                    Lp = 1.0 - F_avg(compose_circuit_unitary(self.params_angles, self.taus), U_target)
                    v = base.copy(); v[idx] -= PS; self._set_flat(v)
                    Lm = 1.0 - F_avg(compose_circuit_unitary(self.params_angles, self.taus), U_target)
                    grad[idx] = 0.5*(Lp - Lm)

        for k in range(self.h.m):
            idx = nb_angles + k
            v = base.copy(); v[idx] += PS; self._set_flat(v)
            Lp = 1.0 - F_avg(compose_circuit_unitary(self.params_angles, self.taus), U_target)
            v = base.copy(); v[idx] -= PS; self._set_flat(v)
            Lm = 1.0 - F_avg(compose_circuit_unitary(self.params_angles, self.taus), U_target)
            grad[idx] = 0.5*(Lp - Lm)

        # Add Analytic /0 Projective Gradient
        grad += self.h.alpha_proj * projective_grad(base)

        # Add H/TV Gradient (Light FD)
        eps = 1e-4
        for i in range(base.size):
            v = base.copy(); self._set_flat(v)
            r0 = self.h.beta_H * L1_total(self.params_angles, self.taus) + self.h.beta_TV * TV_total(self.params_angles, self.taus)
            v = base.copy(); v[i] += eps; self._set_flat(v)
            r1 = self.h.beta_H * L1_total(self.params_angles, self.taus) + self.h.beta_TV * TV_total(self.params_angles, self.taus)
            grad[i] += (r1 - r0) / eps

        self._set_flat(base)
        return grad

    def run(self, U_target: np.ndarray):
        lr0 = self.h.lr
        for t in range(self.h.iters):
            # Cosine Annealing Learning Rate
            lr = max(1e-4, lr0 * (0.5*(1 + np.cos(np.pi*t/self.h.iters))))
            grad = self._ps_grad(U_target)
            vec = self._flat()
            vec -= lr * grad
            self._set_flat(vec)

    def as_qiskit(self) -> QuantumCircuit:
        qc = QuantumCircuit(2)
        a0 = self.params_angles[0]
        for q in range(2):
            qc.append(RXGate(a0[q][0]), [q])
            qc.append(RYGate(a0[q][1]), [q])
            qc.append(RZGate(a0[q][2]), [q])
            
        for k in range(self.h.m):
            qc.append(RZZGate(self.taus[k]), [0, 1])
            a = self.params_angles[k+1]
            for q in range(2):
                qc.append(RXGate(a[q][0]), [q])
                qc.append(RYGate(a[q][1]), [q])
                qc.append(RZGate(a[q][2]), [q])
        return qc

class PSFGateSynthesis(TransformationPass):
    """ Qiskit Transpiler Pass: Replaces 2Q Unitaries with PSF-optimized native circuits. """
    def __init__(self, hyper: Optional[PSFHyper] = None):
        super().__init__()
        self.hyper = hyper or PSFHyper()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        new_dag = dag.copy()
        for node in list(new_dag.op_nodes()):
            if isinstance(node.op, UnitaryGate) and node.op.num_qubits == 2:
                U_target = np.asarray(node.op.to_matrix(), dtype=complex)
                synth = PSFHybridSynthesizer(self.hyper)
                synth.run(U_target)
                new_dag.substitute_node_with_dag(node, circuit_to_dag(synth.as_qiskit()), wires=node.qargs)
        return new_dag
