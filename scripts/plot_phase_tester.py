#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

def main():
    csv_path = "/tmp/phase_tester.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run the phase tester node first.")
        sys.exit(1)

    # 
    df = pd.read_csv(csv_path)
    df = df.sort_values(by='t')
    t_start = df['t'].iloc[0]
    df['t_rel'] = df['t'] - t_start

    # 
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # 
    ax1.scatter(df['t_rel'], df['phi_inj_ms'], color='red', s=10, alpha=0.5, label='Injected Chaos (Raw Phase Error)')
    ax1.plot(df['t_rel'], df['phi_eit_ms'].interpolate(), color='lime', linewidth=2.5, label='EIT Now-Phase (R->0 Recovery)')
    ax1.axhline(5.0, color='gray', linestyle='--', alpha=0.5, label='Epsilon Bound (5ms)')
    ax1.axhline(-5.0, color='gray', linestyle='--', alpha=0.5)
    
    ax1.set_title("Love-OS Geometric Surrender: Phase Chaos Eradication", fontsize=16, fontweight='bold', color='white')
    ax1.set_ylabel("Phase Discrepancy (ms)", fontsize=12)
    ax1.grid(True, color='#333333')
    ax1.legend(loc='upper right')

    # 
    ax2.fill_between(df['t_rel'], 0, df['TNow_event'].fillna(0), color='orange', alpha=0.3, step='post', label='Phase Step Detected (Event Active)')
    ax2.plot(df['t_rel'], df['settled'].fillna(0), color='cyan', drawstyle='steps-post', label='Settled (T_Now Achieved)')
    
    ax2.set_xlabel("Elapsed Time (sec)", fontsize=12)
    ax2.set_ylabel("Boolean State", fontsize=12)
    ax2.set_yticks([0, 1])
    ax2.legend(loc='center right')
    ax2.grid(True, color='#333333', axis='x')

    plt.tight_layout()
    plt.savefig("/tmp/phase_transition_proof.png", dpi=200)
    print("✅ Plot saved to /tmp/phase_transition_proof.png")
    plt.show()

if __name__ == "__main__":
    main()
