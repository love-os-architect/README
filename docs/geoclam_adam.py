# -*- coding: utf-8 -*-
"""
GeoClampAdam — Love-OS Geometric Optimizer with PSF-Zero /0 Projection
Optimized for Lie groups SO(3) and S³ (Quaternions).
"""

from __future__ import annotations
import math
from typing import Iterable, Tuple, Optional
import torch
from torch.optim.optimizer import Optimizer

# ========================== Lie Algebra & Retraction ==========================
def _hat_so3(v: torch.Tensor) -> torch.Tensor:
    """ R^3 → so(3) skew-symmetric matrix """
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    O = torch.zeros_like(x)
    return torch.stack([
        torch.stack([O, -z,  y], dim=-1),
        torch.stack([z,  O, -x], dim=-1),
        torch.stack([-y,  x,  O], dim=-1)
    ], dim=-2)

def _exp_so3(phi: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """ Rodrigues' formula: so(3) → SO(3) """
    theta = torch.linalg.norm(phi, dim=-1, keepdim=True).clamp_min(eps)
    A = torch.sin(theta) / theta
    B = (1.0 - torch.cos(theta)) / (theta * theta)
    K = _hat_so3(phi)
    I = torch.eye(3, device=phi.device, dtype=phi.dtype).expand(K.shape)
    return I + A[..., None] * K + B[..., None] * (K @ K)

def _project_so3_tangent(R: torch.Tensor, G: torch.Tensor) -> torch.Tensor:
    """ Project Euclidean gradient onto so(3) tangent space """
    RtG = R.transpose(-1, -2) @ G
    skew = 0.5 * (RtG - RtG.transpose(-1, -2))
    return torch.stack([skew[..., 2, 1], skew[..., 0, 2], skew[..., 1, 0]], dim=-1)

def _normalize_quat(q: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """ Normalize quaternion + enforce short hemisphere (q0 ≥ 0) """
    q = q / torch.linalg.norm(q, dim=-1, keepdim=True).clamp_min(eps)
    sign = torch.where(q[..., 0:1] >= 0, 1.0, -1.0)
    return q * sign

def _project_s3_tangent(q: torch.Tensor, g: torch.Tensor) -> torch.Tensor:
    """ Project onto T_q S³ """
    inner = (q * g).sum(dim=-1, keepdim=True)
    return g - inner * q

def _clamp_radius(r_raw: torch.Tensor, r_trust: torch.Tensor, mode: str = "hard") -> torch.Tensor:
    """ /0 Geometric Step Clamp """
    if mode == "soft":
        alpha = 8.0
        s = torch.sigmoid(alpha * (r_raw - r_trust))
        return r_raw * (1.0 - s) + r_trust * s
    return torch.minimum(r_raw, r_trust)


# ========================== GeoClampAdam ==========================
class GeoClampAdam(Optimizer):
    """
    Geometric Adam on Lie groups with PSF-Zero /0 projection.
    Dynamically clamps geodesic step size according to local curvature.
    """

    def __init__(
        self,
        params: Iterable[torch.nn.Parameter],
        lr: float = 1e-2,
        betas: Tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        manifold: str = "SO3",           # "SO3" or "S3"
        max_step: Optional[float] = None,
        base_trust: Optional[float] = None,
        kappa: float = 0.05,             # curvature sensitivity
        clamp_mode: str = "hard",        # "hard" or "soft"
    ):
        if manifold not in ("SO3", "S3"):
            raise ValueError("manifold must be 'SO3' or 'S3'")

        # Safe topological bounds
        if max_step is None:
            max_step = math.pi - 1e-3 if manifold == "SO3" else (math.pi / 2 - 1e-3)
        if base_trust is None:
            base_trust = 0.28 * max_step

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
                else:
                    self._step_s3(p, group)

        return loss

    def _get_state(self, p: torch.nn.Parameter, shape: torch.Size):
        state = self.state[p]
        if len(state) == 0:
            state["step"] = 0
            state["m"] = torch.zeros(shape, device=p.device, dtype=p.dtype)
            state["v"] = torch.zeros_like(state["m"])
            state["vnorm"] = torch.zeros(1, device=p.device, dtype=p.dtype)
        return state

    def _step_so3(self, p: torch.nn.Parameter, group: dict):
        g_tan = _project_so3_tangent(p, p.grad)
        state = self._get_state(p, g_tan.shape)

        m = state["m"]
        v = state["v"]
        vnorm = state["vnorm"]

        # Adam in tangent space
        m.mul_(group["betas"][0]).add_(g_tan, alpha=1 - group["betas"][0])
        v.mul_(group["betas"][1]).addcmul_(g_tan, g_tan, value=1 - group["betas"][1])

        precond = 1.0 / (torch.sqrt(v) + group["eps"])
        xi_raw = -group["lr"] * m * precond

        # Dynamic trust radius using /0 curvature awareness
        cur_norm = torch.linalg.norm(g_tan, dim=-1).mean()
        vnorm.mul_(group["betas"][1]).add_(cur_norm.detach() * (1 - group["betas"][1]))
        r_trust = min(group["max_step"], group["base_trust"] / (1.0 + group["kappa"] * float(vnorm)))

        r_raw = torch.linalg.norm(xi_raw, dim=-1, keepdim=True)
        r_sat = _clamp_radius(r_raw, torch.full_like(r_raw, r_trust), mode=group["clamp_mode"])
        xi = xi_raw * (r_sat / torch.clamp(r_raw, min=1e-12))

        # Geodesic update (Right-invariant)
        dR = _exp_so3(xi)
        p.copy_(p @ dR)

    def _step_s3(self, p: torch.nn.Parameter, group: dict):
        p.copy_(_normalize_quat(p))
        g_tan = _project_s3_tangent(p, p.grad)
        state = self._get_state(p, g_tan.shape)

        m = state["m"]
        v = state["v"]
        vnorm = state["vnorm"]

        m.mul_(group["betas"][0]).add_(g_tan, alpha=1 - group["betas"][0])
        v.mul_(group["betas"][1]).addcmul_(g_tan, g_tan, value=1 - group["betas"][1])

        precond = 1.0 / (torch.sqrt(v) + group["eps"])
        xi_raw = -group["lr"] * m * precond

        cur_norm = torch.linalg.norm(g_tan, dim=-1).mean()
        vnorm.mul_(group["betas"][1]).add_(cur_norm.detach() * (1 - group["betas"][1]))
        r_trust = min(group["max_step"], group["base_trust"] / (1.0 + group["kappa"] * float(vnorm)))

        r_raw = torch.linalg.norm(xi_raw, dim=-1, keepdim=True)
        r_sat = _clamp_radius(r_raw, torch.full_like(r_raw, r_trust), mode=group["clamp_mode"])
        xi = xi_raw * (r_sat / torch.clamp(r_raw, min=1e-12))

        # Retraction + short hemisphere enforcement
        q_new = _normalize_quat(p + xi)
        p.copy_(q_new)
