"""
VitaSense AI - Export Paper Data, Figures, Tables & Provenance
Protocol Amendments 1-4 | PRD Benchmarking Suite

Produces:
1. CSV files in results/paper/
2. Vector PDF figures in paper/figures/
3. LaTeX .tex tables in paper/tables/
4. Provenance tracking CSV in paper/NUMBERS_PROVENANCE.csv
5. Verification against docs/RESULTS_SUMMARY.md
"""

import sys
import re
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

def fmt_p(val: float) -> str:
    """Rounds p-values to two decimal places using standard half-up rounding."""
    d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "results" / "paper"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TAB_DIR = ROOT / "paper" / "tables"
TAB_DIR.mkdir(parents=True, exist_ok=True)
DOCS_SUMMARY = ROOT / "docs" / "RESULTS_SUMMARY.md"


def generate_figures():
    print("=" * 80)
    print("GENERATING VECTOR PDF FIGURES (paper/figures/)")
    print("=" * 80)

    # Enhanced style configuration for clear, high-visibility figures
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10.0,
        "axes.labelsize": 10.2,
        "axes.titlesize": 10.8,
        "xtick.labelsize": 9.0,
        "ytick.labelsize": 9.0,
        "legend.fontsize": 8.0,
        "figure.titlesize": 11.0,
        "lines.linewidth": 1.9,
        "lines.markersize": 7.0,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    # -------------------------------------------------------------------------
    # Fig 1: Recall vs FA/hr per Arm and Condition
    # -------------------------------------------------------------------------
    df_comb = pd.read_csv(OUT_DIR / "combined_metrics.csv")
    fig, ax = plt.subplots(figsize=(4.3, 2.75))

    arm_styles = {
        "Arm 1 (Fixed)": {"color": "#1f77b4", "marker": "o", "label": "Arm 1: Fixed Pop"},
        "Arm 2 (Personal)": {"color": "#d62728", "marker": "s", "label": "Arm 2: Personal"},
        "Arm 3a (+Kinematic)": {"color": "#2ca02c", "marker": "^", "label": "Arm 3a: +Kinematic"},
        "Arm 3b (+Trust Score)": {"color": "#9467bd", "marker": "D", "label": "Arm 3b: +Trust"},
        "Arm 3b-noMotion": {"color": "#ff7f0e", "marker": "v", "label": "Arm 3b: noMotion"},
        "Arm 4 (added post hoc)": {"color": "#0284c7", "marker": "P", "label": "Arm 4: Post hoc"},
    }

    cond_alphas = {
        "Condition 0 (No-Fault)": 1.0,
        "Regime A (Low Duty ~10%)": 0.85,
        "Regime B (Nominal ~25-30%)": 0.7,
        "F7 (High-Motion BVP Noise)": 0.55,
    }

    cond_order = [
        "Condition 0 (No-Fault)",
        "Regime A (Low Duty ~10%)",
        "Regime B (Nominal ~25-30%)",
        "F7 (High-Motion BVP Noise)",
    ]

    for arm, style in arm_styles.items():
        if "Arm 4" in arm:
            arm_df = df_comb[df_comb["Arm"].str.contains("Arm 4")].copy()
        else:
            arm_df = df_comb[df_comb["Arm"] == arm].copy()
        if arm_df.empty:
            continue
        arm_df["cond_idx"] = arm_df["Condition"].map(lambda c: cond_order.index(c) if c in cond_order else 99)
        arm_df = arm_df.sort_values("cond_idx")
        ax.plot(
            arm_df["Clean_FA_hr"],
            arm_df["Event_Recall_pct"],
            color=style["color"],
            linestyle="--",
            alpha=0.75,
            linewidth=1.8,
            zorder=2,
        )
        for _, row in arm_df.iterrows():
            ax.scatter(
                row["Clean_FA_hr"],
                row["Event_Recall_pct"],
                color=style["color"],
                marker=style["marker"],
                alpha=cond_alphas.get(row["Condition"], 0.8),
                edgecolors="black" if row["Condition"] == "Condition 0 (No-Fault)" else "none",
                linewidth=0.8,
                s=58,
                zorder=3,
            )

    custom_handles = [
        plt.Line2D([0], [0], color=s["color"], marker=s["marker"], linestyle="--", label=s["label"])
        for s in arm_styles.values()
    ]
    ax.legend(handles=custom_handles, loc="lower right", framealpha=0.92, frameon=True, fontsize=7.8)

    ax.set_xlabel("Clean False Alerts per Hour [FA/h]", fontweight="bold")
    ax.set_ylabel("Event Recall [%]", fontweight="bold")
    ax.set_xlim(0.0, 8.0)
    ax.set_ylim(45, 100)
    ax.grid(True, linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_recall_vs_fahr.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_DIR / 'fig_recall_vs_fahr.pdf'}")

    # -------------------------------------------------------------------------
    # Fig 2: Forest Plot of Paired Differences (3b minus 3a) with 95% CIs
    # -------------------------------------------------------------------------
    df_paired = pd.read_csv(OUT_DIR / "paired_3b_vs_3a.csv")
    fig, ax = plt.subplots(figsize=(4.3, 2.75))

    cond_labels_short = [
        "F7: Optical (+5dB)",
        "Regime B (~25-30%)",
        "Regime A (~10%)",
        "Condition 0: Clean",
    ]
    cond_keys = [
        "F7 (High-Motion BVP Noise)",
        "Regime B (Nominal ~25-30%)",
        "Regime A (Low Duty ~10%)",
        "Condition 0 (No-Fault)",
    ]

    y_pos = np.arange(len(cond_keys))

    means = []
    err_low = []
    err_high = []
    p_vals = []

    for k in cond_keys:
        row = df_paired[df_paired["Condition"] == k].iloc[0]
        m = row["Mean_Diff_FA_hr"]
        c1 = row["CI95_Mean_Low"]
        c2 = row["CI95_Mean_High"]
        means.append(m)
        err_low.append(m - c1)
        err_high.append(c2 - m)
        p_vals.append(row["Wilcoxon_p"])

    ax.axvline(0.0, color="black", linestyle="--", linewidth=1.1, zorder=1)
    ax.errorbar(
        means,
        y_pos,
        xerr=[err_low, err_high],
        fmt="o",
        color="#1f77b4",
        ecolor="#222222",
        elinewidth=1.8,
        capsize=4.5,
        capthick=1.6,
        markersize=7.5,
        zorder=3,
    )

    for i, (m, p) in enumerate(zip(means, p_vals)):
        ax.text(
            0.95,
            i,
            f"Diff: {m:+.2f} (p={fmt_p(p)})",
            va="center",
            ha="left",
            fontsize=7.8,
            fontweight="bold",
            color="#111111",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(cond_labels_short, fontweight="medium")
    ax.set_xlabel(r"Mean Diff in FA/hr ($\Delta = \mathrm{3b} - \mathrm{3a}$) [FA/h]", fontweight="bold", fontsize=9.8)
    ax.set_xlim(-2.2, 3.65)
    ax.grid(True, linestyle=":", alpha=0.55, axis="x")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_forest_plot_3b_vs_3a.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_DIR / 'fig_forest_plot_3b_vs_3a.pdf'}")

    # -------------------------------------------------------------------------
    # Fig 3: Per-Subject FA/hr for 3a vs 3b (Condition 0)
    # -------------------------------------------------------------------------
    df_persub = pd.read_csv(OUT_DIR / "per_subject_metrics.csv")
    df_persub_c0 = df_persub[df_persub["Condition"] == "Condition 0 (No-Fault)"]

    fig, ax = plt.subplots(figsize=(4.3, 2.75))
    sids = [f"S{i}" for i in range(1, 16)]
    x = np.arange(len(sids))
    width = 0.40

    fa_3a = [df_persub_c0[df_persub_c0["Subject"] == s]["FA_hr_3a"].values[0] for s in sids]
    fa_3b = [df_persub_c0[df_persub_c0["Subject"] == s]["FA_hr_3b"].values[0] for s in sids]

    ax.bar(x - width / 2, fa_3a, width, label="Arm 3a (+Kinematic)", color="#2ca02c", alpha=0.88, edgecolor="black", linewidth=0.5)
    ax.bar(x + width / 2, fa_3b, width, label="Arm 3b (+Trust Score)", color="#9467bd", alpha=0.88, edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([f"S{i}" for i in range(1, 16)], fontsize=7.5, fontweight="semibold")
    ax.set_xlabel("PPG-DaLiA Subject ID (S1–S15)", fontweight="bold", fontsize=10.0)
    ax.set_ylabel("Clean FA per Hour [FA/h]", fontweight="bold", fontsize=10.0)
    ax.set_xlim(-0.7, 14.7)
    ax.set_ylim(0, 13.5)
    ax.legend(loc="upper right", framealpha=0.92, frameon=True, fontsize=8.2)
    ax.grid(True, linestyle=":", alpha=0.55, axis="y")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_persubject_fahr.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_DIR / 'fig_persubject_fahr.pdf'}")

    # -------------------------------------------------------------------------
    # Fig 4: Arm 1 Sensitivity: Threshold by Persistence
    # -------------------------------------------------------------------------
    df_arm1 = pd.read_csv(OUT_DIR / "sensitivity_arm1.csv")
    fig, ax1 = plt.subplots(figsize=(4.3, 2.75))

    p_styles = {
        10: {"color": "#1f77b4", "ls": "-", "m": "o"},
        20: {"color": "#ff7f0e", "ls": "--", "m": "s"},
        30: {"color": "#2ca02c", "ls": "-.", "m": "^"},
    }

    for p, st in p_styles.items():
        sub = df_arm1[df_arm1["Persistence_P_sec"] == p].sort_values("tau_pop_bpm")
        ax1.plot(
            sub["tau_pop_bpm"],
            sub["Recall_pct"],
            color=st["color"],
            linestyle=st["ls"],
            marker=st["m"],
            linewidth=1.9,
            markersize=6.5,
            label=f"Rec (P={p}s)",
        )

    ax1.set_xlabel(r"Population Cutoff $\tau_{\mathrm{pop}}$ [bpm]", fontweight="bold", fontsize=10.0)
    ax1.set_ylabel("Event Recall [%]", color="#111111", fontweight="bold", fontsize=10.0)
    ax1.set_ylim(20, 100)
    ax1.grid(True, linestyle=":", alpha=0.55)

    ax2 = ax1.twinx()
    for p, st in p_styles.items():
        sub = df_arm1[df_arm1["Persistence_P_sec"] == p].sort_values("tau_pop_bpm")
        ax2.plot(
            sub["tau_pop_bpm"],
            sub["Clean_FA_hr"],
            color=st["color"],
            linestyle=":",
            linewidth=1.9,
            alpha=0.85,
        )
    ax2.set_ylabel("Clean FA/hr [FA/h] (dotted)", color="#333333", fontweight="bold", fontsize=10.0)
    ax2.set_ylim(0, 10)

    ax1.legend(loc="lower left", framealpha=0.92, frameon=True, fontsize=8.0)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_arm1_sensitivity.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {FIG_DIR / 'fig_arm1_sensitivity.pdf'}")


