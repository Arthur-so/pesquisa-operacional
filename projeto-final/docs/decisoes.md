# Decisões de projeto

Registro do que foi decidido, das alternativas e do motivo. Serve de material para o artigo.
Ambiente dos testes: Intel Core i5-13420H (12 threads), 23 GB de RAM, Linux, g++ 11.4, Python 3.10,
AMPL 20261109 (amplpy 0.18) + HiGHS 1.15.1, OR-Tools 9.15 (só para auditoria).

---

## A. Dados

### A1. Pasta das instâncias e instâncias que faltavam
- **Fato:** o zip tem só 52 arquivos (`2bppc/2kdc01`–`2kdc52`), não 64.
- **Decisão:** gerar as 53–64 (`scripts/gerar_instancias_60.py` → `instancias_geradas/`) copiando a
  original indicada pelo artigo-base (53←21, 54←38, …, 64←16) e trocando só a caixa para 60×60.
- **Motivo:** conferimos a regra nas cópias que existem: 50≡18, 51≡35 e 52≡04 são idênticas,
  exceto a linha `W H`.
- **Alternativa:** pedir os arquivos aos autores (não deu: o e-mail do Hokama não existe mais).

### A2. A instância 01 do zip está errada
- **Fato:** o arquivo `2kdc01` é uma cópia exata dos dados da `2kdc02` (tipo II, sem rodapé). A `2kdc49`,
  que deveria ser "a 01 com caixa 60×60", não bate com ele, e todos os itens dela cabem em 30×30.
- **Decisão:** reconstruir a 01 como "49 com caixa 30×30" (`instancias_geradas/2kdc01`, que tem
  prioridade sobre o arquivo do zip na leitura). O arquivo original não foi alterado.
- **Consequência:** a 01 reconstruída é tipo I, d=7%, como diz a Tabela 1 do artigo-base.

### A3. Leitura
- O nome vem do arquivo (o rodapé às vezes diz `2kdc4`); o valor da mochila é ignorado;
  pares repetidos e laços seriam descartados (não ocorrem).

---

## B. Método exato (AMPL)

### B1. Solver
- **Decisão:** AMPL via `amplpy` com **HiGHS** (gratuito). Rodou nas 64 instâncias com a licença
  demo que vem com o amplpy (os modelos são pequenos porque K = UB, ver B3).
- **Alternativa:** CPLEX/Gurobi acadêmico, se o professor exigir (é só trocar `option solver`).

### B2. Renumeração dos itens (ordem "Oc" do artigo-base)
- **Decisão:** o `.dat` renumera os itens por grau de conflito decrescente no grafo estendido
  (empate: área decrescente). `orig[i]` guarda o número original, usado na saída.
- **Motivo:** (8) e (10) fixam os primeiros itens nas primeiras caixas; colocar ali os itens mais
  restritos fortalece a quebra de simetria. Foi a melhor configuração do artigo-base.

### B3. Número de caixas do modelo: K = UB heurístico
- **Decisão:** `K = {1..UB}`, com UB = melhor de 204 ordens × {FF, BF} × {BSSF, BL} do guloso
  Maximal Rectangles (`preprocess.upper_bound`), em vez de `K = {1..n}`.
- **Motivo:** reduz as variáveis de 650 para 25·UB+UB (UB ≤ 20) e é a melhoria "L2" do
  artigo-base. É válido porque existe solução com UB caixas.

### B4. Forma das restrições
- (4) conflito: `α_ik + α_jk ≤ 1`, para E ∪ ED (ED = arestas da regra (12)).
- (11) pilha de largos / fileira de altos com `≤ H·β_k` e `≤ W·β_k` (mais forte que `≤ H` e
  igualmente válida).
- (13) cliques maximais com ≥ 3 itens do grafo estendido, `Σ α_ik ≤ β_k`. As de 2 itens já são (4).
- (10) só para `i < K`, porque para `i ≥ K` a restrição é redundante.

### B5. Subproblema 2D-OPP (exato)
- PLI disjuntivo clássico (variáveis de posição e de relação esquerda/abaixo entre pares), com três reforços que **não** mudam o conjunto de soluções viáveis:
  1. limites `x_i ≤ W − w_i` e `y_i ≤ H − h_i` direto nas variáveis;
  2. `l_ij = 0` se `w_i + w_j > W` e `b_ij = 0` se `h_i + h_j > H` (relação impossível);
  3. quebra de simetria por espelhamento: o maior item fica no quadrante inferior esquerdo
     (`2x ≤ W − w`, `2y ≤ H − h`). Espelhar a caixa preserva a viabilidade.
