"""Gera o arquivo .dat do AMPL para uma instância (com pré-processamento).

O que vai no .dat:
  - itens RENUMERADOS pela ordem "conflito" (grau decrescente no grafo
    estendido; empate: área decrescente). orig[i] guarda o número original.
    Motivo: as restrições (8) e (10) fixam os primeiros itens nas primeiras
    caixas; colocar ali os itens mais "difíceis" fortalece o modelo (Oc no
    artigo-base, a melhor configuração deles).
  - E  = arestas originais; ED = arestas por dimensão, regra (12).
  - CLQ = cliques maximais (>= 3 itens) do grafo estendido, restrição (13).
  - LB  = max(ceil(área/WH), maior clique), restrição (14).
  - K   = UB do guloso (nº de caixas disponíveis no modelo).
  - ordem_rem = itens por área crescente (ordem de remoção na redução de
    grupos inviáveis: tenta tirar primeiro os pequenos).

Uso: python ampl/gerar_dat.py [numeros...]   (sem argumentos: todas as 64)
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from bppc.instance import load  # noqa: E402
from bppc.preprocess import (dimension_edges, item_order, lower_bound,  # noqa: E402
                             maximal_cliques, upper_bound)
from bppc.solution import write_solution  # noqa: E402

DIR_DAT = RAIZ / "ampl" / "dat"
DIR_UB = RAIZ / "resultados" / "ub_heuristico"


def gerar(numero: int, criterio: str = "conflito") -> Path:
    inst = load(numero)
    ordem = item_order(inst, criterio)          # ordem[novo] = original
    novo = {orig: k + 1 for k, orig in enumerate(ordem)}  # original -> novo (1-based)
    lb = lower_bound(inst)
    ub, sol_ub = upper_bound(inst)
    E = sorted(tuple(sorted((novo[i], novo[j]))) for i, j in inst.edges)
    ED = sorted(tuple(sorted((novo[i], novo[j]))) for i, j in dimension_edges(inst))
    cliques = [sorted(novo[i] for i in c) for c in maximal_cliques(inst)]
    rem = sorted(range(1, inst.n + 1),
                 key=lambda k: (inst.area(ordem[k - 1]), k))

    L = [f"# {inst.name}  tipo={inst.tipo}  dens={inst.densidade}",
         f"param n := {inst.n};", f"param W := {inst.W};", f"param H := {inst.H};",
         f"param K := {ub};", f"param LB := {lb};", f"param UB := {ub};",
         f"param nfix := {inst.n // 2};",
         f"param nome := '{inst.name}';", "",
         "param:  w  h  orig :="]
    for k, o in enumerate(ordem, start=1):
        L.append(f"  {k:3d} {inst.w[o]:3d} {inst.h[o]:3d} {o + 1:3d}")
    L.append(";")
    L.append("set E := " + " ".join(f"({i},{j})" for i, j in E) + ";")
    L.append("set ED := " + " ".join(f"({i},{j})" for i, j in ED) + ";")
    L.append(f"param nclq := {len(cliques)};")
    for c, itens in enumerate(cliques, start=1):
        L.append(f"set CLQ[{c}] := {' '.join(map(str, itens))};")
    L.append("param ordem_rem := " +
             " ".join(f"{r} {k}" for r, k in enumerate(rem, start=1)) + ";")
    DIR_DAT.mkdir(parents=True, exist_ok=True)
    caminho = DIR_DAT / f"{inst.name}.dat"
    caminho.write_text("\n".join(L) + "\n")

    DIR_UB.mkdir(parents=True, exist_ok=True)
    write_solution(DIR_UB / f"{inst.name}.sol", sol_ub,
                   f"{inst.name} UB guloso = {ub} caixas")
    return caminho


if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:]] or list(range(1, 65))
    for k in nums:
        print(gerar(k))
