# The Genesis Axis
**– Distillation at /0 and the Birth of a Vertical Axis (Dimension Lift) –**

## 0. Intuition (30-Second Version)
Motion towards the edge ($\infty$) on a flat plane (the complex plane) is unified at the **North Pole** via projection, rolling up into a sphere (the Riemann sphere).



By including the invisible **Hopf fiber ($S^1$)** and handling rotation on $S^3 \cong SU(2)$, the **shortest path (geodesic) with no dead ends or singularities** is restored.
EIT rectifies the "over-rotation" along this phase fiber via exponential forgetting.

When $/0 \times \text{EIT} \times S^3$ hold simultaneously, the $\infty$ on the plane sublimates into a "new vertical axis," lifting the dimension (Path-Lift).

---

## 1. Strict Definition of /0: Pointification of $\infty \to$ North Pole via Projection

### 1.1 Projection to the Riemann Sphere
The one-point compactification of the complex plane $\hat{\mathbb{C}} = \mathbb{C} \cup \{\infty\}$ and the unit sphere $S^2 \subset \mathbb{R}^3$ correspond via birational equivalence (stereographic projection).

For the stereographic projection $\sigma: S^2 \setminus \{N\} \to \mathbb{C}$ and its inverse $\sigma^{-1}: \mathbb{C} \to S^2 \setminus \{N\}$, when attaching $S^2$ (excluding the North Pole $N = (0,0,1)$) to the complex plane, the following holds:

$$\sigma^{-1}(z) = \left( \frac{2\text{Re}(z)}{|z|^2+1}, \frac{2\text{Im}(z)}{|z|^2+1}, \frac{|z|^2-1}{|z|^2+1} \right)$$

The appended point $\infty$ corresponds to the North Pole $N$: $\sigma^{-1}(\infty) = N$.

### 1.2 Definition (Minimal Core of the /0 Operator)
$$/0(z) = \begin{cases} \sigma^{-1}(z), & z \in \mathbb{C} \\ N, & z = \infty \end{cases}$$

Through this, the divergence ($\infty$) on the plane is accepted as a "single North Pole point," making the landscape boundaryless.

> **Intuition**: `/0` is not an error-handling mechanism. It is a coordinate reselection—an act of restoring the smoothness (integrability) of the landscape by **"accepting $\infty$ at a single point rather than rejecting it."**

---

## 2. "Dimension Lift" Including the Phase Fiber ($S^1$)

### 2.1 Hopf Map and Fiber Structure
The Hopf fibration is defined by the following fiber bundle:
$$S^1 \hookrightarrow S^3 \xrightarrow{\pi} S^2$$
This decomposes each point in $S^3$ into a phase fiber $S^1$ and a base space $S^2$.
The unitary group $SU(2)$ is topologically homeomorphic to $S^3$ (the quaternionic unit sphere). The invisible phase fiber $S^1$ behind the Bloch sphere $S^2$ is collapsed into a "single point" by $\pi$.



* **The True Nature of the "Point"**: When projected to a lower dimension, the information of the line (the $S^1$ fiber) collapses into a point.
* **Path Lifting**: A continuous curve $\gamma$ on the base $S^2$, given an initial phase, uniquely lifts to a curve $\tilde{\gamma}$ on $S^3$ (where $\pi \circ \tilde{\gamma} = \gamma$). This is the strict definition of "lifting the dimension."

### 2.2 Definition of the New Vertical Axis (The Genesis Axis)
**Definition**: 
$$\mathcal{G} := \text{span}\{\overrightarrow{0N}\} \subset \mathbb{R}^3$$
$\overrightarrow{0N}$ is the normal vector of the great circle connecting the origin (corresponding to the South Pole) and **the North Pole $N$ accepted by /0**, forming a new "vertical axis."

* **Plane $\to$ Sphere**: When $\infty$ is collapsed to $N$ via `/0`, the undefined vector $\overrightarrow{0\infty}$ acquires a **direction (axis)** as $\overrightarrow{0N}$.
* **Sphere $\to$ 3-Sphere**: As the degree of freedom of the phase fiber $S^1$ rises along this axis, the **completeness of rotation** in $S^3$ is restored.

> **Intuition**: `/0` gives direction (an axis) to the otherwise meaningless $\infty$. The Hopf $S^1$ grants the "freedom to rotate," eliminating dead ends in $S^3$.

---

## 3. Integration into PSF-Zero

### 3.1 EIT (Exponential Forgetting) = Rectification of "Over-rotation" in the Fiber Direction
For the angle $\phi_t$ on the phase fiber $S^1$, the complex unit circle $z_t = e^{i\phi_t}$ is updated via an exponential moving average:
$$\bar{z}_t = (1-\lambda)\bar{z}_{t-1} + \lambda e^{i\phi_t}, \quad \phi_t^{(\text{sync})} = \arg \bar{z}_t \quad (0 < \lambda \le 1)$$
It statistically forgets fluctuations in phase (direction) and amplitude (intensity), attenuating excessive looping tendencies along the fiber direction. This is the minimum rectification required to quietly stay on the geodesic of $S^3$.