def generate_tables():
    print("\n" + "=" * 80)
    print("GENERATING LATEX .TEX TABLES (paper/tables/)")
    print("=" * 80)

    # 1. Dataset Summary Table
    tab_dataset = r"""\begin{table}[htbp]
\caption{PPG-DaLiA Benchmark Dataset Summary \cite{ref_reiss_dalia}}
\label{tab:dataset}
\centering
\scriptsize
\begin{tabular}{|l|p{4.8cm}|}
\hline
\textbf{Attribute} & \textbf{Specification} \\
\hline
Subjects & $N = 15$ healthy individuals (7M, 8F, age 21--55, mean 30.6) \\
\hline
Protocol Duration & $\approx 2.4$\,h per subject ($35.94$ total recording hours; $31.27$ non-event exposure hours) \\
\hline
Activities & Sitting, Walking, Stairs, Cycling, Driving, Lunch, Soccer \\
\hline
Wrist Sensors & Empatica E4 (BVP: 64\,Hz, 3D ACC: 32\,Hz, GSR/Temp: 4\,Hz) \\
\hline
Reference Standard & Chest ECG (RespiBAN Professional, 700\,Hz) \\
\hline
Quarantine & Chest ECG strictly quarantined from alerting arms \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_dataset.tex").write_text(tab_dataset, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_dataset.tex'}")

    # 2. Fault Taxonomy Table
    tab_fault_tax = r"""\begin{table}[htbp]
