"""Formato comum de solução + verificador independente.

Arquivo de solução (texto, usado por AMPL, Python e C++):
    # comentários livres
    item caixa x y          <- uma linha por item, item e caixa de 1 a n

O verificador NÃO confia em nada do método que gerou a solução: relê a
instância e confere tudo do zero.
"""
from __future__ import annotations

from pathlib import Path


def write_solution(path, sol, cabecalho: str = "") -> None:
    """sol: lista de (item, caixa, x, y), 0-based."""
    linhas = [f"# {l}" for l in cabecalho.splitlines()] if cabecalho else []
    linhas += [f"{i + 1} {k + 1} {x} {y}" for i, k, x, y in sorted(sol)]
    Path(path).write_text("\n".join(linhas) + "\n")


def read_solution(path):
    sol = []
    for ln in Path(path).read_text().splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        i, k, x, y = (int(round(float(t))) for t in s.split()[:4])
        sol.append((i - 1, k - 1, x, y))
    return sol


def verify(inst, sol) -> tuple[bool, int, list[str]]:
    """Confere uma solução. Retorna (ok, nº de caixas, lista de erros).

    Checa: todo item alocado exatamente uma vez; item dentro da caixa;
    sem sobreposição entre itens da mesma caixa; sem par em conflito
    (arestas ORIGINAIS da instância) na mesma caixa.
    """
    erros = []
    vistos = {}
    for i, k, x, y in sol:
        if not 0 <= i < inst.n:
            erros.append(f"item inexistente {i + 1}")
            continue
        if i in vistos:
            erros.append(f"item {i + 1} alocado mais de uma vez")
        vistos[i] = (k, x, y)
    faltando = [i + 1 for i in range(inst.n) if i not in vistos]
    if faltando:
        erros.append(f"itens não alocados: {faltando}")
    por_caixa: dict[int, list[int]] = {}
    for i, (k, x, y) in vistos.items():
        por_caixa.setdefault(k, []).append(i)
        if x < 0 or y < 0 or x + inst.w[i] > inst.W or y + inst.h[i] > inst.H:
            erros.append(f"item {i + 1} fora da caixa {k + 1}: ({x},{y})")
    for k, itens in por_caixa.items():
        for a in range(len(itens)):
            i = itens[a]
            _, xi, yi = vistos[i]
            for b in range(a + 1, len(itens)):
                j = itens[b]
                _, xj, yj = vistos[j]
                if inst.conflict[i][j]:
                    erros.append(f"conflito {i + 1}-{j + 1} na caixa {k + 1}")
                sobrepoe = (xi < xj + inst.w[j] and xj < xi + inst.w[i] and
                            yi < yj + inst.h[j] and yj < yi + inst.h[i])
                if sobrepoe:
                    erros.append(f"sobreposição {i + 1}-{j + 1} na caixa {k + 1}")
    return (not erros, len(por_caixa), erros)
