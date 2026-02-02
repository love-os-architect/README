import numpy as np
import matplotlib.pyplot as plt

class LoveOSUnified:
    """
    Love-OS Unified Theory Simulator
    Integrates: Electric, Thermal, Fluid, Sync, Info
    """
    def __init__(self, N=20, dt=0.01):
        self.N = N
        self.dt = dt
        self.time = 0.0
        
        # --- 1. State Variables (The "X") ---
        self.I = np.zeros(N)       # Impulse (Ideal)
        self.A = np.zeros(N)       # Action (Reality)
        self.theta = np.random.uniform(0, 2*np.pi, N) # Phase
        self.omega = np.random.normal(0, 1.0, N)      # Intrinsic Freq
        self.u = np.zeros((N, 2))  # Fluid Flow (2D Vector for simplicity)
        self.F = np.zeros(N)       # Free Energy (Prediction Error)
        
        # --- 2. Parameters (The "Environment") ---
        self.R_i = np.ones(N) * 2.0   # Internal Resistance (Ego)
        self.R_ij = np.ones((N,N)) * 1.0 # Social Resistance
        self.K_ij = np.ones((N,N)) * 2.0 # Sync Coupling
        self.beta = 0.1  # Thermal Sensitivity
        self.nu = 0.1    # Fluid Viscosity
        
        # Awakened Node Setting (Node 0)
        self.is_awakened = False

    def activate_awakening(self):
        """Set Node 0 to Awakened State (R=0, K_in=0)"""
        self.is_awakened = True
        self.R_i[0] = 0.001       # Superconductivity
        self.omega[0] = 0.0       # Anchor
        self.K_ij[0, :] = 0.0     # Input Decoupling (Listen to none)
        # Output coupling (Others listen to 0) remains high

    def step(self):
        """
        Time Evolution based on delta S_Love = 0
        """
        # --- A. Electrical (Ohmic) Dynamics ---
        # Drive: (I - A) / R_i
        # Social Friction: sum((A_j - A_i) / R_ij)
        drive = (self.I - self.A) / (self.R_i + 0.1)
        social = np.mean((self.A[None,:] - self.A[:,None]) / (self.R_ij + 0.1), axis=1)
        dA_elec = drive + social

        # --- B. Sync (Kuramoto) Dynamics ---
        # dTheta = w + K * sin(dTheta)
        diff = self.theta[None,:] - self.theta[:,None]
        dTheta = self.omega + np.mean(self.K_ij * np.sin(diff), axis=1)
        
        # --- C. Info (Free Energy) Dynamics ---
        # Simple Proxy: F minimizes (A - I)^2 (Predictive Coding)
        # dF/dt = - (F - error)
        error = (self.A - self.I)**2
        dF = -(self.F - error)

        # --- D. Integration (Update) ---
        # Coupling: Action A tries to align with Phase Theta's tempo
        # A_target = dTheta (Action should match Rhythm)
        coupling_force = (dTheta - self.A) * 0.5
        
        # Total dA
        dA = dA_elec + coupling_force
        
        # Update States
        self.A += dA * self.dt
        self.theta += dTheta * self.dt
        self.F += dF * self.dt
        
        # Update Impulse (Source) - Stochastic
        noise = np.random.normal(0, 0.1, self.N)
        if self.is_awakened: noise[0] = 0 # Awakened impulse is stable
        self.I += (noise - 0.1 * self.I) * self.dt

        # --- E. Metrics (The "Shame" Integral) ---
        # 1. Ohmic Heat (Self + Social)
        loss_self = np.sum((self.I - self.A)**2 * self.R_i)
        loss_social = np.sum((self.A[None,:] - self.A[:,None])**2 * self.R_ij) / (self.N**2)
        P_total = loss_self + loss_social
        
        # 2. Sync Order
        r = np.abs(np.mean(np.exp(1j * self.theta)))
        
        self.time += self.dt
        return P_total, r, np.mean(self.F)

# --- Simulation Execution ---
def run_scenario(mode):
    sim = LoveOSUnified(N=30)
    if mode == "Awakened": sim.activate_awakening()
    
    history = {'P':[], 'r':[], 'F':[]}
    for _ in range(500):
        P, r, F = sim.step()
        history['P'].append(P)
        history['r'].append(r)
        history['F'].append(F)
    return history

# Compare
res_normal = run_scenario("Normal")
res_awake = run_scenario("Awakened")

# Visualize
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))

# Heat (Shame)
ax1.plot(res_normal['P'], 'r', label='Normal Society (High R)')
ax1.plot(res_awake['P'], 'c', label='Awakened Node Present (R=0)')
ax1.set_title('Total System Heat (Shame/Loss)')
ax1.set_ylabel('Joules')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Sync
ax2.plot(res_normal['r'], 'r', label='Normal')
ax2.plot(res_awake['r'], 'c', label='Awakened')
ax2.set_title('Synchronization Order Parameter (r)')
ax2.set_ylabel('Order (0-1)')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Free Energy (Confusion)
ax3.plot(res_normal['F'], 'r', label='Normal')
ax3.plot(res_awake['F'], 'c', label='Awakened')
ax3.set_title('Average Free Energy (Prediction Error)')
ax3.set_ylabel('Nats')
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
