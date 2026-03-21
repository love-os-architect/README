# geoclam_adam.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Iterable, Optional, Tuple
import math
import torch
from torch.optim.optimizer import Optimizer

# =====================================================================
# Lie Algebra & Manifold Utilities
# =====================================================================

def _hat_so3(v: torch.Tensor) -> torch.Tensor:
    """vee^-1 : Maps R^3 -> 3x3 skew-symmetric matrices (Lie algebra)."""
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    O = torch.zeros_like(x)
    return torch.stack([
        torch.stack([ O, -z,  y], dim=-1),
        torch.stack([ z,  O, -x], dim=-1),
        torch.stack([-y,  x,  O], dim=-1)
    ], dim=-2)

def _exp_so3(phi: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Rodrigues' formula for exact Exponential Map: R^3 -> SO(3)."""
    theta = torch.linalg.norm(phi, dim=-1, keepdim=True).clamp_min(eps)
    A = torch.sin(theta) / theta
    B = (1.0 - torch.cos(theta)) / (theta * theta)
    K = _hat_so3(phi)
    I = torch.eye(3, device=phi.device, dtype=phi.dtype).expand(K.shape)
    return I + A[..., None] * K + B[..., None] * (K @ K)

def _project_so3_tangent(R: torch.Tensor, G: torch.Tensor) -> torch.Tensor:
    """Projects Euclidean gradient onto the SO(3) tangent space (Lie algebra)."""
    RtG = R.transpose(-1, -2) @ G
    Sk = 0.5 * (RtG - RtG.transpose(-1, -2))
    return torch.stack([Sk[..., 2, 1], Sk[..., 0, 2], Sk[..., 1, 0]], dim=-1)

def _normalize_quat(q: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """Normalizes quaternions and enforces the short hemisphere (q0 >= 0) to avoid unwinding."""
    q = q / (torch.linalg.norm(q, dim=-1, keepdim=True).clamp_min(eps))
    sign = torch.where(q[..., :1] >= 0, torch.ones_like(q[..., :1]), -torch.ones_like(q[..., :1]))
    return q * sign

def _project_s3_tangent(q: torch.Tensor, g: torch.Tensor) -> torch.Tensor:
    """Projects Euclidean gradient onto the S3 tangent space."""
    inner = (q * g).sum(dim=-1, keepdim=True)
    return g - inner * q

def _smooth_clamp_radius(r_raw: torch.Tensor, r_trust: torch.Tensor, mode: str = "hard") -> torch.Tensor:
    """/0 Geometric Clamp: Saturates the update radius based on the curvature trust limit."""
    if mode == "soft":
        alpha = 6.0
        s = torch.sigmoid(alpha * (r_raw - r_trust))
        return r_raw * (1.0 - s) + (r_trust - 1e-9) * s
    return torch.minimum(r_raw, r_trust)

# =====================================================================
# GeoClampAdam Optimizer
# =====================================================================

class GeoClampAdam(Optimizer):
    r"""
    Geometric Adam optimizer on Lie groups with PSF-Zero (/0 clamp).
    Surrenders to the manifold's curvature by dynamically capping the geodesic step radius.

    Supported Manifolds:
      - 'SO3': Rotations (..., 3, 3) updated via exact Exponential Map.
      - 'S3' : Unit Quaternions (..., 4) updated via Orthogonal Retraction.
    """

    def __init__(
        self,
        params: Iterable[torch.nn.Parameter],
        lr: float = 1e-2,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        manifold: str = "SO3",
        max_step: Optional[float] = None,
        base_trust: Optional[float] = None,
        kappa: float = 0.0,
        clamp_mode: str = "hard",
    ):
        if manifold not in ("SO3", "S3"):
            raise ValueError("manifold must be 'SO3' or 'S3'.")

        # Topologically safe bounds to absolutely prevent unwinding (> pi)
        if max_step is None:
            max_step = math.pi - 1e-3 if manifold == "SO3" else (math.pi / 2.0 - 1e-3)
        if base_trust is None:
            base_trust = 0.25 * max_step

        defaults = dict(
            lr=lr, betas=betas, eps=eps, manifold=manifold, 
            max_step=max_step, base_trust=base_trust, 
            kappa=kappa, clamp_mode=clamp_mode
        )
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                if group["manifold"] == "SO3":
                    self._step_so3(p, group)
                elif group["manifold"] == "S3":
                    self._step_s3(p, group)

        return loss

    def _get_state_buffers(self, p: torch.nn.Parameter, shape_m: torch.Size):
        state = self.state[p]
        if len(state) == 0:
            state["step"] = 0
            state["m"] = torch.zeros(shape_m, device=p.device, dtype=p.dtype)
            state["v"] = torch.zeros_like(state["m"])
            state["vnorm"] = torch.tensor(0.0, device=p.device, dtype=p.dtype)
        return state["m"], state["v"], state["vnorm"]

    @torch.no_grad()
    def _step_so3(self, p, group):
        g_alg = _project_so3_tangent(p, p.grad)
        m, v, vnorm = self._get_state_buffers(p, g_alg.shape)

        # Adam Moments in Tangent Space
        m.mul_(group["betas"][0]).add_(g_alg, alpha=(1.0 - group["betas"][0]))
        v.mul_(group["betas"][1]).addcmul_(g_alg, g_alg, value=(1.0 - group["betas"][1]))

        precond = 1.0 / (torch.sqrt(v) + group["eps"])
        xi_raw = -group["lr"] * (m * precond)

        # Dynamic Curvature Trust Radius (/0 Clamp)
        cur_norm = torch.linalg.norm(g_alg, dim=-1).mean()
        vnorm.mul_(group["betas"][1]).add_(cur_norm.detach() * (1.0 - group["betas"][1]))
        r_trust = min(group["max_step"], float(group["base_trust"] / (1.0 + float(group["kappa"]) * float(vnorm))))

        # Saturated Geodesic Step
        r_raw = torch.linalg.norm(xi_raw, dim=-1, keepdim=True)
        r_sat = _smooth_clamp_radius(r_raw, torch.full_like(r_raw, r_trust), mode=group["clamp_mode"])
        xi = xi_raw * (r_sat / torch.clamp(r_raw, min=1e-12))

        # Frictionless Geodesic Update on SO(3)
        dR = _exp_so3(xi)
        p.copy_(dR @ p)
        self.state[p]["step"] += 1

    @torch.no_grad()
    def _step_s3(self, p, group):
        p.copy_(_normalize_quat(p))
        g_tan = _project_s3_tangent(p, p.grad)
        m, v, vnorm = self._get_state_buffers(p, g_tan.shape)

        m.mul_(group["betas"][0]).add_(g_tan, alpha=(1.0 - group["betas"][0]))
        v.mul_(group["betas"][1]).addcmul_(g_tan, g_tan, value=(1.0 - group["betas"][1]))

        precond = 1.0 / (torch.sqrt(v) + group["eps"])
        xi_raw = -group["lr"] * (m * precond)

        cur_norm = torch.linalg.norm(g_tan, dim=-1).mean()
        vnorm.mul_(group["betas"][1]).add_(cur_norm.detach() * (1.0 - group["betas"][1]))
        r_trust = min(group["max_step"], float(group["base_trust"] / (1.0 + float(group["kappa"]) * float(vnorm))))

        r_raw = torch.linalg.norm(xi_raw, dim=-1, keepdim=True)
        r_sat = _smooth_clamp_radius(r_raw, torch.full_like(r_raw, r_trust), mode=group["clamp_mode"])
        xi = xi_raw * (r_sat / torch.clamp(r_raw, min=1e-12))

        # Retraction Update ensuring Short Hemisphere (No Unwinding)
        q_new = _normalize_quat(p + xi)
        p.copy_(q_new)
        self.state[p]["step"] += 1
