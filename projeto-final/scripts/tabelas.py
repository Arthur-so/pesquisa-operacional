"""Gera as tabelas das Etapas 5 (exato) e 6 (exato x metaheurísticas).

Etapa 5: por instância -> W, tipo, densidade, LB, UB guloso, ótimo, tempo,
         iterações do laço, cortes, 2D-OPPs resolvidos.
Etapa 6: por instância -> ótimo e tempo do exato; para cada metaheurística:
         melhor, média de caixas, % de execuções no ótimo, tempo médio até a
         melhor solução e tempo total médio.

Saída: resultados/tabelas/etapa5.{md,csv} e etapa6.{md,csv}
Uso: python scripts/tabelas.py [--meta rotulo=arquivo.csv:config ...]
     ex.: --meta BRKGA=resultados/meta/variantes64.csv:BRKGA-ff-bl-desempate
               RKO=resultados/meta/rko64.csv:RKO-ff-bl-desempate
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from bppc.instance import load  # noqa: E402
from bppc.preprocess import lower_bound  # noqa: E402

SAIDA = RAIZ / "resultados" / "tabelas"


def etapa5() -> pd.DataFrame:
    ex = pd.read_csv(RAIZ / "resultados" / "ampl" / "resultados.csv", sep=";")
    linhas = []
    for _, r in ex.iterrows():
        inst = load(r["instancia"][4:])
        linhas.append({
            "Inst.": inst.numero, "W=H": inst.W, "Tipo": inst.tipo,
            "D(%)": round(100 * inst.densidade), "LB": lower_bound(inst),
            "UB guloso": r["ub_heur"], "Ótimo": r["caixas"],
            "Status": r["status"], "Tempo (s)": round(r["tempo_ampl"], 2),
            "Iter.": r["iter"], "Cortes": r["cortes"], "#OPP": r["opp"],
            "Tempo OPP (s)": round(r["tempo_opp"], 2)})
    return pd.DataFrame(linhas).sort_values("Inst.")


def etapa6(t5: pd.DataFrame, metas: list[str]) -> pd.DataFrame:
    tab = t5[["Inst.", "Ótimo", "Tempo (s)"]].rename(columns={"Tempo (s)": "Exato T(s)"})
    for spec in metas:
        rot, resto = spec.split("=", 1)
        arq, cfg = resto.rsplit(":", 1)
        df = pd.read_csv(RAIZ / arq, sep=";")
        df = df[df["config"] == cfg].copy()
        df["Inst."] = df["instancia"].str[4:].astype(int)
        df = df.merge(t5[["Inst.", "Ótimo"]], on="Inst.")
        g = df.groupby("Inst.").agg(
            melhor=("caixas", "min"), media=("caixas", "mean"),
            pct=("caixas", lambda c: 0), t_melhor=("tempo_melhor", "mean"),
            t_total=("tempo_total", "mean"))
        g["pct"] = df.assign(ok=df["caixas"] == df["Ótimo"]).groupby("Inst.")["ok"].mean() * 100
        g.columns = [f"{rot} melhor", f"{rot} média", f"{rot} %ót.",
                     f"{rot} T.melhor(s)", f"{rot} T.total(s)"]
        tab = tab.merge(g.reset_index(), on="Inst.", how="left")
    return tab.round(2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", nargs="*", default=[])
    a = ap.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)
    t5 = etapa5()
    t5.to_csv(SAIDA / "etapa5.csv", sep=";", index=False)
    (SAIDA / "etapa5.md").write_text(t5.to_markdown(index=False))
    print(f"Etapa 5: {(t5['Status'] == 'otimo').sum()}/64 ótimos; tempo total "
          f"{t5['Tempo (s)'].sum():.1f} s; máximo {t5['Tempo (s)'].max():.1f} s")
    if a.meta:
        t6 = etapa6(t5, a.meta)
        t6.to_csv(SAIDA / "etapa6.csv", sep=";", index=False)
        (SAIDA / "etapa6.md").write_text(t6.to_markdown(index=False))
        cols = [c for c in t6.columns if "%ót." in c]
        print("Etapa 6: % médio de execuções no ótimo:",
              {c: round(t6[c].mean(), 1) for c in cols})


if __name__ == "__main__":
    main()
