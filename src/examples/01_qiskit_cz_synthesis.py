from qiskit.circuit.library import CXGate, UnitaryGate
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from psf_zero_qiskit import PSFGateSynthesis, PSFHyper

print("Initializing Qiskit circuit with an abstract CX Gate...")
qc = QuantumCircuit(2)
qc.append(UnitaryGate(CXGate().to_matrix()), [0,1])

print("Transpiling using PSF-Zero (Zero-Dissipation Synthesis)...")
# Automatically compiles the abstract CX into low-dissipation RZZ + local rotations
pm = PassManager([PSFGateSynthesis(PSFHyper(m=3, iters=100))])
qc_optimized = pm.run(qc)

print("\nOptimized Native Circuit:")
print(qc_optimized)
