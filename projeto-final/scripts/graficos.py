"""Gráficos quantitativos: performance profile e boxplot dos tempos.

Performance profile (Dolan e Moré, 2002), como no artigo-base: para cada
instância, o "tempo para resolver" de cada método é dividido pelo menor tempo
entre os métodos (razão de desempenho r). A curva mostra a fração das
instâncias com r <= tau.
  - Exato: tempo até provar o ótimo.
  - Metaheurísticas: tempo médio até a melhor solução, nas execuções que
    chegaram ao ótimo; infinito se nenhuma chegou.

Uso: python scripts/graficos.py ROTULO=arquivo.csv:config [...]
Saída: resultados/figuras/perf_profile.png e boxplot_tempos.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
FIG = RAIZ / "resultados" / "figuras"
# paleta categórica validada (ordem fixa): azul, laranja, verde-água
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
ESTILOS = ["-", "--", "-.", ":"]
TINTA, TINTA2 = "#2b2b29", "#6b6a64"


def estilo_eixos(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(TINTA2)
    ax.tick_params(colors=TINTA2, labelcolor=TINTA)
    ax.grid(True, color="#e4e3de", lw=0.6)
    ax.set_axisbelow(True)


def main() -> None:
    ex = pd.read_csv(RAIZ / "resultados" / "ampl" / "resultados.csv", sep=";")
    ex = ex.set_index("instancia")
    tempos = {"Exato (AMPL)": ex["tempo_ampl"].clip(lower=1e-3)}
    corridas = {}
    for spec in sys.argv[1:]:
        rot, resto = spec.split("=", 1)
        arq, cfg = resto.rsplit(":", 1)
        df = pd.read_csv(RAIZ / arq, sep=";")
        df = df[df["config"] == cfg].copy()
        df["otimo"] = df["instancia"].map(ex["caixas"])
        ok = df[df["caixas"] == df["otimo"]]
        t = ok.groupby("instancia")["tempo_melhor"].mean().clip(lower=1e-3)
        tempos[rot] = t.reindex(ex.index).fillna(np.inf)
        corridas[rot] = df["tempo_melhor"].clip(lower=1e-3)

    T = pd.DataFrame(tempos)
    R = T.div(T.min(axis=1), axis=0)
    FIG.mkdir(parents=True, exist_ok=True)

    # ---------------- performance profile ----------------
    fig, ax = plt.subplots(figsize=(6.4, 4))
    taus = np.logspace(0, np.log10(max(2, R[np.isfinite(R)].max().max()) * 1.2), 400)
    for k, m in enumerate(R.columns):
        y = [(R[m] <= t).mean() * 100 for t in taus]
        ax.step(taus, y, where="post", color=CORES[k], ls=ESTILOS[k], lw=2, label=m)
    ax.set_xscale("log")
    ax.set_ylim(0, 102)
    ax.set_xlabel("razão de desempenho τ (tempo / menor tempo)", color=TINTA)
    ax.set_ylabel("% das instâncias com razão ≤ τ", color=TINTA)
    ax.set_title("Performance profile do tempo até o ótimo (64 instâncias)",
                 color=TINTA, fontsize=11, loc="left")
    estilo_eixos(ax)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "perf_profile.png", dpi=150)
    plt.close(fig)

    # ---------------- boxplot dos tempos ----------------
    dados = [tempos["Exato (AMPL)"].values] + [v.values for v in corridas.values()]
    rotulos = ["Exato (AMPL)\nprova do ótimo"] + [f"{r}\naté a melhor sol." for r in corridas]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    bp = ax.boxplot(dados, patch_artist=True, widths=0.5, showfliers=True,
                    medianprops=dict(color=TINTA, lw=1.5),
                    flierprops=dict(marker="o", ms=3, mfc="none", mec=TINTA2))
    for k, caixa in enumerate(bp["boxes"]):
        caixa.set(facecolor=CORES[k], alpha=0.35, edgecolor=CORES[k], lw=1.5)
    ax.set_xticks(range(1, len(rotulos) + 1), rotulos)
    ax.set_yscale("log")
    ax.set_ylabel("tempo (s, escala log)", color=TINTA)
    ax.set_title("Tempos por método", color=TINTA, fontsize=11, loc="left")
    estilo_eixos(ax)
    fig.tight_layout()
    fig.savefig(FIG / "boxplot_tempos.png", dpi=150)
    plt.close(fig)
    print("figuras em", FIG)
    print((R.replace(np.inf, np.nan).describe().round(2)).to_string())


if __name__ == "__main__":
    main()
