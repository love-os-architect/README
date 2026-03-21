#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Love-OS Aerospace Core: S3 Geodesic Control & Convex Thruster Allocation
-------------------------------------------------------------------------
This module unifies the inner-loop PSF-Zero geometric attitude controller 
(Lyapunov-stable, unwinding-free) with the outer-loop convex QP thruster 
allocator (Fuel-minimizing, Soft-MIB compliant).
"""

import numpy as np
import scipy.sparse as sp
import cvxpy as cp

# =====================================================================
# 1. INNER LOOP: PSF-Zero S3 Geometric PD Controller
# =====================================================================
class PSFZeroAttitudeController:
    def __init__(self, delta_hysteresis: float = 0.05):
        self.sigma = 1.0  # State variable for hemispheric hysteresis (prevents unwinding)
        self.delta = delta_hysteresis

    def compute_torque(self, q_c: np.ndarray, q_d: np.ndarray, 
                       omega_c: np.ndarray, K_q: float, K_w: float) -> np.ndarray:
        """
        Computes the ideal frictionless torque along the S3 minimal arc.
        q_c, q_d: Quaternions [w, x, y, z]
        """
        # 1. Error Quaternion: q_e = q_d^{-1} ⊗ q_c
        q_d_inv = np.array([q_d[0], -q_d[1], -q_d[2], -q_d[3]])
        # Quaternion multiplication (Hamilton convention)
        w1, x1, y1, z1 = q_d_inv
        w2, x2, y2, z2 = q_c
        q_e = np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
        q_e = q_e / np.linalg.norm(q_e)

        # 2. Hemispheric Hysteresis (Surrender to the shortest path)
        if q_e[0] < -self.delta:
            self.sigma = -1.0
        elif q_e[0] > self.delta:
            self.sigma = 1.0

        # 3. Geometric Gradient on S3
        e_q = 2.0 * self.sigma * q_e[1:4]

        # 4. PSF-Zero Control Law (Lyapunov V_dot <= 0 guaranteed)
        tau_ideal = -K_q * e_q - K_w * omega_c
        return tau_ideal

# =====================================================================
# 2. OUTER LOOP: OSQP Thruster Allocation with Soft-MIB Refitting
# =====================================================================
def soft_mib_refit_safe(
    dt_initial: np.ndarray, tau_ref: np.ndarray, B: np.ndarray, A: np.ndarray, 
    tmax: np.ndarray, mib: np.ndarray, W_tau: np.ndarray, 
    lam_refit: float = 1e-5, W_force: float = 1e3
) -> np.ndarray:
    """
    Safely reallocates thrust if initial commands fall below the Minimum Impulse Bit (MIB).
    Converts the strict Zero-Translation equality into a Soft Penalty to guarantee 
    solver feasibility (preventing OSQP stall).
    """
    m = B.shape[1]
    
    # 1. Clip sub-MIB thrusters to strict zero
    active = dt_initial >= mib
    dt_clipped = dt_initial.copy()
    dt_clipped[~active] = 0.0

    if not np.any(active):
        return dt_clipped

    # 2. Extract Active Set (J)
    J = np.where(active)[0]
    B_J = B[:, J]
    A_J = A[:, J] if A is not None else None
    dt_J = dt_clipped[J]
    tmax_J = tmax[J]
    mib_J = mib[J]

    # 3. Build Feasible Refit QP
    x = cp.Variable(len(J), nonneg=True)
    cons = [x <= tmax_J, x >= mib_J]  # Strict MIB enforcement

    # 4. Objective: Track Torque + Stay close to original + SOFT Zero-Translation Penalty
    obj = 0.5 * cp.sum_squares(W_tau @ (B_J @ x - tau_ref)) \
          + 0.5 * lam_refit * cp.sum_squares(x - dt_J)

    if A_J is not None:
        # Crucial: Soft penalty prevents 'infeasible' crashes when A_J x = 0 is impossible
        obj += 0.5 * W_force * cp.sum_squares(A_J @ x)

    prob = cp.Problem(cp.Minimize(obj), cons)
    
    try:
        prob.solve(solver=cp.OSQP, verbose=False)
        if prob.status in ["optimal", "optimal_inaccurate"]:
            dt_refit = dt_clipped.copy()
            dt_refit[J] = x.value
            return dt_refit
    except Exception:
        pass
    
    # Fallback to pure clipped if solver fails
    return dt_clipped
