"""Posicionamento geométrico heurístico: Maximal Rectangles (Jylänki, 2010).

Usado em Python só para obter um limitante superior (UB) rápido para o
método exato. O decodificador da metaheurística tem sua própria versão em
C++ (meta/), com a mesma lógica.

Origem (0,0) no canto inferior esquerdo; item ocupa [x, x+w) x [y, y+h).
"""
from __future__ import annotations


class MaxRectsBin:
    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.free: list[tuple[int, int, int, int]] = [(0, 0, W, H)]
        self.used_area = 0

    def find(self, w: int, h: int, regra: str = "bssf"):
        """Melhor posição para um item w x h. Retorna (score, x, y) ou None."""
        best = None
        for fx, fy, fw, fh in self.free:
            if fw >= w and fh >= h:
                if regra == "bssf":   # Best Short Side Fit
                    a, b = fw - w, fh - h
                    score = (min(a, b), max(a, b))
                else:                 # "bl": Bottom-Left
                    score = (fy + h, fx)
                if best is None or score < best[0]:
                    best = (score, fx, fy)
        return best

    def place(self, x: int, y: int, w: int, h: int) -> None:
        novos = []
        for r in self.free:
            fx, fy, fw, fh = r
            if x >= fx + fw or x + w <= fx or y >= fy + fh or y + h <= fy:
                novos.append(r)
                continue
            # Parte r em até 4 retângulos maximais em volta do item.
            if x > fx:
                novos.append((fx, fy, x - fx, fh))
            if x + w < fx + fw:
                novos.append((x + w, fy, fx + fw - (x + w), fh))
            if y > fy:
                novos.append((fx, fy, fw, y - fy))
            if y + h < fy + fh:
                novos.append((fx, y + h, fw, fy + fh - (y + h)))
        # Remove retângulos contidos em outros.
        podados = []
        for i, a in enumerate(novos):
            contido = False
            for j, b in enumerate(novos):
                if i != j and b[0] <= a[0] and b[1] <= a[1] and \
                        a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]:
                    if a != b or j < i:   # duplicatas: mantém só a primeira
                        contido = True
                        break
            if not contido:
                podados.append(a)
        self.free = podados
        self.used_area += w * h


def greedy_pack(inst, ordem, escolha: str = "ff", regra: str = "bssf"):
    """Decodificador guloso: itens na ordem dada; caixa sem conflito onde cabe.

    escolha = "ff" (primeira caixa que serve) ou "bf" (a mais cheia que serve).
    Retorna lista de (item, caixa, x, y) — tudo 0-based.
    """
    bins: list[MaxRectsBin] = []
    itens_da_caixa: list[list[int]] = []
    sol = []
    for i in ordem:
        cand = None
        for k, b in enumerate(bins):
            if any(inst.conflict[i][j] for j in itens_da_caixa[k]):
                continue
            if b.used_area + inst.area(i) > inst.W * inst.H:
                continue
            pos = b.find(inst.w[i], inst.h[i], regra)
            if pos is None:
                continue
            if escolha == "ff":
                cand = (k, pos)
                break
            if cand is None or b.used_area > bins[cand[0]].used_area:
                cand = (k, pos)
        if cand is None:
            bins.append(MaxRectsBin(inst.W, inst.H))
            itens_da_caixa.append([])
            k = len(bins) - 1
            pos = bins[k].find(inst.w[i], inst.h[i], regra)
            assert pos is not None, "item maior que a caixa"
        else:
            k, pos = cand
        _, x, y = pos
        bins[k].place(x, y, inst.w[i], inst.h[i])
        itens_da_caixa[k].append(i)
        sol.append((i, k, x, y))
    return sol


def pack_single_bin(inst, itens, tentativas: int = 50, seed: int = 0):
    """Tenta (heuristicamente) arrumar `itens` numa única caixa.

    Retorna lista de (item, x, y) se conseguir, ou None (o que NÃO prova que
    é impossível). Útil só como atalho para respostas positivas.
    """
    import random
    rng = random.Random(seed)
    ordens = [sorted(itens, key=lambda i: -inst.area(i)),
              sorted(itens, key=lambda i: (-inst.h[i], -inst.w[i])),
              sorted(itens, key=lambda i: (-inst.w[i], -inst.h[i])),
              sorted(itens, key=lambda i: -max(inst.w[i], inst.h[i]))]
    for t in range(tentativas):
        ordem = ordens[t] if t < len(ordens) else rng.sample(list(itens), len(itens))
        for regra in ("bssf", "bl"):
            b = MaxRectsBin(inst.W, inst.H)
            res = []
            for i in ordem:
                pos = b.find(inst.w[i], inst.h[i], regra)
                if pos is None:
                    break
                b.place(pos[1], pos[2], inst.w[i], inst.h[i])
                res.append((i, pos[1], pos[2]))
            else:
                return res
    return None