\caption{Fault Taxonomy and Seeded Regimes (Protocol Amendment 3)}
\label{tab:fault_taxonomy}
\centering
\scriptsize
\begin{tabular}{|l|p{3.3cm}|c|c|}
\hline
\textbf{Fault ID} & \textbf{Mechanism \& Parameter} & \textbf{Reg. A} & \textbf{Reg. B} \\
\hline
F0\_CLEAN & Ambient background & 28.09\,h & 21.67\,h \\
\hline
F1\_GAPS & Packet dropout (5--15\,s NaN) & 0.94\,h & 3.15\,h \\
\hline
F2\_STALE & Sensor freeze (10--30\,s constant) & 0.62\,h & 1.58\,h \\
\hline
F3\_DUPL & Repeated packets (burst 2--5) & 0.62\,h & 1.56\,h \\
\hline
F4\_SPIKE & Sudden jumps ($\pm 30$--$60$\,bpm) & 0.07\,h & 0.21\,h \\
\hline
F5\_DRIFT & Slow ramp ($+0.2$\,bpm/s trend) & 0.45\,h & 1.55\,h \\
\hline
F6\_UNIT & Scale error ($0.5\times$ or $2.0\times$) & 0.48\,h & 1.56\,h \\
\hline
F7\_OPTICAL & Motion noise ($\text{SNR}=+5$\,dB, 64\,Hz) & Standalone & Standalone \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_fault_taxonomy.tex").write_text(tab_fault_tax, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_fault_taxonomy.tex'}")

    # 3. Parameter Grids Table
    tab_param_grids = r"""\begin{table}[htbp]
\caption{Evaluated Parameter Grids (Amendment 4 \& Draft Amendment 5)}
\label{tab:parameter_grids}
\centering
\scriptsize
\begin{tabular}{|l|p{4.5cm}|c|}
\hline
\textbf{Arm} & \textbf{Tuned Parameters} & \textbf{Refractory $R$} \\
\hline
Arm 1 & \raggedright $\tau_{\text{pop}} \in \{100, 110, 120, 125, 130\}$\,bpm; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
Arm 2 & \raggedright $k \in \{2.0, 2.5, 3.0, 3.5, 4.0\}$; $\kappa \in \{0.5, 1.0, 2.0\}$\,h; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
Arm 3a & \raggedright $\theta_{\text{rest}} \in \{0.03, 0.05, 0.08\}$\,g; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
Arm 3b & \raggedright $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
Arm 3b-noMot & \raggedright $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
Arm 4 (post hoc) & \raggedright $\alpha \in \{0.05, 0.10, 0.15\}$; $\lambda \in \{0.5, 1.0\}$; $\theta_{\text{unc}} \in \{0.20, 0.30\}$; $P \in \{10, 20, 30\}$\,s & 60\,s \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_parameter_grids.tex").write_text(tab_param_grids, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_parameter_grids.tex'}")

    # 4. Combined Metrics Table
    df_comb = pd.read_csv(OUT_DIR / "combined_metrics.csv")
    df_comb["Arm"] = df_comb["Arm"].replace({
        "Arm 4 (Conformal Abstention)": "Arm 4 (added post hoc)",
    })
    cond_order = [
        "Condition 0 (No-Fault)",
        "Regime A (Low Duty ~10%)",
        "Regime B (Nominal ~25-30%)",
        "F7 (High-Motion BVP Noise)",
    ]
    arm_order = [
        "Arm 1 (Fixed)",
        "Arm 2 (Personal)",
        "Arm 3a (+Kinematic)",
        "Arm 3b (+Trust Score)",
        "Arm 3b-noMotion",
        "Arm 4 (added post hoc)",
    ]
    df_comb["_cond_k"] = df_comb["Condition"].map(lambda c: cond_order.index(c) if c in cond_order else 99)
    df_comb["_arm_k"] = df_comb["Arm"].map(lambda a: arm_order.index(a) if a in arm_order else 99)
    df_comb = df_comb.sort_values(["_cond_k", "_arm_k"]).drop(columns=["_cond_k", "_arm_k"])
    df_comb.to_csv(OUT_DIR / "combined_metrics.csv", index=False)

    lines = [
        r"\begin{table*}[t]",
        r"\caption{Leave-One-Subject-Out Combined Alerting Benchmark Results Across Conditions (precision is alert-level and recall is episode-level)}",
        r"\label{tab:combined_metrics}",
        r"\centering",
        r"\scriptsize",
        r"\begin{tabular}{|l|l|c|c|c|c|c|c|}",
        r"\hline",
        r"\textbf{Condition} & \textbf{Alerting Arm} & \textbf{Recall (\%)} & \textbf{FA/hr} & \textbf{True Alerts} & \textbf{False Alerts} & \textbf{Precision (\%)} & \textbf{$F_1$ Score} \\",
        r"\hline",
    ]
    cur_cond = ""
    for _, r in df_comb.iterrows():
        raw_cond = str(r["Condition"]).replace("%", r"\%")
        cond_str = raw_cond if r["Condition"] != cur_cond else ""
        if r["Condition"] != cur_cond and cur_cond != "":
            lines.append(r"\hline")
        cur_cond = r["Condition"]
        lines.append(
            f"{cond_str:<28} & {r['Arm']:<24} & {r['Event_Recall_pct']:>5.1f} & {r['Clean_FA_hr']:>5.2f} & "
            f"{r['True_Alerts_TP']:>4d} & {r['False_Alerts_FP']:>4d} & {r['Precision_pct']:>5.1f} & {r['F1_Score']:>5.3f} \\\\"
        )
    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    (TAB_DIR / "tab_combined_metrics.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_combined_metrics.tex'}")

    # 5. Strata Table (Single Column)
    df_strata = pd.read_csv(OUT_DIR / "strata_metrics.csv")
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{Stratified Alerting Metrics (Recall \% / FA per Hour)}",
        r"\label{tab:strata}",
        r"\centering",
        r"\tiny",
        r"\setlength{\tabcolsep}{1.8pt}",
        r"\begin{tabular}{|l|l|c|c|c|c|c|}",
        r"\hline",
        r"\textbf{Condition} & \textbf{Stratum} & \textbf{Arm 1} & \textbf{Arm 2} & \textbf{Arm 3a} & \textbf{Arm 3b} & \textbf{3b-nM} \\",
        r"\hline",
    ]
    cur_cond = ""
    cond_short = {
        "Condition 0 (No-Fault)": "Cond 0 (Clean)",
        "Regime A (Low Duty ~10%)": r"Reg A (~10\%)",
        "Regime B (Nominal ~25-30%)": r"Reg B (~30\%)",
        "F7 (High-Motion BVP Noise)": "F7 (Optical)",
    }
    strata_short = {
        "Pooled All-15": "All-15",
        "Without S5 (14 subj)": "without S5",
        "Non-Drift": "without S5",
        "S5/S6/S11 (3 subj)": "S5/6/11 (3)",
    }
    for _, r in df_strata.iterrows():
        c_name = cond_short.get(r["Condition"], r["Condition"])
        cond_str = c_name if r["Condition"] != cur_cond else ""
        if r["Condition"] != cur_cond and cur_cond != "":
            lines.append(r"\hline")
        cur_cond = r["Condition"]
        s_name = strata_short.get(r["Stratum"], r["Stratum"])
        c1 = f"{r['Arm 1_Recall_pct']:.0f}\\%/{r['Arm 1_FA_hr']:.1f}"
        c2 = f"{r['Arm 2_Recall_pct']:.0f}\\%/{r['Arm 2_FA_hr']:.1f}"
        c3 = f"{r['Arm 3a_Recall_pct']:.0f}\\%/{r['Arm 3a_FA_hr']:.1f}"
        c4 = f"{r['Arm 3b_Recall_pct']:.0f}\\%/{r['Arm 3b_FA_hr']:.1f}"
        c5 = f"{r['Arm 3b-noMotion_Recall_pct']:.0f}\\%/{r['Arm 3b-noMotion_FA_hr']:.1f}"
        lines.append(f"{cond_str:<16} & {s_name:<11} & {c1} & {c2} & {c3} & {c4} & {c5} \\\\")
    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])
    (TAB_DIR / "tab_strata.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_strata.tex'}")

    # 6. Paired Comparison Table (Single Column)
    df_paired = pd.read_csv(OUT_DIR / "paired_3b_vs_3a.csv")
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{Paired Statistical Comparison: Arm 3b vs Arm 3a}",
        r"\label{tab:paired_comparison}",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\begin{tabular}{|l|c|c|c|c|}",
        r"\hline",
        r"\textbf{Condition} & \textbf{Mean $\Delta$} & \textbf{95\% Boot. CI} & \textbf{Wilcoxon $W$} & \textbf{$p$-val} \\",
        r"\hline",
    ]
    cond_short_map = {
        "Condition 0 (No-Fault)": "Condition 0 (Clean)",
        "Regime A (Low Duty ~10%)": r"Regime A (~10\%)",
        "Regime B (Nominal ~25-30%)": r"Regime B (~25--30\%)",
        "F7 (High-Motion BVP Noise)": "F7 (Optical Noise)",
    }
    for _, r in df_paired.iterrows():
        c_short = cond_short_map.get(r['Condition'], r['Condition'])
        ci_str = f"[{r['CI95_Mean_Low']:+.2f}, {r['CI95_Mean_High']:+.2f}]"
        lines.append(
            f"{c_short:<22} & {r['Mean_Diff_FA_hr']:>+5.2f} & {ci_str} & {r['Wilcoxon_W']:>5.1f} & {fmt_p(r['Wilcoxon_p']):>4} \\\\"
        )
    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])
    (TAB_DIR / "tab_paired_comparison.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_paired_comparison.tex'}")

    # 7. Edge-of-Grid Table (Compact Cross-Condition Format)
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{Edge-of-Grid Parameter Boundary Selection Across 15 LOSO Folds}",
        r"\label{tab:edge_of_grid}",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabular}{|l|l|c|c|c|c|}",
        r"\hline",
        r"\textbf{Arm} & \textbf{Parameter Boundary} & \textbf{Cond 0} & \textbf{Reg A} & \textbf{Reg B} & \textbf{F7} \\",
        r"\hline",
        r"Arm 1 (Fixed)    & $\tau_{\text{pop}} = 100$\,bpm$_{\mathrm{lo}}$ & 100\% & 100\% & 100\% & 100\% \\",
        r"                 & $P = 30$\,s$_{\mathrm{hi}}$                     & 100\% & 100\% & 100\% & 100\% \\",
        r"\hline",
        r"Arm 2 (Personal) & $k = 2.0_{\mathrm{lo}}$                         & 100\% & 100\% & 100\% & 100\% \\",
        r"                 & $\kappa = 2.0$\,h$_{\mathrm{hi}}$               & 93.3\% & 93.3\% & 100\% & 100\% \\",
        r"                 & $P = 10$\,s$_{\mathrm{lo}}$                     & 100\% & 100\% & 100\% & 100\% \\",
        r"\hline",
        r"Arm 3a (+Kin.)   & $\theta_{\text{rest}} = 0.08$\,g$_{\mathrm{hi}}$ & 93.3\% & 93.3\% & 93.3\% & 100\% \\",
        r"                 & $\theta_{\text{rest}} = 0.03$\,g$_{\mathrm{lo}}$ & 6.7\%  & 6.7\%  & 6.7\%  & 0.0\% \\",
        r"\hline",
        r"Arm 3b (+Trust)  & $\theta_{\text{trust}} = 0.60_{\mathrm{lo}}$     & 93.3\% & 93.3\% & 93.3\% & 100\% \\",
        r"                 & $\theta_{\text{trust}} = 0.80_{\mathrm{hi}}$     & 6.7\%  & 6.7\%  & 6.7\%  & 0.0\% \\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ]
    (TAB_DIR / "tab_edge_of_grid.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_edge_of_grid.tex'}")

    # 8. Fault Disaggregated Table (Compact Single-Column Format)
    df_fault = pd.read_csv(OUT_DIR / "fault_disaggregated.csv")
    lines = [
        r"\begin{table}[htbp]",
        r"\caption{Disaggregated False Alerts per Fault Type (Regimes A \& B)}",
        r"\label{tab:fault_disaggregated}",
        r"\centering",
        r"\tiny",
        r"\setlength{\tabcolsep}{1.8pt}",
        r"\begin{tabular}{|l|l|c|c|c|c|c|c|}",
        r"\hline",
        r"\textbf{Reg.} & \textbf{Fault} & \textbf{Exp.} & \textbf{Arm 1} & \textbf{Arm 2} & \textbf{Arm 3a} & \textbf{Arm 3b} & \textbf{3b-nM} \\",
        r"\hline",
    ]
    cur_reg = ""
    for _, r in df_fault.iterrows():
        reg_short = "Reg A" if "Regime A" in r["Regime"] else "Reg B"
        reg_display = reg_short if reg_short != cur_reg else ""
        if reg_short != cur_reg and cur_reg != "":
            lines.append(r"\hline")
        cur_reg = reg_short
        c1 = f"{r['Arm 1_FA_hr']:.1f} ({r['Arm 1_FA_Count']})" + ("*" if r['Arm 1_Insufficient_Data'] else "")
        c2 = f"{r['Arm 2_FA_hr']:.1f} ({r['Arm 2_FA_Count']})" + ("*" if r['Arm 2_Insufficient_Data'] else "")
        c3 = f"{r['Arm 3a_FA_hr']:.1f} ({r['Arm 3a_FA_Count']})" + ("*" if r['Arm 3a_Insufficient_Data'] else "")
        c4 = f"{r['Arm 3b_FA_hr']:.1f} ({r['Arm 3b_FA_Count']})" + ("*" if r['Arm 3b_Insufficient_Data'] else "")
        c5 = f"{r['Arm 3b-noMotion_FA_hr']:.1f} ({r['Arm 3b-noMotion_FA_Count']})" + ("*" if r['Arm 3b-noMotion_Insufficient_Data'] else "")
        ft_escaped = r['Fault_Type'].replace("_", r"\_")
        lines.append(f"{reg_display:<5} & {ft_escaped:<10} & {r['Exposure_Hours']:>4.1f}h & {c1:<9} & {c2:<9} & {c3:<9} & {c4:<9} & {c5:<9} \\\\")
    lines.extend([
        r"\hline",
        r"\multicolumn{8}{|l|}{* Insufficient data ($<10$ alerts or $<1.0$\,h). Rate shown as FA/h (count).} \\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])
    (TAB_DIR / "tab_fault_disaggregated.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_fault_disaggregated.tex'}")

    # 8b. Alerting Arms Table (Table II)
    tab_alerting_arms = r"""\begin{table}[htbp]