- Antes do PLI: cache e condições necessárias baratas (área, pilha de largos ≤ H, fileira de
  altos ≤ W). **Nenhum teste heurístico**: toda resposta é exata.
- Cache: cada grupo vira o número `Σ 2^(i−1)` (exato em ponto flutuante para n = 25), guardado
  nos conjuntos `VIAVEIS` e `INVIAVEIS`.

### B6. Redução do grupo inviável
- **Decisão:** filtro de remoção. Tenta tirar os itens em ordem de **área crescente**; se o grupo
  continua não cabendo, o item sai. O corte (5) vale para o grupo reduzido em **todas** as caixas.
- **Motivo:** grupos menores dão cortes mais fortes. Começar pelos pequenos tende a deixar no
  grupo os itens grandes, que são os "culpados".
- **Resultado:** a auditoria (B9) mostrou que **100% dos cortes são mínimos**.

### B7. Coordenadas inteiras na solução final
- O PLI pode devolver coordenadas fracionárias. No fim, para cada caixa, x e y são recalculados como
  caminho mais longo nas relações esquerda/abaixo escolhidas pelo solver. O resultado é inteiro,
  nunca maior que o do solver (logo dentro da caixa), e respeita as mesmas separações.

### B8. Tempo
- No AMPL: `_ampl_elapsed_time + _total_solve_elapsed_time` (só o primeiro não conta o solver).
  O executor (`ampl/rodar_ampl.py`) mede também o tempo de parede, que inclui carregar o AMPL.
- Limite de 3600 s por instância. Se estourar, reporta o LB (máximo entre o LB inicial, o último
  mestre resolvido e o `bestbound` do HiGHS) e o UB guloso. Não aconteceu em nenhuma instância.

### B9. Validação dos resultados exatos
- Toda solução do AMPL passa pelo verificador independente (`src/bppc/solution.py`).
- **Auditoria dos cortes** (`scripts/auditar_cortes.py`): cada grupo proibido foi reconferido com
  outro método exato, o CP-SAT (programação por restrições, `NoOverlap2D`). **Todos os cortes das 64
  instâncias são válidos e mínimos.** Logo, os 64 ótimos estão confirmados por dois métodos
  independentes.

### B10. Resultado (Etapa 5)
- **64/64 instâncias resolvidas até o ótimo, 150,4 s no total** (158 s de parede, incluindo carregar o AMPL) (máx.: 41,5 s na 53; 55 em 2,3 s).
  Tabela: `resultados/ampl/resultados.csv`.
- Para comparação, o artigo-base (C++ + CPLEX + CP Optimizer, outra máquina) levou ~30 min no
  total com a melhor configuração, 778 s na 53 e 362 s na 55. Hipótese para a diferença: o UB guloso
  (K pequeno), os cortes mínimos aplicados em todas as caixas e a quebra de simetria no 2D-OPP.
  **Não é uma comparação justa** (máquina, solver e linguagem diferentes); deve ser citada com
  essa ressalva.

---

## C. Metaheurística

