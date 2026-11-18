"""Leitura das instâncias do 2BPPC.

Formato dos arquivos de instância:
    n
    |E|
    W H
    n linhas: largura altura valor   (valor = mochila, ignorado)
    |E| linhas: i j                  (itens numerados de 1 a n)
    [nome / type / density]          (rodapé opcional: a 2kdc01 não tem)

Internamente os itens são indexados de 0 a n-1. Na saída para o usuário
(arquivos de solução, AMPL) usamos de 1 a n, como nos arquivos originais.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_ORIGINAIS = RAIZ / "2bppc"
DIR_GERADAS = RAIZ / "instancias_geradas"

# Instâncias 49-64: cópias de originais com caixa 60x60 (artigo-base, Seção 5).
MAPA_60 = {49: 1, 50: 18, 51: 35, 52: 4, 53: 21, 54: 38, 55: 7, 56: 24,
           57: 41, 58: 10, 59: 27, 60: 44, 61: 13, 62: 30, 63: 47, 64: 16}


@dataclass
class Instance:
    name: str
    n: int
    W: int
    H: int
    w: list[int]
    h: list[int]
    edges: list[tuple[int, int]]          # arestas originais, 0-based, i < j
    tipo: str | None = None
    densidade: float | None = None
    conflict: list[list[bool]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.conflict = [[False] * self.n for _ in range(self.n)]
        for i, j in self.edges:
            self.conflict[i][j] = self.conflict[j][i] = True

    @property
    def numero(self) -> int:
        return int(re.search(r"(\d+)$", self.name).group(1))

    def area(self, i: int) -> int:
        return self.w[i] * self.h[i]


def read_instance(path: str | Path) -> Instance:
    path = Path(path)
    linhas = path.read_text().split("\n")
    tokens: list[str] = []
    rodape: list[str] = []
    for ln in linhas:
        s = ln.strip()
        if not s:
            continue
        if re.fullmatch(r"[\d\s.]+", s):
            tokens.extend(s.split())
        else:
            rodape.append(s)
    it = iter(tokens)
    n, m = int(next(it)), int(next(it))
    W, H = int(next(it)), int(next(it))
    w, h = [], []
    for _ in range(n):
        w.append(int(next(it)))
        h.append(int(next(it)))
        next(it)  # valor da mochila: ignorado
    edges = set()
    for _ in range(m):
        a, b = int(next(it)) - 1, int(next(it)) - 1
        if a == b:
            continue
        edges.add((min(a, b), max(a, b)))
    tipo = dens = None
    for s in rodape:
        if s.lower().startswith("type:"):
            tipo = s.split(":", 1)[1].strip()
        elif s.lower().startswith("density:"):
            dens = float(s.split(":", 1)[1])
    # O nome vem do arquivo (o rodapé às vezes diz "2kdc4" em vez de "2kdc04").
    return Instance(path.name, n, W, H, w, h, sorted(edges), tipo, dens)


def instance_path(numero: int) -> Path:
    nome = f"2kdc{numero:02d}"
    # instancias_geradas/ tem prioridade: contém a 01 reconstruída.
    for d in (DIR_GERADAS, DIR_ORIGINAIS):
        p = d / nome
        if p.exists():
            return p
    raise FileNotFoundError(nome)


def all_instance_paths() -> list[Path]:
    return [instance_path(k) for k in range(1, 65)]


def load(numero_ou_caminho) -> Instance:
    if isinstance(numero_ou_caminho, int) or str(numero_ou_caminho).isdigit():
        return read_instance(instance_path(int(numero_ou_caminho)))
    return read_instance(numero_ou_caminho)