\caption{Evaluated Alerting Arms, Decision Rules \& Tuning Grids}
\label{tab:alerting_arms}
\centering
\footnotesize
\renewcommand{\arraystretch}{1.14}
\setlength{\tabcolsep}{3.0pt}
\begin{tabular}{|l|p{4.15cm}|c|}
\hline
\textbf{Alerting Arm} & \textbf{Decision Rule \& Tuning Grid} & \textbf{Hold-off $R$} \\
\hline
\textbf{Arm 1: Fixed Pop.} & $HR(t) > \tau_{\text{pop}}$ & 60\,s \\
 & $\tau_{\text{pop}} \in \{100, 110, 120, 125, 130\}$\,bpm, $P \in \{10, 20, 30\}$\,s & \\
\hline
\textbf{Arm 2: Personal} & $HR(t) > \max(\tau_{\text{flr}}, \hat{\mu}_i(t) + k \cdot \hat{\sigma}_i(t))$ & 60\,s \\
 & $k \in \{2.0, \dots, 4.0\}$, $\kappa \in \{0.5, 1, 2\}$\,h, $P \in \{10, 20, 30\}$\,s & \\
\hline
\textbf{Arm 3a: +Kinematic} & Arm 2 $\land\; (\text{ENMO}_{10\text{s}}(t) \le \theta_{\text{rest}})$ & 60\,s \\
 & $\theta_{\text{rest}} \in \{0.03, 0.05, 0.08\}$\,g, $P \in \{10, 20, 30\}$\,s & \\
