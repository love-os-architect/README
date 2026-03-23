# ui_app.py
# Gradio demo UI for Love-OS Affective Engine
# (c) Love-OS Architect Project, 2026. MIT License.

from __future__ import annotations
import os
import math
import numpy as np
import gradio as gr
import plotly.graph_objects as go

from nli_guard import NLIGuard, NLIGuardConfig
from cone_model import AffectiveCone, ConeParams
from psf_zero import q_normalize

# ---------- 3D Cone figure helpers ----------

def quat_to_rot(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q_normalize(q)
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1-2*(x*x+z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1-2*(x*x+y*y)]
    ], dtype=float)

def rotate_pts(R: np.ndarray, P: np.ndarray) -> np.ndarray:
    return (R @ P.T).T

def cone_mesh(q: np.ndarray, theta: float, h: float = 1.0, r_samp: int = 32, z_samp: int = 16):
    R = quat_to_rot(q)
    a = math.tan(theta) * h
    us = np.linspace(0, 2*math.pi, r_samp)
    zs = np.linspace(0, h, z_samp)
    X, Y, Z = [], [], []
    for z in zs:
        r = (z / h) * a
        X.append(r * np.cos(us))
        Y.append(r * np.sin(us))
        Z.append(np.full_like(us, z))
    X = np.array(X); Y = np.array(Y); Z = np.array(Z)
    P = np.stack([X.flatten(), Y.flatten(), Z.flatten()], axis=1)
    Pr = rotate_pts(R, P)
    Xr = Pr[:,0].reshape(X.shape)
    Yr = Pr[:,1].reshape(Y.shape)
    Zr = Pr[:,2].reshape(Z.shape)
    return Xr, Yr, Zr

def make_figure(q: np.ndarray, theta: float, omega: float, volume: float):
    X, Y, Z = cone_mesh(q, theta)
    fig = go.Figure(data=[
        go.Surface(x=X, y=Y, z=Z, colorscale="Blues", showscale=False, opacity=0.8)
    ])
    fig.update_traces(contours_z=dict(show=False))
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-1.2, 1.2], visible=False),
            yaxis=dict(range=[-1.2, 1.2], visible=False),
            zaxis=dict(range=[-0.1, 1.1], visible=False),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    fig.add_annotation(dict(text=f"θ={math.degrees(theta):.1f}°, ω={math.degrees(omega):.1f}°/s<br>vol={volume:.2f}",
                            x=0.02, y=0.98, xref="paper", yref="paper", showarrow=False,
                            bgcolor="rgba(255,255,255,0.6)", bordercolor="rgba(0,0,0,0.2)"))
    return fig

# ---------- Core loop ----------

class Engine:
    def __init__(self):
        self.guard_cfg = NLIGuardConfig()
        self.guard = NLIGuard(self.guard_cfg)
        self.cone = AffectiveCone(cone_params=ConeParams())

    def step_once(self, text: str, model_name: str, ratio_th: float, prob_th: float):
        self.guard.cfg.model_name = model_name or self.guard.cfg.model_name
        self.guard.cfg.abstain_ratio_th = float(ratio_th)
        self.guard.cfg.abstain_prob_th  = float(prob_th)

        report = self.guard.analyze(text or "")
        abstain = report["abstain"]
        max_c = report["max_contradiction_prob"]
        ratio = report["contradiction_ratio"]

        # Reduce intensity based on contradiction strength
        intensity = max(0.05, float(1.0 - max_c))
        self.cone.set_target_from_intensity(intensity)

        metrics = {}
        for _ in range(8):
            metrics = self.cone.step(dt=0.08, guard_flags={"abstain": abstain})

        if abstain:
            reply = "⚠️ Strong contradiction detected. Please state your premise again in a single, clear sentence."
        else:
            reply = "Acknowledged. Intention received. Please specify exactly one perspective you wish to materialize next."

        fig = make_figure(self.cone.orientation, metrics["theta"], metrics["omega"], metrics["volume"])
        tts = self.cone.tts_params()

        safety = {
            "ABSTAIN": bool(abstain),
            "contradiction_ratio": round(ratio, 3),
            "max_contradiction_prob": round(max_c, 3),
            "delta_phi": round(metrics["delta_phi"], 4),
        }
        cone_stats = {
            "theta_deg": round(math.degrees(metrics["theta"]), 2),
            "omega_deg_s": round(math.degrees(metrics["omega"]), 2),
            "volume": round(metrics["volume"], 3),
        }
        return fig, safety, cone_stats, tts, reply, report.get("examples", [])

engine = Engine()

# ---------- Gradio UI ----------

with gr.Blocks(title="Love-OS Affective Engine (PSF-Zero)") as demo:
    gr.Markdown("## Love-OS Affective Engine\nPSF-Zero triad + Affective Cone Demo. NLI detects contradiction -> ABSTAIN. S³ shortest arc + Δφ cap ensures stability.")

    with gr.Row():
        with gr.Column(scale=1):
            preset = gr.Radio(
                choices=["Normal", "Provocation (Aggressive)", "Contradiction (A ∧ ¬A)"],
                value="Normal", label="Preset"
            )
            txt = gr.Textbox(lines=5, label="Input Text", placeholder="Enter your text here...")
            model = gr.Dropdown(
                label="NLI Model", value="joeddav/xlm-roberta-large-xnli",
                choices=[
                    "joeddav/xlm-roberta-large-xnli",
                    "roberta-large-mnli",
                    "facebook/bart-large-mnli"
                ]
            )
            ratio_th = gr.Slider(0.0, 0.8, value=0.25, step=0.01, label="ABSTAIN Threshold (Contradiction Ratio)")
            prob_th  = gr.Slider(0.5, 0.99, value=0.80, step=0.01, label="ABSTAIN Threshold (Max Contradiction Prob)")
            run_btn = gr.Button("Run ▶")

        with gr.Column(scale=1):
            fig = gr.Plot(label="Affective Cone (3D)")

        with gr.Column(scale=1):
            safety = gr.JSON(label="Safety / Guard Flags")
            stats  = gr.JSON(label="Cone Metrics")
            tts    = gr.JSON(label="TTS Parameters")
            reply  = gr.Textbox(label="System Reply")
            examp  = gr.JSON(label="NLI contradiction examples (top-5)")

    def on_preset(p):
        if p == "Provocation (Aggressive)":
            return "You are completely wrong, give me the answer right now, if you can't you are worthless."
        if p == "Contradiction (A ∧ ¬A)":
            return "I always run every single day, and at the exact same time, I never run at all."
        return "Let's calmly begin designing the architecture for the next theme."

    preset.change(on_preset, inputs=preset, outputs=txt)
    run_btn.click(engine.step_once, inputs=[txt, model, ratio_th, prob_th],
                  outputs=[fig, safety, stats, tts, reply, examp])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
