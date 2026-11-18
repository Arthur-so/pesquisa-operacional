"""Audita os cortes (5) gerados pelo AMPL com um 2D-OPP exato independente.

Lê as linhas "CORTE i j k ..." dos logs em resultados/ampl/logs/ e reconfere
com CP-SAT (bppc.opp_cpsat) que cada grupo NÃO cabe numa caixa. Se algum
grupo couber, o "ótimo" daquela instância não é confiável.

Também confere a minimalidade: tirando qualquer item, o grupo deveria caber
(é o que a redução do bppc.run tenta garantir; não afeta a validade).

Uso: python scripts/auditar_cortes.py [numeros...]
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from bppc.instance import load  # noqa: E402
from bppc.opp_cpsat import opp_cpsat  # noqa: E402


def main() -> None:
    nums = [int(a) for a in sys.argv[1:]] or list(range(1, 65))
    total_ruins = 0
    for k in nums:
        inst = load(k)
        log = RAIZ / "resultados" / "ampl" / "logs" / f"{inst.name}.log"
        if not log.exists():
            continue
        cortes = [[int(t) - 1 for t in ln.split()[1:]]
                  for ln in log.read_text().splitlines() if ln.startswith("CORTE")]
        invalidos = nao_minimos = 0
        for c in cortes:
            r, _ = opp_cpsat(inst, c)
            if r != "nao_cabe":
                invalidos += 1
                print(f"  {inst.name}: corte {[i + 1 for i in c]} -> {r} !!!")
            for i in c:
                if len(c) > 2 and opp_cpsat(inst, [j for j in c if j != i])[0] == "nao_cabe":
                    nao_minimos += 1
                    break
        total_ruins += invalidos
        print(f"{inst.name}: {len(cortes)} cortes, inválidos={invalidos}, "
              f"não mínimos={nao_minimos}")
    print("TODOS OS CORTES VÁLIDOS" if total_ruins == 0 else f"{total_ruins} CORTES INVÁLIDOS")


if __name__ == "__main__":
    main()
