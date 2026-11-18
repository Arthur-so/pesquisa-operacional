"""Executa a metaheurística (rko_bppc) em lote: configurações x instâncias x sementes.

Cada execução: chama meta/rko_bppc, lê a linha "RESULTADO ...", confere a
solução com o verificador independente (bppc.solution.verify) e grava uma
linha no CSV. Execuções independentes rodam em paralelo (--paralelo).

Configurações pré-definidas (CONFIGS): variantes do decodificador com o
BRKGA (teste rápido) e o RKO completo.

Atenção: o limite é de TEMPO DE RELÓGIO. Muitas execuções simultâneas (ou em
núcleos lentos) andam mais devagar e são cortadas antes. Para comparações
justas use --cpus com um núcleo rápido por execução.

Uso:
  python meta/experimentos.py --exp variantes --tempo 2 --sementes 5 \
         --configs todas_variantes --inst 3 9 17 ...
"""
from __future__ import annotations

import argparse
import csv
import queue
import itertools
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
META = RAIZ / "meta"
sys.path.insert(0, str(RAIZ / "src"))
from bppc.instance import instance_path, load  # noqa: E402
from bppc.solution import read_solution, verify  # noqa: E402

# nome -> (arquivo de configuração do RKO, escolha, posicionamento, avaliação)
CONFIGS = {f"BRKGA-{e}-{p}-{a}": ("config/brkga.conf", e, p, a)
           for e, p, a in itertools.product(["ff", "bf", "chave"], ["bssf", "bl"],
                                            ["caixas", "desempate"])}
CONFIGS.update({f"RKO-{e}-{p}-{a}": ("config/rko.conf", e, p, a)
                for e, p, a in itertools.product(["ff", "bf", "chave"], ["bssf", "bl"],
                                                 ["caixas", "desempate"])})
# Decodificador "caixa" (relatório da 2ª conversa): ordem + caixa (+ posição) por item,
# K0 = LB caixas abertas, plano B e reescrita lamarckiana. Quinto campo = opções extras.
CONFIGS.update({
    "BRKGA-caixa-chave-bf-lam":      ("config/brkga.conf", "caixa", "chave", "desempate",
                                      ["--planob", "bf", "--lamarck", "1"]),
    "BRKGA-caixa-chave-bf-semlam":   ("config/brkga.conf", "caixa", "chave", "desempate",
                                      ["--planob", "bf", "--lamarck", "0"]),
    "BRKGA-caixa-chave-seguinte-lam": ("config/brkga.conf", "caixa", "chave", "desempate",
                                       ["--planob", "seguinte", "--lamarck", "1"]),
    "BRKGA-caixa-chave-nova":        ("config/brkga.conf", "caixa", "chave", "desempate",
                                      ["--planob", "nova", "--lamarck", "1"]),
    "BRKGA-caixa-bl-bf-lam":         ("config/brkga.conf", "caixa", "bl", "desempate",
                                      ["--planob", "bf", "--lamarck", "1"]),
})
GRUPOS = {"todas_variantes": [c for c in CONFIGS if c.startswith("BRKGA-") and "-caixa-" not in c],
          "caixa": [c for c in CONFIGS if c.startswith("BRKGA-caixa-")]}

CAMPOS = ["config", "instancia", "semente", "caixas", "ofv", "LB", "tempo_melhor",
          "tempo_total", "alvo", "valida", "pb_outra", "pb_nova"]


CPUS_LIVRES: "queue.Queue[str] | None" = None   # núcleos para fixar as execuções (--cpus)


