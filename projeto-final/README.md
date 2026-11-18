# 2BPPC: empacotamento bidimensional em contêineres com conflitos

Método exato (AMPL, laço de cortes) + metaheurística (RKO/BRKGA com decodificador próprio).
As decisões estão em `docs/decisoes.md`; as perguntas para o professor, em `docs/duvidas_professor.md`.

## Estrutura

```
2bppc/                  instâncias do zip (52 arquivos; não modificados)
instancias_geradas/     01 reconstruída + 53–64 geradas (scripts/gerar_instancias_60.py)
src/bppc/               base comum em Python
  instance.py             leitura das instâncias
  preprocess.py           arestas por dimensão (12), cliques (13), LB (14), UB guloso
  geometry.py             Maximal Rectangles (BSSF / Bottom-Left) e guloso
  solution.py             formato de solução + VERIFICADOR INDEPENDENTE
  opp_cpsat.py            2D-OPP exato em CP-SAT (só para auditoria)
  plot.py                 desenho das caixas
ampl/                   MÉTODO EXATO
  bppc.mod                mestre (1)–(14) + 2D-OPP disjuntivo
  bppc.run                laço de cortes (cache, redução de grupos, tempo limite)
  testa_grupo.run         teste "o grupo P cabe numa caixa?" (chamado pelo laço)
  gerar_dat.py            .dat pré-processado de cada instância
  rodar_ampl.py           execução em lote + verificação das soluções
meta/                   METAHEURÍSTICA
  RKO_Cpp_v2.0/           RKO oficial (código genérico, sem modificação)
  src/Problem_2BPPC.h     decodificador e leitura (interface do RKO)
  src/rko_bppc.cpp        main adaptado (sementes, parada no LB, argumentos)
  config/                 brkga.conf, rko.conf, parâmetros do RKO
  experimentos.py         execuções em lote (configs × instâncias × sementes)
  analisar.py             resumo contra os ótimos do exato
scripts/                auditoria dos cortes, tabelas, gráficos, comparar_tempos.py
resultados/             CSVs, logs, soluções, figuras e tabelas
```

## Como rodar e conferir os tempos (passo a passo)

Todos os comandos são rodados **da pasta do projeto** (`projeto-final/`). Os tempos dependem da máquina; os
ótimos não podem mudar.

### 0. Preparar o ambiente (só na primeira vez)

```bash
cd ~/repo/pesquisa-operacional/projeto-final
python3 -m venv .venv
.venv/bin/pip install amplpy highspy numpy matplotlib pandas networkx ortools tabulate
.venv/bin/python -m amplpy.modules install highs cbc     # AMPL + solver HiGHS (licença demo basta)
.venv/bin/python scripts/gerar_instancias_60.py          # cria instancias_geradas/ (01 e 53–64)
cd meta && make && cd ..                                  # compila a metaheurística (C++)
```

### 1. Método exato (AMPL): uma instância

```bash
.venv/bin/python ampl/rodar_ampl.py --tlim 3600 --pasta resultados/minha_execucao 53
```

Saída esperada (uma linha por instância):

```
2kdc53;otimo;4;4;4;41.55;69;676;sim
  │      │   │ │ │   │    │   │   └─ verificador independente aprovou a solução
  │      │   │ │ │   │    │   └──── 2D-OPPs resolvidos pelo solver
  │      │   │ │ │   │    └──────── cortes gerados
  │      │   │ │ │   └───────────── tempo de parede (s)
  │      │   │ │ └───────────────── UB do guloso
  │      │   │ └─────────────────── LB final
  │      │   └───────────────────── nº de caixas da solução
  │      └───────────────────────── status (otimo = provado)
  └──────────────────────────────── instância
```

`--pasta` manda tudo (CSV, logs, soluções) para uma pasta sua. **Sem `--pasta`, ele grava em
`resultados/ampl/`, por cima dos resultados oficiais.**

### 2. Método exato: as 64 instâncias (≈ 3 min nesta máquina)

```bash
.venv/bin/python ampl/rodar_ampl.py --tlim 3600 --pasta resultados/minha_execucao
```

### 3. Conferir seus tempos contra os oficiais

```bash
.venv/bin/python scripts/comparar_tempos.py resultados/minha_execucao/resultados.csv
```

Mostra, por instância, o ótimo oficial × o seu (têm que ser iguais), o tempo oficial × o seu, e os totais.
Os resultados oficiais estão em `resultados/ampl/resultados.csv` (tempo total: 150 s).

