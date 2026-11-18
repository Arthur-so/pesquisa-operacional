"""Executa o método exato em AMPL (bppc.mod + bppc.run) em lote.

Para cada instância:
  1. gera o .dat (gerar_dat.py), que também grava a solução gulosa (UB);
  2. chama o AMPL com tempo limite; guarda o log em resultados/ampl/logs;
  3. lê a linha de resultado gravada pelo bppc.run;
  4. confere a solução do AMPL com o verificador independente (solution.py);
     se não houver solução ótima (tempo), a melhor solução é a gulosa.
Saída: resultados/ampl/resultados.csv (uma linha por instância).

Uso: python ampl/rodar_ampl.py [--tlim 3600] [--pasta resultados/minha_execucao] [numeros...]
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_AMPL = RAIZ / "ampl"
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(DIR_AMPL))

from gerar_dat import DIR_UB, gerar  # noqa: E402
from bppc.instance import load  # noqa: E402
from bppc.solution import read_solution, verify  # noqa: E402

DIR_RES = RAIZ / "resultados" / "ampl"
CAMPOS = ["instancia", "status", "caixas", "lb", "ub_heur", "tempo_ampl",
          "iter", "cortes", "opp", "tempo_opp"]


def ambiente_ampl() -> tuple[str, dict]:
    """Acha o binário do AMPL e põe os solvers instalados pelo amplpy no PATH."""
    import amplpy.modules as m
    ampl = m.find("ampl")
    sp = Path(ampl).parents[2]
    bins = [str(p) for p in sp.glob("ampl_module_*/bin")]
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(bins + [env.get("PATH", "")])
    return ampl, env


def rodar(numero: int, tlim: float, ampl: str, env: dict) -> dict:
    inst = load(numero)
    dat = gerar(numero)
    (DIR_RES / "logs").mkdir(parents=True, exist_ok=True)
    (DIR_RES / "solucoes").mkdir(parents=True, exist_ok=True)
    arq_sol = DIR_RES / "solucoes" / f"{inst.name}.sol"
    arq_lin = DIR_RES / "logs" / f"{inst.name}.linha"
    for p in (arq_sol, arq_lin):
        p.unlink(missing_ok=True)
    script = (f"model '{DIR_AMPL / 'bppc.mod'}';\n"
              f"data '{dat}';\n"
              f"let tlim := {tlim};\n"
              f"let arq_sol := '{arq_sol}';\n"
              f"let arq_csv := '{arq_lin}';\n"
              f"let dir_ampl := '{DIR_AMPL}';\n"
              f"include '{DIR_AMPL / 'bppc.run'}';\n")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run([ampl], input=script, text=True, capture_output=True,
                              env=env, timeout=tlim + 120)
        saida = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        saida = (e.stdout or "") + "\n[TIMEOUT externo]"
        if isinstance(saida, bytes):
            saida = saida.decode()
    parede = time.perf_counter() - t0
    (DIR_RES / "logs" / f"{inst.name}.log").write_text(saida)

    ub_sol = read_solution(DIR_UB / f"{inst.name}.sol")
    ub = verify(inst, ub_sol)[1]
    linha = dict.fromkeys(CAMPOS, "")
    linha.update(instancia=inst.name, ub_heur=ub)
    if arq_lin.exists() and arq_lin.read_text().strip():
        valores = arq_lin.read_text().strip().splitlines()[-1].split(";")
        linha.update(zip(CAMPOS, valores))
    elif "demo license" in saida.lower() or "limited to 500" in saida.lower() \
            or "too many" in saida.lower():
        linha.update(status="limite_licenca_demo", caixas=ub, lb="")
    else:
        linha.update(status="erro", caixas=ub)
    linha["tempo_parede"] = f"{parede:.2f}"

    # Verificação independente da solução produzida pelo AMPL.
    if linha["status"] == "otimo":
        ok, nb, erros = verify(inst, read_solution(arq_sol))
        linha["verificada"] = "sim" if ok and nb == int(linha["caixas"]) else \
            f"NAO: {erros[:3]} nb={nb}"
    else:
        linha["verificada"] = "solucao gulosa"
    return linha


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tlim", type=float, default=3600)
    ap.add_argument("--pasta", default="",
                    help="pasta de saída (CSV, logs, soluções); padrão: resultados/ampl "
                         "(os resultados oficiais). Use outra para não sobrescrevê-los.")
    ap.add_argument("--saida", default="", help="CSV de saída (padrão: <pasta>/resultados.csv)")
    ap.add_argument("numeros", nargs="*", type=int)
    a = ap.parse_args()
    global DIR_RES
    if a.pasta:
        DIR_RES = Path(a.pasta).resolve()
    if not a.saida:
        a.saida = str(DIR_RES / "resultados.csv")
    nums = a.numeros or list(range(1, 65))
    ampl, env = ambiente_ampl()
    DIR_RES.mkdir(parents=True, exist_ok=True)
    novo = not Path(a.saida).exists()
    with open(a.saida, "a", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=CAMPOS + ["tempo_parede", "verificada"],
                           delimiter=";")
        if novo:
            wr.writeheader()
        for k in nums:
            r = rodar(k, a.tlim, ampl, env)
            wr.writerow(r)
            f.flush()
            print(";".join(str(r[c]) for c in ["instancia", "status", "caixas", "lb",
                                                "ub_heur", "tempo_parede", "cortes",
                                                "opp", "verificada"]), flush=True)


if __name__ == "__main__":
    main()
