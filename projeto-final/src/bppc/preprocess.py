"""Pré-processamento comum: arestas por dimensão (12), cliques (13), LB (14), UB.

- Regra (12) / "D" no artigo-base: se w_i + w_j > W e h_i + h_j > H, os dois
  itens não cabem juntos de jeito nenhum -> nova aresta de conflito.
- Cliques: no grafo estendido (original + D), uma clique C exige |C| caixas
  distintas. Usamos as cliques maximais com |C| >= 3 (as de tamanho 2 já são
  arestas comuns).
- LB = max(ceil(área total / WH), maior clique).
- UB = melhor solução de várias execuções do guloso (geometry.greedy_pack).
"""
from __future__ import annotations

import math
import random

import networkx as nx

from .geometry import greedy_pack


def dimension_edges(inst) -> list[tuple[int, int]]:
    extra = []
    for i in range(inst.n):
        for j in range(i + 1, inst.n):
            if inst.conflict[i][j]:
                continue
            if inst.w[i] + inst.w[j] > inst.W and inst.h[i] + inst.h[j] > inst.H:
                extra.append((i, j))
    return extra


def conflict_graph(inst, com_dimensao: bool = True) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(inst.n))
    G.add_edges_from(inst.edges)
    if com_dimensao:
        G.add_edges_from(dimension_edges(inst))
    return G


def maximal_cliques(inst, tamanho_min: int = 3) -> list[list[int]]:
    G = conflict_graph(inst)
    return sorted((sorted(c) for c in nx.find_cliques(G) if len(c) >= tamanho_min),
                  key=lambda c: (-len(c), c))


def max_clique_size(inst) -> int:
    G = conflict_graph(inst)
    return max(len(c) for c in nx.find_cliques(G))


def lb_area(inst) -> int:
    return math.ceil(sum(inst.area(i) for i in range(inst.n)) / (inst.W * inst.H))


def lower_bound(inst) -> int:
    return max(lb_area(inst), max_clique_size(inst))


def upper_bound(inst, tentativas_aleatorias: int = 200, seed: int = 0):
    """Melhor de várias ordens x {FF, BF} x {BSSF, BL}. Retorna (UB, solução)."""
    rng = random.Random(seed)
    G = conflict_graph(inst)
    n = inst.n
    ordens = [
        sorted(range(n), key=lambda i: -inst.area(i)),
        sorted(range(n), key=lambda i: (-G.degree(i), -inst.area(i))),
        sorted(range(n), key=lambda i: (-inst.h[i], -inst.w[i])),
        sorted(range(n), key=lambda i: (-inst.w[i], -inst.h[i])),
    ]
    ordens += [rng.sample(range(n), n) for _ in range(tentativas_aleatorias)]
    melhor = None
    for ordem in ordens:
        for escolha in ("ff", "bf"):
            for regra in ("bssf", "bl"):
                sol = greedy_pack(inst, ordem, escolha, regra)
                nb = 1 + max(k for _, k, _, _ in sol)
                if melhor is None or nb < melhor[0]:
                    melhor = (nb, sol)
    return melhor


def item_order(inst, criterio: str = "conflito") -> list[int]:
    """Ordem de renumeração dos itens para as restrições (8) e (10).

    "conflito" (Oc no artigo-base): grau decrescente no grafo estendido,
    desempate por área decrescente. "area" (Oa): área decrescente.
    "original": mantém a numeração do arquivo.
    """
    if criterio == "original":
        return list(range(inst.n))
    G = conflict_graph(inst)
    if criterio == "conflito":
        return sorted(range(inst.n), key=lambda i: (-G.degree(i), -inst.area(i), i))
    return sorted(range(inst.n), key=lambda i: (-inst.area(i), i))
