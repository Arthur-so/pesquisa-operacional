"""Gera as instâncias 53-64 que faltam no zip (2bppc/ só tem 1-52).

Regra (artigo-base, Seção 5): a instância k (49..64) é a original MAPA_60[k]
com a caixa trocada para 60x60. Conferimos a regra nas que existem:
50==18, 51==35 e 52==04 (idênticas exceto a linha "W H"). A 49 NÃO bate com
o arquivo 2kdc01, que é uma cópia da 2kdc02; reconstruímos a 01 a partir da
49 (ver docs/decisoes.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bppc.instance import DIR_GERADAS, DIR_ORIGINAIS, MAPA_60  # noqa: E402


def reconstruir_01() -> None:
    """O 2kdc01 do zip é cópia exata do 2kdc02 (sem rodapé). A 49 é a
    instância 1 com caixa 60x60, então a 01 verdadeira = 49 com caixa 30x30."""
    linhas = (DIR_ORIGINAIS / "2kdc49").read_text().split("\n")
    linhas[2] = "30 30"
    texto = "\n".join(linhas).replace("2kdc49\n", "2kdc1\n")
    (DIR_GERADAS / "2kdc01").write_text(texto)
    print("2kdc01 <- 2kdc49 com caixa 30x30 (reconstruída)")


def main() -> None:
    DIR_GERADAS.mkdir(exist_ok=True)
    reconstruir_01()
    for k, orig in MAPA_60.items():
        destino_original = DIR_ORIGINAIS / f"2kdc{k:02d}"
        if destino_original.exists():
            continue
        linhas = (DIR_ORIGINAIS / f"2kdc{orig:02d}").read_text().split("\n")
        assert linhas[2].split() == linhas[2].split()[:2]
        linhas[2] = "60 60"
        texto = "\n".join(linhas)
        texto = texto.replace(f"2kdc{orig}\n", f"2kdc{k}\n")  # nome no rodapé
        (DIR_GERADAS / f"2kdc{k:02d}").write_text(texto)
        print(f"2kdc{k:02d} <- 2kdc{orig:02d}")


if __name__ == "__main__":
    main()