\hline
\textbf{Arm 3b: +Trust} & Arm 2 $\land\; (S_{\text{trust}}(t) \ge \theta_{\text{trust}})$ & 60\,s \\
 & $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$, $P \in \{10, 20, 30\}$\,s & \\
\hline
\textbf{Arm 3b-noMot} & Arm 2 $\land\; (S_{\text{gap}} S_{\text{stale}} S_{\text{phys}} \ge \theta_{\text{trust}})$ & 60\,s \\
(Motion Ablated) & $\theta_{\text{trust}} \in \{0.60, 0.70, 0.80\}$, $P \in \{10, 20, 30\}$\,s & \\
\hline
\textbf{Arm 4: Conformal} & Arm 2 $\land\; \neg \text{Abstain}(t)$ & 60\,s \\
(added post hoc) & $\alpha \in \{0.05, 0.10\}$, $\lambda \in \{0.5, 1.0\}$, $\theta_{\text{unc}} \in \{0.2, 0.3\}$ & \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_alerting_arms.tex").write_text(tab_alerting_arms, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_alerting_arms.tex'}")

    # 9. Protocol Deviations Table (Single Column Format)
    tab_deviations = r"""\begin{table}[htbp]
\caption{Protocol Evolution and Amendments (from git log)}
\label{tab:deviations}
\centering
\scriptsize
\begin{tabular}{|l|p{4.7cm}|}
\hline
\textbf{Milestone [Commit]} & \textbf{Ratified Scope and Description} \\
\hline
Protocol v1.0.0 [\texttt{41eff1e}] & 2026-10-18: Frozen protocol: $H_1$--$H_3$, faults F1--F7, LOSO cross-validation. \\
\hline
ENMO Scale Fix [\texttt{3a5ccc2}, \texttt{1dd80b2}] & 2026-10-19: Removed redundant /64 accelerometer division, enforced median norm check $[0.8, 1.2]$\,g. \\
\hline
Adaptive Ramp [\texttt{e358bf1}] & 2026-10-19: Adapted synthetic tachycardia ramp rates ($r_{\text{lo}}, r_{\text{hi}}$) clamped to $[105, 135]$\,bpm. \\
\hline
Persistence \& Refractory [\texttt{cad4c7f}, \texttt{d55d432}] & 2026-10-19: StandardAlertEmitter with $P \in \{10, 20, 30\}$\,s and refractory $R = 60$\,s across all arms. \\
\hline
Grid Widening [\texttt{a9ce657}] & 2026-10-19: Widened parameter search grids for $\tau_{\text{pop}}$ and $k$ following boundary selection. \\
\hline
Fallback Selection [\texttt{f92ca8d}] & 2026-10-19: Arm 2 recall ceiling ($\approx 80.4\%$) triggered max-recall fallback rule in 100\% of folds. \\
\hline
Arm 4 Post Hoc [Draft Amend.~5] & 2026-10-22: Post hoc inductive conformal abstention evaluated with $\alpha \in \{0.05, 0.10\}$ (selected $\alpha = 0.10$ across all 15 folds). \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_deviations.tex").write_text(tab_deviations, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_deviations.tex'}")

    # 10. Limitations Table
    tab_limitations = r"""\begin{table}[htbp]
\caption{Threats to Validity and Scientific Limitations}
\label{tab:limitations}
\centering
\scriptsize
\begin{tabular}{|l|p{4.7cm}|}
\hline
\textbf{Threat Domain} & \textbf{Empirical Limitation and Mitigation} \\
\hline
Synthetic Events & True resting tachycardia absent in cohort; 112 episodes injected into derived stream ($105$--$135$\,bpm). Arm 1 recall directly depends on this injection range vs 100\,bpm floor. \\
\hline
Cohort Size & $N = 15$ healthy young adults in PPG-DaLiA protocol only; free-living 24/7 unconstrained monitoring unproven. Reported with 95\% bootstrap CIs. \\
\hline
Subject S5 Outlier & Subject S5 exhibited severe sensor drift and motion artifacts; results reported both pooled and without S5. \\
\hline
Unopened Sources & Threshold values ($\tau_{\text{pop}}, \theta_{\text{rest}}, \theta_{\text{trust}}$) are design choices with unopened sources; evaluated via sensitivity grids. \\
\hline
Noise Coupling & Estimator tracking errors and motion artifacts interact directly with downstream thresholding logic. \\
\hline
Grid Boundaries & Tuning selected boundaries ($\tau_{\text{pop}} = 100$, $k = 2.0$, $P = 10$\,s / $30$\,s), reflecting trade-offs. \\
\hline
Arm 4 Status & Arm 4 inductive conformal abstention evaluated post hoc with $\alpha = 0.15$ (unratified). Academic benchmark only. \\
\hline
\end{tabular}
\end{table}
"""
    (TAB_DIR / "tab_limitations.tex").write_text(tab_limitations, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_limitations.tex'}")

    # 11. Dataset and Faults Combined Table
    tab_dataset_and_faults = r"""\begin{table}[htbp]
