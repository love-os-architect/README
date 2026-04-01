# -*- coding: utf-8 -*-
from __future__ import annotations
import time, math
import numpy as np
from dataclasses import dataclass

def _now_ms():
    return time.time() * 1000.0

@dataclass
class PSFConfig:
    lam: float = 0.10
    sigma: float = 1.0
    max_phase_jump: float = math.radians(45)
    max_latency_ms: float = 5000.0
    use_cayley: bool = True

class MetricsCollector:
    def __init__(self): self.reset()
    def reset(self):
        self.time_ms = 0.0
        self.renorm_calls = 0
        self.quatmul_calls = 0
        self.steps = 0
    def add_time(self, dt): self.time_ms += dt
    def inc_renorm(self): self.renorm_calls += 1
    def inc_quatmul(self, n=1): self.quatmul_calls += n
    def inc_step(self): self.steps += 1

def clamp(delta, sigma):
    return delta / math.sqrt(sigma*sigma + delta*delta)

def eit(zbar, phi, lam):
    return (1-lam)*zbar + lam*complex(math.cos(phi), math.sin(phi))

def quat_from_axis_angle(axis, angle):
    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    if n == 0.0:
        return np.array([1., 0., 0., 0.])
    axis /= n
    h = 0.5 * angle
    return np.array([math.cos(h), *(math.sin(h)*axis)])

def quat_mul(q1, q2):
    w1,x1,y1,z1 = q1
    w2,x2,y2,z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quat_normalize(q):
    n = np.linalg.norm(q)
    return q if n == 0 else q/n

def su2_update(q, axis, dtheta, cfg, mc):
    dq = quat_from_axis_angle(axis, dtheta)
    mc.inc_quatmul(1)
    q1 = quat_mul(dq, q)
    q1 = quat_normalize(q1)
    mc.inc_renorm()
    return q1

def psfzero_step(q, grad_axis, grad_angle, zbar, phi, cfg, mc=None):
    mc = mc or MetricsCollector()
    t0 = _now_ms()

    dtheta = clamp(grad_angle, cfg.sigma)
    zbar_new = eit(zbar, phi, cfg.lam)
    q_new = su2_update(q, grad_axis, dtheta, cfg, mc)

    dt = _now_ms() - t0
    mc.add_time(dt)
    mc.inc_step()

    info = {
        "latency_ms": dt,
        "applied_angle": dtheta,
        "max_phase_jump": abs(dtheta),
    }
    return q_new, zbar_new, info