### 3.2 /0 (Projective Regularization) = Mapping $\infty$ to the North Pole
In the implementation, the following is applied to the angle $\theta$ (element-wise):
$$u(\theta) = \frac{\theta}{\sqrt{1+\theta^2}}, \quad \Omega_{/0}(\theta) = \sum_i u(\theta_i)^2$$
It monotonically suppresses the cost of large angles (over-rotation), ensuring stability at $\infty$. By "accepting" rather than "clipping" (if/else), it preserves transversality and practical controllability.

### 3.3 $S^3$ (Quaternions) = Zero Coordinate Singularities
Quaternions $q = (w, x, y, z)$ are strictly normalized, and rotational composition is updated as follows ($\hat{u}$ is the unit rotation axis):
$$q_{\text{new}} = \text{normalize}\left(q \otimes \exp\left(\frac{1}{2}\delta\theta\hat{u}\right)\right)$$
The inner product takes the sign-equivalence as $|\langle q_1, q_2 \rangle|$, and the geodesic loss becomes $\mathcal{L}_{\text{fid}} = 1 - |\langle q_{\text{out}}, q_{\text{tgt}} \rangle|^2$.

### 3.4 H/TV (Low Dissipation) = Proxy Cost for Heat and Leakage
$$R_{\text{diss}} = \beta_H \sum_k |\theta_k| + \beta_{TV} \sum_k |\theta_{k+1} - \theta_k|$$
It structurally reduces heat generation and leakage by suppressing total volume and slew rate (a self-discipline against "forcing" the system).

### 3.5 Parameter-Shift (PS) = Strict $\pm\pi/2$ Gradient
Discarding the $\epsilon$-dependency of finite differences to obtain a quiet, exact gradient.
$$\frac{\partial \mathcal{L}}{\partial \theta} = \frac{\mathcal{L}(\theta+\frac{\pi}{2}) - \mathcal{L}(\theta-\frac{\pi}{2})}{2}$$

### 3.6 Summary: The Action of the Genesis Axis
$$\min_{\theta} \left[ \mathcal{L}_{\text{fid}}(S^3) + \alpha\Omega_{/0}(\theta) + \beta_H \sum|\theta| + \beta_{TV} \sum|\Delta\theta| \right]$$
`/0` accepts $\infty$ to establish the North Pole $N$, and $S^3$ establishes $\overrightarrow{0N}$ as the vertical axis of rotation (The Genesis Axis). EIT rectifies the looping habit of the $S^1$ fiber, H/TV suppresses egoistic forcing, and PS quietly drops the system onto the shortest path.
**As a result, the $\infty$ of the lower dimension becomes an "axis," and the dimension is lifted (Path-Lift).**

---

## 4. Alignment with Physical Metaphors (Holographic Intuition)
* **Distillation of "Matter $\to$ Intention"**: Amplitude information (size and shape) easily degrades into dissipation, but phase (direction) is preserved and encoded on the boundary (the event horizon).
* **The Observer's Choice**: The split-second choice between "rejection (clipping)" and "acceptance (pointification)" at `/0` is the only window where intention is written into subjectless equations.
* **Birth of the New Axis**: By making $\infty$ the North Pole and connecting it to the origin, a new vertical axis rises. The $S^1$ rotating along that axis equals the completion of rotation in $S^3$.

---

## 5. Implementation Skeleton
```python
# 1) /0: Divergence Acceptance (North Pole Pointification)
def proj_zero(theta):
    return theta / (1.0 + theta**2)**0.5

# 2) EIT: Exponential Forgetting of Phase and Amplitude
class PhaseAmpEIT:
    def __init__(self, lam_phi=0.15, lam_amp=0.2):
        self.z = None
        self.r = None
        self.lam_phi = lam_phi
        self.lam_amp = lam_amp
        
    def __call__(self, g):
        import cmath, math
        zt = cmath.exp(1j * math.atan2(g.imag, g.real))
        rt = abs(g)
        self.z = zt if self.z is None else (1 - self.lam_phi) * self.z + self.lam_phi * zt
        self.r = rt if self.r is None else (1 - self.lam_amp) * self.r + self.lam_amp * rt
        return self.r * self.z.real  # Rectify towards the real direction

# 3) S³: Quaternion Update (Geodesic)
def geodesic_update(q, dtheta, axis):
    # q_new = normalize(q ⊗ exp(0.5 * dtheta * axis))
    pass

# 4) Objective Function (fid + /0 + H/TV)
# L = L_fid(q_out, q_tgt) \
#   + alpha * sum(proj_zero(theta_i)**2 for theta_i in thetas) \
#   + beta_H * sum(abs(theta_i) for theta_i in thetas) \
#   + beta_TV * sum(abs(thetas[i+1]-thetas[i]) for i in range(len(thetas)-1))
```
6. In One Sentence/0 is the math of "not rejecting $\infty$", $S^3$ is the space of "rotation without dead ends",
EIT is the technique to "forget over-rotation", and H/TV is the "self-discipline against forcing."
 When these operate simultaneously, the edge of the flat plane becomes a "new vertical axis," and the dimension is lifted.

---