### C1. Arcabouço
- **Decisão:** RKO oficial v2.0 (`github.com/RKO-solver/RKO_Cpp_v2.0`, clonado em
  `meta/RKO_Cpp_v2.0`). O código genérico (Data.h, Method.h, QLearning.h, MH/*.h) é usado
  **sem modificação**. Escrevemos:
  - `meta/src/Problem_2BPPC.h`: o "Problem.h" do 2BPPC (TProblemData, ReadData, Decoder);
  - `meta/src/rko_bppc.cpp`: cópia adaptada do `main.cpp` do RKO.
- **Adaptações no main e motivos:**
  1. **Sementes:** no main original, `#pragma omp parallel private(rng)` dá a cada thread uma cópia
     do gerador com a semente padrão do `mt19937`. A semente escolhida só afeta o pool inicial.
     Usamos `thread_local` e semeamos cada thread com `semente·1000003 + 7919·(thread+1)`.
  2. **Parada no LB:** se o decodificador atinge o LB, a solução é ótima provada. Ele sinaliza a
     parada via `stop_execution`. Sem isso, toda execução gastaria o tempo inteiro.
  3. **Melhor solução global no decodificador:** as metaheurísticas só levam soluções ao pool no
     fim de uma iteração. Se paramos no meio, a solução que atingiu o LB se perderia. O decodificador
     guarda a melhor solução vista e o instante em que ela apareceu (`tempo_melhor`).
  4. **IPR não para:** o IPR do RKO v2.0 não confere `stop_execution`, só o relógio
     (`runData.MAXTIME`). As outras threads ficavam presas na barreira do `omp for` até o fim do
     tempo, mesmo com o ótimo provado (na 55: ótimo em 0,03 s, término em 5 s). Correção sem mexer no
     RKO: ao atingir o alvo, o decodificador zera o `MAXTIME` do objeto `runData` do main por um
     ponteiro global. Todas as metaheurísticas releem esse campo a cada iteração e param (55: 0,008 s).
  5. Configuração, semente e variante do decodificador entram pela linha de comando. A saída é uma
     linha `RESULTADO` + arquivo de solução no formato comum.

### C2. Decodificador
Chaves → ordem dos itens (menor chave primeiro). Para cada item, as caixas abertas são filtradas
por conflito (máscara de bits: `itens_da_caixa & conflitos[i]`), por área livre e por encaixe
geométrico (Maximal Rectangles). Escolhida a caixa, o item é posicionado. Se nenhuma serve, abre
uma caixa nova. **Toda solução é viável por construção.** O verificador conferiu todas as
execuções (0 inválidas).

Variantes implementadas (parâmetros `--escolha`, `--posic`, `--aval`):
- escolha da caixa: FF (primeira) | BF (mais cheia) | chave (2n chaves: a chave n+i escolhe FF/BF);
- posicionamento: Maximal Rectangles com BSSF | Bottom-Left;
- avaliação: só o nº de caixas | nº de caixas + área da caixa mais vazia / WH.

O LB do decodificador (área e maior clique no grafo estendido, por branch-and-bound em bits) é
calculado em C++ e bate com o do Python.

### C3. Testes rápidos das variantes (BRKGA, parâmetros offline do RKO)
**Condição de execução:** 3 execuções simultâneas, cada uma fixada com `taskset` num núcleo rápido
próprio (CPUs 0, 2, 4). Ver C3a: a primeira rodada, com 10 simultâneas, saiu contaminada.

**Teste 1:** 12 variantes × 13 instâncias (9, 17, 22, 28, 29, 40, 48, 55, 59, 53, 3, 20, 26: onde o
guloso falha ou o ótimo é maior que o LB) × 5 sementes × 2 s = 780 execuções.
Arquivo: `resultados/meta/variantes.csv`.

| variante | % no ótimo | % na 48 | tempo médio até a melhor (s) |
|---|---|---|---|
| BF-BL-desempate | 100,0 | 100 | 0,113 |
| FF-BL-desempate | 100,0 | 100 | 0,148 |
| FF-BSSF-desempate | 100,0 | 100 | 0,151 |
| BF-BSSF-desempate | 98,5 | 80 | 0,098 |
| chave-BSSF-desempate | 98,5 | 80 | 0,135 |
| chave-BL-desempate | 96,9 | 60 | 0,133 |
| (as 6 variantes sem desempate) | 92,3 – 93,8 | 0 – 20 | 0,03 – 0,08 |

**Teste 2:** as 4 melhores × 64 instâncias × 5 sementes × 1 s = 1280 execuções
(`resultados/meta/variantes64.csv`):

| variante | % no ótimo | % na 48 | tempo médio até a melhor (s) |
|---|---|---|---|
| BF-BL-desempate | 100,0 | 100 | 0,048 |
| FF-BL-desempate | 100,0 | 100 | 0,052 |
| BF-BSSF-desempate | 99,7 | 80 | 0,044 |
| FF-BSSF-desempate | 99,4 | 60 | 0,047 |

A 48 é a única instância em que as variantes se diferenciam. 0 soluções inválidas nas 2060 execuções.

### C3a. Correção: efeito da carga da máquina (11/11/2026)
- A primeira rodada dos dois testes executou **10 execuções ao mesmo tempo**. O i5-13420H tem 4
  núcleos rápidos (4,6 GHz, 2 threads cada: CPUs 0–7) e 4 lentos (3,4 GHz: CPUs 8–11). Execuções em
  núcleo lento ou dividindo núcleo andaram mais devagar e foram cortadas pelo limite **de relógio**.
- Efeito visível: no Teste 2, a BF-BL não achou o ótimo da 48 em nenhuma das 5 execuções (5 caixas).
  Rodando sozinha, ou com núcleo fixo, ela acerta 5 de 5 (0,12–0,71 s). Com a mesma semente, a busca
  é a mesma (por exemplo, semente 1: ótimo aos 0,405 s, sozinha ou fixada); só a velocidade mudava.
- A conclusão antiga, de que "FF-BL é melhor que BF-BL", estava **errada**. Os testes foram refeitos com
  `meta/experimentos.py --cpus 0,2,4`; os arquivos antigos estão em `resultados/meta/*_10simultaneas.csv`.
- **Lição:** com limite por tempo de relógio, o resultado depende da carga da máquina. Isso reforça a
  parada por nº de avaliações do decodificador (dúvida A6).

### C4. Decisão sobre o decodificador
- **Padrão: n chaves, FF, Bottom-Left, avaliação com desempate.**
- O **desempate é a decisão mais importante**: só com o nº de caixas, a função é um platô (quase
  todas as ordens dão o mesmo valor) e o BRKGA não tem direção. A área da caixa mais vazia dá um
  gradiente na direção de esvaziar e eliminar uma caixa. Na 48: 0–20% sem desempate, 60–100% com.
- **FF e BF empatam.** FF fica como padrão por ser mais simples e mais barata (para na primeira caixa
  que serve; BF olha todas).
- **BL um pouco à frente de BSSF**, mas só no Teste 2 e só na 48 (100% contra 60–80%); no Teste 1, a
  FF-BSSF também acertou 100%. É um indício, não uma prova.
- **2n chaves não compensaram:** dobram o espaço de busca e não melhoraram nenhuma instância.
- As outras variantes continuam no código, para o artigo e para eventuais perguntas do professor.

### C5. Soluções iniciais "inteligentes" (área / grau decrescente)
- **Não implementado (sugestão).** No RKO v2.0, as metaheurísticas não partem do pool: cada uma
  gera sua população ou solução inicial aleatória (`CreateInitialSolutions`). Injetar sementes
  exigiria modificar o código genérico. Como o BRKGA já acha o ótimo em < 0,1 s em média, o ganho
  seria pequeno.

### C6. Observação importante para a comparação (Etapa 6)
- Em **32 das 64 instâncias o ótimo é maior que o LB**. Nelas a metaheurística acha o ótimo, mas
  não tem como prová-lo e roda até o tempo limite. O tempo justo a comparar é o **tempo até a
  melhor solução** (`tempo_melhor`), lado a lado com o tempo total.

### C7. Primeira comparação BRKGA × RKO completo (64 instâncias × 5 sementes × 1 s)
Decodificador FF-BL-desempate. BRKGA com 1 thread; RKO com 10 metaheurísticas (10 threads) e
Q-Learning. Arquivos: `resultados/meta/variantes64.csv`, `resultados/meta/rko64.csv`; tabela em
`resultados/tabelas/etapa6.md`; figuras em `resultados/figuras/`.

| método | % execuções no ótimo | tempo médio até a melhor (s) | tempo total médio (s) |
|---|---|---|---|
| Exato (AMPL+HiGHS) | 100 (prova) | — | 2,35 (máx. 41,5) |
| BRKGA | 100,0 | 0,052 (máx. 0,44) | 0,51 |
| RKO | 99,7 | 0,030 (máx. 0,18) | 0,51 |

- BRKGA: 3 execuções simultâneas com núcleo fixo (dados refeitos em 11/11/2026, ver C3a). RKO: uma
  execução por vez (ele próprio usa 10 threads, que dividem 4 núcleos rápidos e 4 lentos).
- Só a 48 não fecha sempre: o RKO erra 1 de 5; o BRKGA acerta as 5.
- O tempo total médio da metaheurística (~0,5 s) é dominado pelas 32 instâncias em que o ótimo é
  maior que o LB: nelas, a execução vai até o limite de 1 s.
- O RKO acha a melhor solução ~1,7× mais rápido (0,030 s contra 0,052 s), mas usa 10 threads contra 1.