### 4. Metaheurística: uma execução

```bash
cd meta
./rko_bppc ../2bppc/2kdc48 --tempo 5 --semente 1 --conf config/brkga.conf \
           --escolha ff --posic bl --aval desempate --sol saida48.sol
cd ..
PYTHONPATH=src .venv/bin/python -m bppc.plot 48 meta/saida48.sol caixas48.png   # confere e desenha
```

Saída esperada:

```
RESULTADO ../2bppc/2kdc48 semente=1 caixas=4 ofv=4.751600 LB=4 tempo_melhor=0.459 tempo_total=0.459 alvo=1 ...
```

- `caixas`: nº de caixas da melhor solução; `tempo_melhor`: quando ela foi achada; `tempo_total`: duração da execução;
- `alvo=1`: atingiu o LB (ótimo provado) e parou antes do tempo; `alvo=0`: rodou até o limite;
- `--conf config/brkga.conf` = só o BRKGA; `--conf config/rko.conf` = RKO completo (10 metaheurísticas);
- `--escolha ff|bf|chave`, `--posic bl|bssf`, `--aval desempate|caixas`: variantes do decodificador;
- a mesma semente refaz a mesma busca.

### 5. Metaheurística: várias execuções (≈ 2 min para o BRKGA, ≈ 3 min para o RKO)

```bash
# BRKGA: 64 instâncias × 5 sementes × 1 s, 3 execuções por vez, cada uma num núcleo rápido
.venv/bin/python meta/experimentos.py --exp meu_brkga --configs BRKGA-ff-bl-desempate \
       --tempo 1 --sementes 5 --cpus 0,2,4
# RKO completo: uma execução por vez (ele já usa 10 threads)
.venv/bin/python meta/experimentos.py --exp meu_rko --configs RKO-ff-bl-desempate \
       --tempo 1 --sementes 5 --paralelo 1

.venv/bin/python meta/analisar.py resultados/meta/meu_brkga.csv --por-instancia
```

`analisar.py` mostra a % de execuções que acharam o ótimo do exato, o tempo médio até a melhor solução e quantas
soluções foram inválidas (deve ser 0). Para comparar com os resultados oficiais:

```bash
.venv/bin/python meta/analisar.py resultados/meta/variantes64.csv   # BRKGA oficial (100 %, 0,052 s)
.venv/bin/python meta/analisar.py resultados/meta/rko64.csv         # RKO oficial (99,7 %, 0,030 s)
```

**Cuidado com execuções simultâneas:** o limite é de tempo de relógio. Use `--cpus 0,2,4` (um núcleo rápido
por execução) em vez de `--paralelo 10`, ou a carga da máquina muda os resultados
(ver `docs/decisoes.md`, C3a). Se o CSV do `--exp` já existir, o script continua de onde parou; para refazer,
use outro nome.

### 6. Outros comandos

```bash
.venv/bin/python scripts/auditar_cortes.py      # reconfere com CP-SAT os cortes do exato (lê resultados/ampl/logs)
.venv/bin/python scripts/tabelas.py --meta BRKGA=resultados/meta/variantes64.csv:BRKGA-ff-bl-desempate \
                                           RKO=resultados/meta/rko64.csv:RKO-ff-bl-desempate
.venv/bin/python scripts/graficos.py BRKGA=resultados/meta/variantes64.csv:BRKGA-ff-bl-desempate \
                                     RKO=resultados/meta/rko64.csv:RKO-ff-bl-desempate
```

No AMPL interativo (de dentro de `ampl/`): `model bppc.mod; data dat/2kdc50.dat; include bppc.run;`

## Documentos de estudo

- `docs/fluxo/fluxo_projeto.pdf`: fluxogramas, resultados e perguntas para o professor.
- `docs/retorno_professor/retorno_professor.pdf`: retorno do professor e próximos passos.
- `docs/retorno_professor_2/retorno_professor_2.pdf`: segunda conversa com o professor (caixas iniciais, "para qual caixa", ordem fixa, comparar BRKGAs).

Para regenerar o documento de fluxo depois de novos resultados:

```bash
.venv/bin/python scripts/tabelas.py --meta BRKGA=resultados/meta/variantes64.csv:BRKGA-ff-bl-desempate \
                                           RKO=resultados/meta/rko64.csv:RKO-ff-bl-desempate
.venv/bin/python scripts/gerar_tex_tabelas.py
cd docs/fluxo && pdflatex fluxo_projeto.tex && pdflatex fluxo_projeto.tex
```
