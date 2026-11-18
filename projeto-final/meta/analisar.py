"""Resume um experimento da metaheurística contra os ótimos do método exato.

Para cada configuração: % de execuções que atingiram o ótimo, desvio médio
(caixas - ótimo), tempo médio até a melhor solução, nº de soluções inválidas.
Com --por-instancia, mostra também a tabela instância x configuração.

Uso: python meta/analisar.py resultados/meta/variantes.csv [--por-instancia]
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def carregar(arq):
    df = pd.read_csv(arq, sep=";")
    ex = pd.read_csv(RAIZ / "resultados" / "ampl" / "resultados.csv", sep=";")
    otimo = ex.set_index("instancia")["caixas"]
    df["otimo"] = df["instancia"].map(otimo)
    df["desvio"] = df["caixas"] - df["otimo"]
    df["acertou"] = (df["desvio"] == 0).astype(int)
    return df


def main() -> None:
    df = carregar(sys.argv[1])
    res = df.groupby("config").agg(
        execucoes=("acertou", "size"), pct_otimo=("acertou", "mean"),
        desvio_medio=("desvio", "mean"), desvio_max=("desvio", "max"),
        t_melhor_medio=("tempo_melhor", "mean"), invalidas=("valida", lambda v: (v == 0).sum()))
    res["pct_otimo"] = (100 * res["pct_otimo"]).round(1)
    print(res.sort_values(["pct_otimo", "t_melhor_medio"], ascending=[False, True])
          .round(3).to_string())
    if "--por-instancia" in sys.argv:
        tab = df.pivot_table(index="instancia", columns="config", values="acertou", aggfunc="mean")
        print("\nFração de execuções que acharam o ótimo, por instância:")
        print((100 * tab).round(0).to_string())


if __name__ == "__main__":
    main()
