"""Gera as tabelas LaTeX do documento docs/fluxo/fluxo_projeto.tex a partir dos CSVs.

Saídas (em docs/fluxo/):
  tab_tempos.tex     64 instâncias: dados, LB/UB, ótimo, tempo do exato, BRKGA e RKO
  tab_resumo.tex     resumo por método
  tab_variantes.tex  testes das variantes do decodificador

Rodar depois de atualizar os resultados: python scripts/gerar_tex_tabelas.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TAB = RAIZ / "resultados" / "tabelas"
META = RAIZ / "resultados" / "meta"
OUT = RAIZ / "docs" / "fluxo"
ESCOLHIDA = ("ff", "bl", "desempate")   # variante padrão do decodificador


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", "{,}")


def tab_tempos():
    t5 = pd.read_csv(TAB / "etapa5.csv", sep=";")
    t6 = pd.read_csv(TAB / "etapa6.csv", sep=";")
    df = t5.merge(t6, on=["Inst.", "Ótimo"])
    linhas = []
    for _, r in df.iterrows():
        marca = r"$^\ast$" if r["Ótimo"] > r["LB"] else ""
        destaque = r["Inst."] in (48, 53, 55)
        cel = [f"{r['Inst.']}{marca}", str(r["W=H"]), r["Tipo"], str(r["D(%)"]),
               str(r["LB"]), str(r["UB guloso"]), str(r["Ótimo"]),
               num(r["Exato T(s)"]), str(r["Cortes"]), str(r["#OPP"]),
               num(r["BRKGA %ót."], 0), num(r["BRKGA T.melhor(s)"], 3),
               num(r["RKO %ót."], 0), num(r["RKO T.melhor(s)"], 3)]
        if destaque:
            cel = [r"\textbf{" + c + "}" for c in cel]
        linhas.append(" & ".join(cel) + r" \\")
    tot = (r"\midrule \multicolumn{7}{l}{\textbf{Total / média}} & "
           f"\\textbf{{{num(df['Exato T(s)'].sum(), 1)}}} & {df['Cortes'].sum()} & "
           f"{df['#OPP'].sum()} & {num(df['BRKGA %ót.'].mean(), 1)} & "
           f"{num(df['BRKGA T.melhor(s)'].mean(), 3)} & {num(df['RKO %ót.'].mean(), 1)} & "
           f"{num(df['RKO T.melhor(s)'].mean(), 3)} \\\\")
    (OUT / "tab_tempos.tex").write_text("\n".join(linhas) + "\n" + tot + "\n")


def tab_resumo():
    """Resumo por método, calculado sobre as EXECUÇÕES brutas (não sobre médias por instância)."""
    ex = pd.read_csv(RAIZ / "resultados" / "ampl" / "resultados.csv", sep=";")
    otimo = ex.set_index("instancia")["caixas"]
    te = ex["tempo_ampl"]
    L = [f"Exato, AMPL (1 thread) & {len(ex)} (1/inst.) & {(ex['status'] == 'otimo').sum()}/64 (provado) & "
         f"100 & -- & {num(te.mean())} ({num(te.max())}) & {num(te.sum(), 1)} \\\\"]
    for rot, arq, cfg, thr in (("BRKGA", "variantes64.csv", "BRKGA-ff-bl-desempate", 1),
                               ("RKO", "rko64.csv", "RKO-ff-bl-desempate", 10)):
        d = pd.read_csv(META / arq, sep=";")
        d = d[d["config"] == cfg].copy()
        d["ok"] = d["caixas"] == d["instancia"].map(otimo)
        n_sem = d.groupby("instancia")["semente"].nunique().max()
        inst_ok = d.groupby("instancia")["ok"].any().sum()
        L.append(f"{rot} ({thr} thread{'s' if thr > 1 else ''}) & {len(d)} ({n_sem}/inst.) & {inst_ok}/64 & "
                 f"{num(100 * d['ok'].mean(), 1)} & {num(d['tempo_melhor'].mean(), 3)} "
                 f"({num(d['tempo_melhor'].max(), 2)}) & {num(d['tempo_total'].mean(), 2)} "
                 f"({num(d['tempo_total'].max(), 2)}) & {num(d['tempo_total'].sum(), 1)} \\\\")
    (OUT / "tab_resumo.tex").write_text("\n".join(L) + "\n")


def tab_variantes():
    ex = pd.read_csv(RAIZ / "resultados" / "ampl" / "resultados.csv", sep=";")
    otimo = ex.set_index("instancia")["caixas"]
    nomes = {"ff": "FF", "bf": "BF", "chave": "chave (2n)", "bssf": "BSSF", "bl": "BL",
             "caixas": "só caixas", "desempate": "desempate"}
    blocos = []
    for arq in ("variantes.csv", "variantes64.csv"):
        df = pd.read_csv(META / arq, sep=";")
        df["ok"] = df["caixas"] == df["instancia"].map(otimo)
        g = df.groupby("config").agg(pct=("ok", "mean"), t=("tempo_melhor", "mean"),
                                     p48=("ok", lambda s: s[df.loc[s.index, "instancia"]
                                                             == "2kdc48"].mean()))
        g = g.sort_values(["pct", "t"], ascending=[False, True])
        topo = g["pct"].max()
        L = []
        for cfg, r in g.iterrows():
            _, e, p, a = cfg.split("-")
            escolhida = (e, p, a) == ESCOLHIDA
            cel = [nomes[e], nomes[p], nomes[a], num(100 * r["pct"], 1),
                   num(100 * r["p48"], 0), num(r["t"], 3)]
            if abs(r["pct"] - topo) < 1e-9:      # empatadas no melhor % de acerto
                cel = [r"\textbf{" + c + "}" for c in cel]
            if escolhida:
                cel[0] = cel[0] + r" \checkmark"
            L.append(" & ".join(cel) + r" \\")
        blocos.append("\n".join(L))
    (OUT / "tab_variantes1.tex").write_text(blocos[0] + "\n")
    (OUT / "tab_variantes2.tex").write_text(blocos[1] + "\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tab_tempos()
    tab_resumo()
    tab_variantes()
    print("tabelas em", OUT)