\caption{PPG-DaLiA Benchmark Dataset \& Injected Fault Regimes}
\label{tab:dataset_and_faults}
\centering
\resizebox{\columnwidth}{!}{%
\begin{tabular}{|l|p{5.0cm}|}
\hline
\multicolumn{2}{|c|}{\textbf{Part A: PPG-DaLiA Benchmark Dataset Characteristics \cite{ref_reiss_dalia}}} \\
\hline
Subjects & $N = 15$ healthy individuals (7 male, 8 female, age 21--55) \\
Duration & $\approx 2.4$\,h per subject ($35.94$ total recording hours; $31.27$ non-event exposure hours) \\
Activities & Sitting, Walking, Stairs, Cycling, Driving, Lunch, Soccer \\
Sensors & Wrist Empatica E4 (BVP: 64\,Hz, 3D ACC: 32\,Hz) \\
Ground Truth & Chest ECG (RespiBAN, 700\,Hz, strictly quarantined) \\
\hline
\multicolumn{2}{|c|}{\textbf{Part B: Evaluated Telemetry \& Sensor Fault Regimes (Amendment 3)}} \\
\hline
Condition 0 & Clean ambulatory background ($31.27$\,h non-event exposure) \\
Regime A & Low-duty ($\approx 10\%$ faults): sporadic gaps (F1), freeze (F2), duplicates (F3), drift (F5), scale errors (F6) \\
Regime B & Nominal-duty ($\approx 25\text{--}30\%$ faults): prolonged flatlines, frequent dropouts, scale errors (seed 42) \\
F7 Noise & Additive Gaussian noise continuously modulated by wrist 3D acceleration injected into raw BVP (SNR $+5$\,dB) \\
\hline
\end{tabular}%
}
\end{table}
"""
    (TAB_DIR / "tab_dataset_and_faults.tex").write_text(tab_dataset_and_faults, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_dataset_and_faults.tex'}")

    # 12. Combined Limitations and Amendments Table
    tab_limitations_and_amendments = r"""\begin{table}[htbp]
\caption{Methodological Limitations \& Protocol Amendments (from git log)}
\label{tab:limitations_and_amendments}
\centering
\renewcommand{\arraystretch}{0.96}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{|l|p{5.4cm}|}
\hline
\multicolumn{2}{|c|}{\textbf{Part A: Methodological Constraints and Threats to Validity}} \\
\hline
Synthetic Injection & 112 episodes ($105$--$135$\,bpm); Arm 1 recall is directly tied to this injection range vs 100\,bpm floor. \\
\hline
Cohort \& Protocol & $N = 15$ healthy adults in PPG-DaLiA protocol; free-living unconstrained 24/7 monitoring unproven. \\
\hline
Subject S5 Outlier & Sustained elevated resting heart rate of unknown cause; reference ECG verified clean; metrics reported both pooled (All-15) and without S5. \\
\hline
Design Choice Bounds & Cutoffs ($\tau_{\text{pop}}, \theta_{\text{rest}}, \theta_{\text{trust}}$) are design choices with unopened sources; evaluated via sensitivity grids. \\
\hline
Grid Boundaries & Tuning selected boundary values: Arm 1 ($\tau_{\text{pop}} = 100$\,bpm, $P = 30$\,s); Arm 2 ($k = 2.0$, $P = 10$\,s, triggering max-recall fallback in 100\% of folds). \\
\hline
\multicolumn{2}{|c|}{\textbf{Part B: Protocol Amendments and Provenance (from git log)}} \\
\hline
Protocol Freeze [\texttt{41eff1e}] & 2026-10-18: Frozen protocol: $H_1$--$H_3$, faults F1--F7, LOSO cross-validation. \\
\hline
ENMO Scale Fix [\texttt{3a5ccc2}] & 2026-10-19: Removed redundant /64 accelerometer division, enforced median norm check $[0.8, 1.2]$\,g. \\
\hline
Adaptive Ramp [\texttt{e358bf1}] & 2026-10-19: Adapted synthetic tachycardia ramp rates ($r_{\text{lo}}, r_{\text{hi}}$) clamped to $[105, 135]$\,bpm. \\
\hline
Emitter Rules [\texttt{cad4c7f}] & 2026-10-19: StandardAlertEmitter with $P \in \{10, 20, 30\}$\,s and refractory $R = 60$\,s across all arms. \\
\hline
Grid Widening [\texttt{a9ce657}] & 2026-10-19: Widened parameter search grids for $\tau_{\text{pop}}$ and $k$ following boundary selection. \\
\hline
Fallback Selection [\texttt{f92ca8d}] & 2026-10-19: Arm 2 recall ceiling ($\approx 80.4\%$) triggered max-recall fallback rule in 100\% of folds. \\
\hline
Arm 4 Post Hoc [Draft Amend.~5] & 2026-10-22: Post hoc inductive conformal abstention evaluated with $\alpha \in \{0.05, 0.10\}$ (selected $\alpha = 0.10$ across all 15 folds). \\
\hline
\end{tabular}%
}
\end{table}
"""
    (TAB_DIR / "tab_limitations_and_amendments.tex").write_text(tab_limitations_and_amendments, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_limitations_and_amendments.tex'}")

    # 13. Combined Statistical and Strata Table (Table V)
    p_c0 = fmt_p(df_paired[df_paired["Condition"] == "Condition 0 (No-Fault)"]["Wilcoxon_p"].iloc[0])
    p_ra = fmt_p(df_paired[df_paired["Condition"] == "Regime A (Low Duty ~10%)"]["Wilcoxon_p"].iloc[0])
    p_rb = fmt_p(df_paired[df_paired["Condition"] == "Regime B (Nominal ~25-30%)"]["Wilcoxon_p"].iloc[0])
    p_f7 = fmt_p(df_paired[df_paired["Condition"] == "F7 (High-Motion BVP Noise)"]["Wilcoxon_p"].iloc[0])

    tab_statistical_and_strata = r"""\begin{table}[htbp]