def executar(config: str, numero: int, semente: int, tempo: int) -> dict:
    conf, esc, pos, ava, *extra = CONFIGS[config]
    extra = extra[0] if extra else []
    inst = load(numero)
    with tempfile.NamedTemporaryFile(suffix=".sol", delete=False) as tmp:
        arq = tmp.name
    cmd = [str(META / "rko_bppc"), str(instance_path(numero)), "--tempo", str(tempo),
           "--semente", str(semente), "--conf", conf, "--escolha", esc,
           "--posic", pos, "--aval", ava, "--sol", arq] + extra
    cpu = CPUS_LIVRES.get() if CPUS_LIVRES else None
    try:
        if cpu is not None:   # fixa a execução num núcleo, sem disputa com as outras
            cmd = ["taskset", "-c", cpu] + cmd
        out = subprocess.run(cmd, cwd=META, capture_output=True, text=True,
                             timeout=tempo * 3 + 30).stdout
    finally:
        if cpu is not None:
            CPUS_LIVRES.put(cpu)
    linha = next(ln for ln in out.splitlines() if ln.startswith("RESULTADO"))
    kv = dict(t.split("=", 1) for t in linha.split()[2:] if "=" in t)
    ok, nb, _ = verify(inst, read_solution(arq))
    os.unlink(arq)
    return {"config": config, "instancia": inst.name, "semente": semente,
            "caixas": int(kv["caixas"]), "ofv": kv["ofv"], "LB": kv["LB"],
            "tempo_melhor": kv["tempo_melhor"], "tempo_total": kv["tempo_total"],
            "alvo": kv["alvo"], "valida": int(ok and nb == int(kv["caixas"])),
            "pb_outra": kv.get("pb_outra", ""), "pb_nova": kv.get("pb_nova", "")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True, help="nome do experimento (arquivo CSV)")
    ap.add_argument("--configs", nargs="+", required=True)
    ap.add_argument("--inst", nargs="*", type=int, default=[])
    ap.add_argument("--tempo", type=int, default=2)
    ap.add_argument("--sementes", type=int, default=5)
    ap.add_argument("--paralelo", type=int, default=10)
    ap.add_argument("--cpus", default="",
                    help="ex.: 0,2,4 -> uma execução por núcleo listado (substitui --paralelo). "
                         "Neste i5-13420H, CPUs 0-7 são 4 núcleos rápidos (2 threads cada) e 8-11 lentos.")
    a = ap.parse_args()
    global CPUS_LIVRES
    if a.cpus:
        CPUS_LIVRES = queue.Queue()
        for c in a.cpus.split(","):
            CPUS_LIVRES.put(c.strip())
        a.paralelo = CPUS_LIVRES.qsize()
    configs = [c for g in a.configs for c in GRUPOS.get(g, [g])]
    insts = a.inst or list(range(1, 65))
    tarefas = [(c, k, s) for c in configs for k in insts for s in range(1, a.sementes + 1)]
    saida = RAIZ / "resultados" / "meta" / f"{a.exp}.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    feitas = set()
    if saida.exists():  # permite retomar um experimento interrompido
        with open(saida) as f:
            feitas = {(r["config"], r["instancia"], int(r["semente"]))
                      for r in csv.DictReader(f, delimiter=";")}
    tarefas = [t for t in tarefas if (t[0], f"2kdc{t[1]:02d}", t[2]) not in feitas]
    print(f"{len(tarefas)} execuções de até {a.tempo}s, {a.paralelo} em paralelo", flush=True)
    novo = not saida.exists()
    with open(saida, "a", newline="") as f, ThreadPoolExecutor(a.paralelo) as ex:
        campos = CAMPOS
        if not novo:   # CSV antigo pode não ter as colunas novas: mantém o cabeçalho dele
            with open(saida) as g:
                campos = g.readline().strip().split(";")
        wr = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        if novo:
            wr.writeheader()
        futuros = [ex.submit(executar, c, k, s, a.tempo) for c, k, s in tarefas]
        for i, fu in enumerate(as_completed(futuros), 1):
            wr.writerow(fu.result())
            f.flush()
            if i % 100 == 0:
                print(f"  {i}/{len(tarefas)}", flush=True)


if __name__ == "__main__":
    main()
