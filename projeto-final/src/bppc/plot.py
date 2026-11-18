"""Desenho das caixas de uma solução (gráfico qualitativo e depuração).

Uso:  python -m bppc.plot <instancia> <arquivo_solucao> [saida.png]
"""
from __future__ import annotations

import math
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def plot_solution(inst, sol, saida, titulo: str | None = None) -> None:
    caixas = sorted({k for _, k, _, _ in sol})
    nb = len(caixas)
    cols = min(nb, 5)
    rows = math.ceil(nb / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(2.6 * cols, 2.8 * rows + 0.4),
                             squeeze=False)
    cmap = plt.get_cmap("tab20")
    for a, k in enumerate(caixas):
        ax = axes[a // cols][a % cols]
        ax.add_patch(Rectangle((0, 0), inst.W, inst.H, fill=False, lw=1.5))
        for i, kk, x, y in sol:
            if kk != k:
                continue
            ax.add_patch(Rectangle((x, y), inst.w[i], inst.h[i],
                                   facecolor=cmap(i % 20), edgecolor="black", lw=0.6))
            fs = 7 if min(inst.w[i], inst.h[i]) >= inst.W / 12 else 5
            ax.text(x + inst.w[i] / 2, y + inst.h[i] / 2, str(i + 1),
                    ha="center", va="center", fontsize=fs)
        usada = sum(inst.area(i) for i, kk, _, _ in sol if kk == k)
        ax.set_title(f"caixa {a + 1} ({100 * usada / (inst.W * inst.H):.0f}%)", fontsize=8)
        ax.set_xlim(0, inst.W)
        ax.set_ylim(0, inst.H)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
    for a in range(nb, rows * cols):
        axes[a // cols][a % cols].axis("off")
    fig.suptitle(titulo or f"{inst.name}: {nb} caixas ({inst.W}x{inst.H})", fontsize=10)
    fig.tight_layout()
    fig.savefig(saida, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    from .instance import load
    from .solution import read_solution, verify

    inst = load(sys.argv[1])
    sol = read_solution(sys.argv[2])
    ok, nb, erros = verify(inst, sol)
    print("válida" if ok else f"INVÁLIDA: {erros[:5]}", f"- {nb} caixas")
    plot_solution(inst, sol, sys.argv[3] if len(sys.argv) > 3 else "solucao.png")
