"""Compara uma execução sua do método exato com os resultados oficiais.

Para cada instância presente nos dois arquivos: ótimo (deve ser IGUAL), tempo
oficial, seu tempo e a razão entre eles. No fim, totais e quantas bateram.

Uso:
  python scripts/comparar_tempos.py resultados/minha_execucao/resultados.csv
  python scripts/comparar_tempos.py MEU.csv --oficial OUTRO.csv
"""
import argparse
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("meu")
    ap.add_argument("--oficial", default=str(RAIZ / "resultados" / "ampl" / "resultados.csv"))
    a = ap.parse_args()
    of = pd.read_csv(a.oficial, sep=";").drop_duplicates("instancia", keep="last")
    me = pd.read_csv(a.meu, sep=";").drop_duplicates("instancia", keep="last")
    df = of.merge(me, on="instancia", suffixes=("_of", "_meu"))
    df["ótimo igual"] = (df["caixas_of"] == df["caixas_meu"]) & (df["status_meu"] == "otimo")
    df["razão"] = df["tempo_ampl_meu"] / df["tempo_ampl_of"].clip(lower=1e-3)
    tab = df[["instancia", "caixas_of", "caixas_meu", "ótimo igual", "tempo_ampl_of",
              "tempo_ampl_meu", "razão", "verificada_meu"]].rename(columns={
        "caixas_of": "ótimo oficial", "caixas_meu": "seu resultado",
        "tempo_ampl_of": "tempo oficial (s)", "tempo_ampl_meu": "seu tempo (s)",
        "verificada_meu": "verificador"})
    print(tab.round(2).to_string(index=False))
    print(f"\n{len(df)} instâncias comparadas; ótimo igual em {df['ótimo igual'].sum()}; "
          f"soluções aprovadas pelo verificador: {(df['verificada_meu'] == 'sim').sum()}")
    print(f"tempo total: oficial {df['tempo_ampl_of'].sum():.1f} s | seu {df['tempo_ampl_meu'].sum():.1f} s")
    print("Obs.: tempos variam com a máquina e com o que mais estiver rodando; os ótimos não podem variar.")


if __name__ == "__main__":
    main()
