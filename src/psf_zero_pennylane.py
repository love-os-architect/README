from __future__ import annotations
import numpy as np
import pennylane as qml
from typing import Callable, Sequence

class PhaseAmpEITState:
    """ Applies Exponential Information Tracking (EIT) to gradient phase and amplitude. """
    def __init__(self, shape, lam_phi=0.15, lam_amp=0.2):
        self.lam_phi = lam_phi
        self.lam_amp = lam_amp
        self.z = np.zeros(shape, dtype=np.complex128) 
        self.r = np.zeros(shape, dtype=np.float64)    
        self.init = False

    def filter(self, g: np.ndarray) -> np.ndarray:
        phi = np.angle(g + 1e-12)
        z_t = np.exp(1j * phi)
        r_t = np.abs(g)

        if not self.init:
            self.z = z_t
            self.r = r_t
            self.init = True
        else:
            self.z = (1 - self.lam_phi) * self.z + self.lam_phi * z_t
            self.r = (1 - self.lam_amp) * self.r + self.lam_amp * r_t

        return self.r * np.cos(np.angle(self.z))

def projective_grad(vec: np.ndarray) -> np.ndarray:
    return 2.0 * vec / (1.0 + vec**2)**2

class PSFHybridOptimizer(qml.GradientDescentOptimizer):
    """ 
    PennyLane Optimizer integrating Love-OS principles:
    1) Phase-Amp EIT for noise synchronization.
    2) /0 Projective Regularization for dissipation control.
    """
    def __init__(self, stepsize: float = 0.1, alpha_proj: float = 1e-2, lam_phi: float = 0.15, lam_amp: float = 0.2):
        super().__init__(stepsize=stepsize)
        self.alpha_proj = alpha_proj
        self.lam_phi = lam_phi
        self.lam_amp = lam_amp
        self._eit_state = None

    def _ensure_state(self, x: Sequence[np.ndarray]):
        if self._eit_state is None:
            shapes = [np.shape(p) for p in x]
            self._eit_state = [PhaseAmpEITState(s, self.lam_phi, self.lam_amp) for s in shapes]

    def step(self, objective_fn: Callable, *args, **kwargs):
        grad_fn = qml.grad(objective_fn)
        g = grad_fn(*args, **kwargs)

        self._ensure_state(g if isinstance(g, (list, tuple)) else [g])
        
        # 1. Apply EIT Filter
        if isinstance(g, (list, tuple)):
            g_filtered = [st.filter(qml.numpy.asarray(gi)) for gi, st in zip(g, self._eit_state)]
        else:
            g_filtered = [self._eit_state[0].filter(qml.numpy.asarray(g))]

        # 2. Add /0 Projective Gradient
        proj_terms = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                proj_terms.append(qml.numpy.concatenate([qml.numpy.ravel(a) for a in arg]))
            else:
                proj_terms.append(qml.numpy.ravel(qml.numpy.asarray(arg)))

        if len(proj_terms) > 0:
            flat = qml.numpy.concatenate(proj_terms)
            pg = projective_grad(qml.numpy.asarray(flat))
            
            offset = 0; k = 0
            for arg in args:
                if isinstance(arg, (list, tuple)):
                    for a in arg:
                        n = a.size
                        g_filtered[k] = g_filtered[k] + self.alpha_proj * pg[offset:offset+n].reshape(a.shape)
                        offset += n; k += 1
                else:
                    n = arg.size
                    g_filtered[k] = g_filtered[k] + self.alpha_proj * pg[offset:offset+n].reshape(arg.shape)
                    offset += n; k += 1

        # 3. Apply Update
        new_args, _ = super().step_and_cost(lambda *a, **kw: objective_fn(*a, **kw), *args, **kwargs)
        
        stepsize = self.stepsize
        updated = []; k = 0
        for arg in new_args:
            if isinstance(arg, (list, tuple)):
                arr = [a - stepsize * g_filtered[k] for a in arg]; k += len(arg)
                updated.append(tuple(arr))
            else:
                updated.append(arg - stepsize * g_filtered[k]); k += 1

        return tuple(updated)
