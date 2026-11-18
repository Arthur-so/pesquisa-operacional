"""2D-OPP exato por Programação por Restrições (OR-Tools CP-SAT).

Formulação diferente do PLI disjuntivo do AMPL: cada item vira um par de
intervalos (x e y) e a restrição global NoOverlap2D impede sobreposição.
Usado para AUDITAR os cortes do método exato (reconferir, com outro método
exato, que cada grupo proibido realmente não cabe numa caixa).
"""
from __future__ import annotations

from ortools.sat.python import cp_model


def opp_cpsat(inst, itens, tempo: float = 60.0, threads: int = 1):
    """Retorna ("cabe", [(i,x,y)...]) | ("nao_cabe", None) | ("desconhecido", None)."""
    m = cp_model.CpModel()
    xs, ys, ix, iy = {}, {}, [], []
    for i in itens:
        x = m.NewIntVar(0, inst.W - inst.w[i], f"x{i}")
        y = m.NewIntVar(0, inst.H - inst.h[i], f"y{i}")
        xs[i], ys[i] = x, y
        ix.append(m.NewFixedSizeIntervalVar(x, inst.w[i], f"ix{i}"))
        iy.append(m.NewFixedSizeIntervalVar(y, inst.h[i], f"iy{i}"))
    m.AddNoOverlap2D(ix, iy)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tempo
    s.parameters.num_search_workers = threads
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "cabe", [(i, s.Value(xs[i]), s.Value(ys[i])) for i in itens]
    if st == cp_model.INFEASIBLE:
        return "nao_cabe", None
    return "desconhecido", None
