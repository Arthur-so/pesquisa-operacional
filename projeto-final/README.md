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

A metaheurística é o **BRKGA** (do arcabouço RKO) com o decodificador do projeto: cada item tem 3 chaves (ordem,
caixa e regra de posição), começam abertas K₀ = LB caixas, e o plano B com reescrita lamarckiana trata os itens que
não cabem na caixa escolhida (ver `docs/retorno_professor_2/retorno_professor_2.pdf`, Figura 2).

```bash
cd meta
./rko_bppc ../2bppc/2kdc48 --tempo 5 --semente 1 --conf config/brkga.conf --sol saida48.sol
cd ..
PYTHONPATH=src .venv/bin/python -m bppc.plot 48 meta/saida48.sol caixas48.png   # confere e desenha
```

Saída esperada:

```
RESULTADO ../2bppc/2kdc48 semente=1 caixas=4 ofv=4.754800 LB=4 tempo_melhor=0.642 tempo_total=0.642 alvo=1 ...
          ... escolha=caixa posic=chave aval=desempate planob=bf lamarck=1 pb_outra=0.3055 pb_nova=0.0737
```

- `caixas`: nº de caixas da melhor solução; `tempo_melhor`: quando ela foi achada; `tempo_total`: duração da execução;
- `alvo=1`: atingiu o LB (ótimo provado) e parou antes do tempo; `alvo=0`: rodou até o limite;
- `pb_outra` / `pb_nova`: fração dos itens que não couberam na caixa da chave e foram para outra caixa aberta / para
  uma caixa nova (plano B), somando todas as decodificações da busca;
- a mesma semente refaz a mesma busca.

Opções do decodificador (os valores padrão são os escolhidos):

| opção | valores | padrão |
|---|---|---|
| `--posic` | `chave` (a chave do item escolhe BL ou BSSF), `bl`, `bssf` (regra fixa) | `chave` |
| `--planob` | `bf` (a mais cheia que serve; senão caixa nova), `seguinte` (k+1, k+2, …), `nova` (caixa nova direto) | `bf` |
| `--lamarck` | `1` (reescreve a chave quando o plano B muda a caixa), `0` | `1` |
| `--aval` | `desempate` (caixas + ocupação da mais vazia), `caixas` | `desempate` |

Teste da reescrita, sem rodar a metaheurística: `./rko_bppc ../2bppc/2kdc48 --teste-lamarck 2000` confere que
decodificar de novo um vetor reescrito dá a mesma solução.

### 5. Metaheurística: várias execuções (≈ 3 min)

```bash
# BRKGA: 64 instâncias × 5 sementes × 1 s, 3 execuções por vez, cada uma num núcleo rápido
.venv/bin/python meta/experimentos.py --exp meu_brkga --configs BRKGA-caixa-chave-bf-lam \
       --tempo 1 --sementes 5 --cpus 0,2,4
.venv/bin/python meta/analisar.py resultados/meta/meu_brkga.csv --por-instancia
```

`analisar.py` mostra a % de execuções que acharam o ótimo do exato, o tempo médio até a melhor solução e quantas
soluções foram inválidas (deve ser 0). Para comparar com o resultado oficial (99,7 % no ótimo, 0,099 s):

```bash
.venv/bin/python meta/analisar.py resultados/meta/caixa64.csv
```

Variantes prontas para comparar: `--configs caixa` roda as cinco (`BRKGA-caixa-chave-bf-lam`,
`-chave-bf-semlam`, `-chave-seguinte-lam`, `-chave-nova`, `-bl-bf-lam`).

**Cuidado com execuções simultâneas:** o limite é de tempo de relógio. Use `--cpus 0,2,4` (um núcleo rápido
por execução) em vez de `--paralelo 10`, ou a carga da máquina muda os resultados
(ver `docs/decisoes.md`, C3a). Se o CSV do `--exp` já existir, o script continua de onde parou; para refazer,
use outro nome.

### 6. Outros comandos

```bash
.venv/bin/python scripts/auditar_cortes.py      # reconfere com CP-SAT os cortes do exato (lê resultados/ampl/logs)
.venv/bin/python scripts/tabelas.py --meta BRKGA=resultados/meta/caixa64.csv:BRKGA-caixa-chave-bf-lam
.venv/bin/python scripts/graficos.py BRKGA=resultados/meta/caixa64.csv:BRKGA-caixa-chave-bf-lam
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