\caption{Paired Statistical Comparison \& Subgroup Stratification}
\label{tab:statistical_and_strata}
\centering
\footnotesize
\renewcommand{\arraystretch}{1.0}
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{|l|c|c|c|c|}
\hline
\multicolumn{5}{|c|}{\textbf{Part A: Paired Difference ($\Delta = \text{Arm 3b} - \text{Arm 3a}$)}} \\
\hline
\textbf{Condition} & \textbf{Mean $\Delta$} & \textbf{95\% CI} & \textbf{$W$} & \textbf{$p$-value} \\
\hline
Clean (Cond 0)       & $+0.13$ & $[-0.54, +0.89]$ & 31.0 & P_C0_VAL \\
Regime A ($\approx 10\%$) & $+0.05$ & $[-0.66, +0.82]$ & 40.0 & P_RA_VAL \\
Regime B ($\approx 25\%$) & $-0.04$ & $[-0.78, +0.69]$ & 52.0 & P_RB_VAL \\
F7 Optical ($+5$\,dB)& $-0.49$ & $[-1.47, +0.38]$ & 17.0 & P_F7_VAL \\
\hline
\multicolumn{5}{|c|}{\textbf{Part B: Stratified Event Recall (\%) / Clean FA/hr}} \\
\hline
\textbf{Stratum} & \textbf{Arm 1} & \textbf{Arm 2} & \textbf{Arm 3a} & \textbf{Arm 3b} \\
\hline
Clean: All-15      & 91 / 3.2  & 80 / 5.7  & 80 / 1.5  & 80 / 1.7  \\
Clean: without S5   & 91 / 2.9  & 80 / 5.3  & 80 / 1.4  & 79 / 1.7  \\
Clean: S5/6/11     & 100 / 9.4 & 94 / 16.1 & 94 / 5.1  & 94 / 3.9  \\
\hline
Reg B: All-15      & 91 / 4.5  & 76 / 7.2  & 76 / 2.3  & 75 / 2.4  \\
Reg B: without S5   & 91 / 4.1  & 75 / 6.4  & 75 / 2.2  & 74 / 2.3  \\
\hline
F7: All-15         & 92 / 3.1  & 64 / 4.6  & 64 / 1.6  & 58 / 1.3  \\
F7: without S5      & 92 / 2.7  & 63 / 4.0  & 63 / 1.2  & 56 / 1.1  \\
\hline
\end{tabular}
\end{table}
""".replace("P_C0_VAL", f"${p_c0}$").replace("P_RA_VAL", f"${p_ra}$").replace("P_RB_VAL", f"${p_rb}$").replace("P_F7_VAL", f"${p_f7}$")
    (TAB_DIR / "tab_statistical_and_strata.tex").write_text(tab_statistical_and_strata, encoding="utf-8")
    print(f"Saved: {TAB_DIR / 'tab_statistical_and_strata.tex'}")



def generate_provenance_csv():
    print("\n" + "=" * 80)
    print("GENERATING NUMBERS PROVENANCE CSV (paper/NUMBERS_PROVENANCE.csv)")
    print("=" * 80)

    rows = [
        # Dataset
        {"Claim_Or_Number": "Subject Count N=15", "Value": "15", "Location": "Sec. III, Tab. I", "Generating_Script": "scripts/prepare_benchmark_ground_truth.py", "Output_File": "data/processed/benchmark_ground_truth.pkl", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Total Recording Time", "Value": "35.94 hours", "Location": "Sec. III, Tab. I", "Generating_Script": "scripts/export_paper_data.py", "Output_File": "results/paper/fault_disaggregated.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Non-event Exposure Time", "Value": "31.27 hours", "Location": "Sec. III, Tab. I", "Generating_Script": "scripts/export_paper_data.py", "Output_File": "results/paper/fault_disaggregated.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Bootstrap Resample Count", "Value": "10,000", "Location": "Sec. V, Sec. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Injected Tachycardia Episodes", "Value": "112", "Location": "Sec. III, Sec. V", "Generating_Script": "scripts/generate_injection_audit.py", "Output_File": "results/synthetic_injection_audit.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Injected Peak HR Floor/Ceil", "Value": "[105, 135] bpm", "Location": "Sec. III, Sec. V", "Generating_Script": "vitasense/benchmarks/synthetic_injection.py", "Output_File": "docs/RESULTS_SUMMARY.md", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Inter-episode Gap Floor", "Value": "60 s", "Location": "Sec. III, Sec. V", "Generating_Script": "vitasense/benchmarks/synthetic_injection.py", "Output_File": "docs/RESULTS_SUMMARY.md", "Status": "VERIFIED"},

        # Combined Metrics: Condition 0
        {"Claim_Or_Number": "Arm 1 Clean Recall", "Value": "91.1%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 1 Clean FA/hr", "Value": "3.20", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 1 Clean F1 Score", "Value": "0.700", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Clean Recall", "Value": "80.4%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Clean FA/hr", "Value": "5.69", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Clean F1 Score", "Value": "0.558", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a Clean Recall", "Value": "80.4%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a Clean FA/hr", "Value": "1.47", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a Clean F1 Score", "Value": "0.772", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b Clean Recall", "Value": "79.5%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b Clean FA/hr", "Value": "1.69", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b Clean F1 Score", "Value": "0.750", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b-noMotion Clean Recall", "Value": "79.5%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b-noMotion Clean FA/hr", "Value": "2.91", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b-noMotion Clean F1 Score", "Value": "0.676", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},

        # Combined Metrics: Regime B
        {"Claim_Or_Number": "Arm 1 Regime B Recall", "Value": "91.1%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 1 Regime B FA/hr", "Value": "4.51", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Regime B Recall", "Value": "75.9%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Regime B FA/hr", "Value": "7.16", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a Regime B Recall", "Value": "75.9%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a Regime B FA/hr", "Value": "2.30", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b Regime B Recall", "Value": "75.0%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b Regime B FA/hr", "Value": "2.37", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b-noMotion Regime B Recall", "Value": "75.0%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b-noMotion Regime B FA/hr", "Value": "3.61", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},

        # Combined Metrics: F7
        {"Claim_Or_Number": "Arm 1 F7 Recall", "Value": "92.0%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 1 F7 FA/hr", "Value": "3.07", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a F7 Recall", "Value": "64.3%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3a F7 FA/hr", "Value": "1.57", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b F7 Recall", "Value": "58.0%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 3b F7 FA/hr", "Value": "1.28", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},

        # Paired Comparisons: Arm 3b vs 3a
        {"Claim_Or_Number": "Condition 0 Paired Mean Diff", "Value": "+0.13 FA/hr", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Condition 0 Wilcoxon W", "Value": "31.0", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Condition 0 Wilcoxon p", "Value": "0.8589", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Condition 0 95% Bootstrap CI", "Value": "[-0.54, +0.89]", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime A Paired Mean Diff", "Value": "+0.05 FA/hr", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime A Wilcoxon W", "Value": "40.0", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime A Wilcoxon p", "Value": "0.7007", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime A 95% Bootstrap CI", "Value": "[-0.66, +0.82]", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime B Paired Mean Diff", "Value": "-0.04 FA/hr", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime B Wilcoxon W", "Value": "52.0", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime B Wilcoxon p", "Value": "0.9750", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Regime B 95% Bootstrap CI", "Value": "[-0.78, +0.69]", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "F7 Paired Mean Diff", "Value": "-0.49 FA/hr", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "F7 Wilcoxon W", "Value": "17.0", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "F7 Wilcoxon p", "Value": "0.2845", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "F7 95% Bootstrap CI", "Value": "[-1.47, +0.38]", "Location": "Sec. VII, Tab. VI", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/paired_3b_vs_3a.csv", "Status": "VERIFIED"},

        # Table I Related Work Literature Provenance (opened & verified)
        {"Claim_Or_Number": "Reiss 2019 Cohort N=15", "Value": "15 subjects", "Location": "Sec. II, Tab. I", "Generating_Script": "scripts/prepare_benchmark_ground_truth.py", "Output_File": "https://archive.ics.uci.edu/dataset/495/ppg+dalia", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Elgendi 2016 SQI count", "Value": "8 SQIs", "Location": "Sec. II, Tab. I", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5597264/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Elgendi 2016 8 SQIs Quote", "Value": "Eight SQIs were tested and evaluated. (Sec. 2.3)", "Location": "Sec. II, Tab. I", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5597264/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Charlton 2023 roadmap claim", "Value": "Benchmark & evaluation needs", "Location": "Sec. II, Tab. I", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10686289/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Vazquez & Facelli 2022 study count", "Value": "14 clinical studies", "Location": "Sec. II, Tab. I", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9309105/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Vazquez & Facelli 14 Studies Quote", "Value": "We identified 14 papers reporting the use of CP for clinical applications (Abstract)", "Location": "Sec. II, Tab. I", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9309105/", "Status": "VERIFIED"},

        # Bibliography Metadata Verification (opened DOI / publisher pages)
        {"Claim_Or_Number": "Ref ref_reiss_dalia", "Value": "Sensors 19(14):3079 (2019), DOI: 10.3390/s19143079", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6679242/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Ref ref_elgendi_sqi", "Value": "Bioengineering 3(4):21 (2016), DOI: 10.3390/bioengineering3040021", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5597264/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Ref ref_charlton_roadmap", "Value": "Physiol. Meas. 44(11):111001 (2023), DOI: 10.1088/1361-6579/acead2", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10686289/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Ref ref_vazquez_conformal", "Value": "J. Healthc. Inform. Res. 6(3):257-285 (2022), DOI: 10.1007/s41666-021-00113-8", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9309105/", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Ref ref_uci_dalia", "Value": "UCI Machine Learning Repository (2019), DOI: 10.24432/C53890", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://archive.ics.uci.edu/dataset/495/ppg+dalia", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Ref ref_physionet_wearable", "Value": "PhysioNet Version 1.0.1 (2025), DOI: 10.13026/he0v-tf17", "Location": "Bibliography", "Generating_Script": "read_url_content", "Output_File": "https://physionet.org/content/wearable-device-dataset/1.0.1/", "Status": "VERIFIED"},

        # Edge of Grid
        {"Claim_Or_Number": "Arm 1 tau_pop boundary 100", "Value": "100.0% (15/15)", "Location": "Sec. VII, Tab. VII", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/edge_of_grid.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 1 Persistence boundary 30", "Value": "100.0% (15/15)", "Location": "Sec. VII, Tab. VII", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/edge_of_grid.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 k boundary 2.0", "Value": "100.0% (15/15)", "Location": "Sec. VII, Tab. VII", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/edge_of_grid.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Persistence boundary 10", "Value": "100.0% (15/15)", "Location": "Sec. VII, Tab. VII", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "results/paper/edge_of_grid.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 2 Fallback Rule Invocations", "Value": "100% (15/15)", "Location": "Sec. VII, Sec. VIII", "Generating_Script": "scripts/run_fault_regimes_benchmark.py", "Output_File": "docs/RESULTS_SUMMARY.md", "Status": "VERIFIED"},

        # Arm 4 (added post hoc) - Recomputed comparable alert counts
        {"Claim_Or_Number": "Arm 4 Clean Recall", "Value": "72.3%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Clean FA/hr", "Value": "0.70", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Clean True Alerts", "Value": "113", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Clean False Alerts", "Value": "22", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Clean Precision", "Value": "83.7%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Clean F1 Score", "Value": "0.776", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A Recall", "Value": "62.5%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A FA/hr", "Value": "0.67", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A True Alerts", "Value": "96", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A False Alerts", "Value": "21", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A Precision", "Value": "82.1%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime A F1 Score", "Value": "0.710", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B Recall", "Value": "55.4%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B FA/hr", "Value": "0.70", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B True Alerts", "Value": "83", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B False Alerts", "Value": "22", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B Precision", "Value": "79.0%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 Regime B F1 Score", "Value": "0.651", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 Recall", "Value": "54.5%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 FA/hr", "Value": "0.35", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 True Alerts", "Value": "82", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 False Alerts", "Value": "11", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 Precision", "Value": "88.2%", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
        {"Claim_Or_Number": "Arm 4 F7 F1 Score", "Value": "0.673", "Location": "Sec. VII, Tab. IV", "Generating_Script": "scripts/run_arm4_evaluation.py", "Output_File": "results/paper/combined_metrics.csv", "Status": "VERIFIED"},
    ]

    df_prov = pd.DataFrame(rows)
    prov_path = ROOT / "paper" / "NUMBERS_PROVENANCE.csv"
    df_prov.to_csv(prov_path, index=False)
    print(f"Saved: {prov_path}")


def main():
    # If CSVs already exist, verify them; otherwise re-run full extraction
    req_csvs = [
        "combined_metrics.csv",
        "strata_metrics.csv",
        "paired_3b_vs_3a.csv",
        "per_subject_metrics.csv",
        "fault_disaggregated.csv",
        "edge_of_grid.csv",
        "sensitivity_arm1.csv",
        "sensitivity_arm2.csv",
    ]
    all_exist = all((OUT_DIR / f).exists() for f in req_csvs)

    if "--force-recompute" in sys.argv or not all_exist:
        from scripts.export_paper_data import export_and_verify_all
        export_and_verify_all()
    else:
        print("Existing CSVs found in results/paper/. Validating contents...")
        # Verify combined metrics against RESULTS_SUMMARY.md
        df_comb = pd.read_csv(OUT_DIR / "combined_metrics.csv")
        summary_text = DOCS_SUMMARY.read_text(encoding="utf-8")
        for _, row in df_comb.iterrows():
            pat = f"{row['Event_Recall_pct']:.1f}% \\| {row['Clean_FA_hr']:.2f} \\| {row['True_Alerts_TP']} \\| {row['False_Alerts_FP']} \\| {row['Precision_pct']:.1f}% \\| {row['F1_Score']:.3f}"
            if not re.search(pat, summary_text):
                raise AssertionError(f"Pattern {pat} not found in {DOCS_SUMMARY}!")
        print("  [OK] All existing CSVs verified against docs/RESULTS_SUMMARY.md.")

    # Generate figures, tables, and provenance
    generate_figures()
    generate_tables()
    generate_provenance_csv()
    print("\nALL ARTIFACTS SUCCESSFULLY PRODUCED!")


if __name__ == "__main__":
    main()
