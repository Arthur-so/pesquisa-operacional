# =====================================================================
#  2BPPC - Empacotamento bidimensional em contêineres com conflitos
#  Modelo mestre (PLI) + subproblema de conferência geométrica (2D-OPP)
#  Numeração das equações = a do artigo do projeto (Artigo_SBPO_2BPPC.docx)
# =====================================================================

# ------------------------- Dados da instância ------------------------
param nome symbolic;
param n integer > 0;
param W integer > 0;
param H integer > 0;
set I := 1..n;                        # itens (já renumerados por conflito)
param w {I} integer > 0;
param h {I} integer > 0;
param orig {I} integer > 0;           # número do item no arquivo original

param K integer > 0;                  # caixas disponíveis (= UB heurístico)
set B := 1..K;
param LB integer > 0;                 # max(ceil(área/WH), maior clique)
param UB integer > 0;
param nfix integer >= 1;              # restrição (10) para i = 2..nfix

set E  within {i in I, j in I: i < j};   # conflitos originais
set ED within {i in I, j in I: i < j};   # conflitos por dimensão, regra (12)
param nclq integer >= 0;
set CLQ {1..nclq} within I;              # cliques maximais (>= 3 itens)
param ordem_rem {1..n} in I;             # ordem de remoção na redução

# ------------------- Cortes geométricos (5), sob demanda --------------
param ncortes integer >= 0 default 0;
set CORTE {1..ncortes} within I;         # grupos que NÃO cabem numa caixa

# ============================ MESTRE ==================================
var beta  {B} binary;                    # caixa k usada
var alpha {I, B} binary;                 # item i na caixa k

minimize NumCaixas: sum {k in B} beta[k];                                # (1)

subject to Area {k in B}:                                                # (2)
    sum {i in I} w[i] * h[i] * alpha[i,k] <= W * H * beta[k];

subject to Atribui {i in I}:                                             # (3)
    sum {k in B} alpha[i,k] = 1;

subject to Conflito {(i,j) in E union ED, k in B}:                      # (4)+(12)
    alpha[i,k] + alpha[j,k] <= 1;

subject to Geometria {c in 1..ncortes, k in B}:                          # (5)
    sum {i in CORTE[c]} alpha[i,k] <= card(CORTE[c]) - 1;

subject to FixaPrimeiro: alpha[1,1] = 1;                                 # (8)

subject to Consecutivas {k in B: k >= 2}: beta[k-1] >= beta[k];          # (9)

subject to RestringeItem {i in 2..nfix: i < K}:                          # (10)
    sum {k in B: k <= i} alpha[i,k] = 1;

subject to PilhaLargos {k in B}:                                         # (11)
    sum {i in I: 2 * w[i] > W} h[i] * alpha[i,k] <= H * beta[k];
subject to FileiraAltos {k in B}:                                        # (11)
    sum {i in I: 2 * h[i] > H} w[i] * alpha[i,k] <= W * beta[k];

subject to Clique {c in 1..nclq, k in B}:                                # (13)
    sum {i in CLQ[c]} alpha[i,k] <= beta[k];

subject to Limitante: sum {k in B} beta[k] >= LB;                        # (14)

# ===================== SUBPROBLEMA 2D-OPP (exato) =====================
# Os itens de P cabem numa caixa W x H, sem rotação?
# l[i,j] = 1 -> i totalmente à esquerda de j;  b[i,j] = 1 -> i abaixo de j.
set P within I default {};
param pivo in I default 1;               # maior item de P (quebra de simetria)

var x {i in P} >= 0, <= W - w[i];
var y {i in P} >= 0, <= H - h[i];
# Se dois itens não cabem lado a lado (ou empilhados), a relação é fixada em 0.
var l {i in P, j in P: i <> j} binary, <= if w[i] + w[j] > W then 0 else 1;
var b {i in P, j in P: i <> j} binary, <= if h[i] + h[j] > H then 0 else 1;

subject to Separa {i in P, j in P: i < j}:
    l[i,j] + l[j,i] + b[i,j] + b[j,i] >= 1;
subject to Esquerda {i in P, j in P: i <> j}:
    x[i] + w[i] <= x[j] + W * (1 - l[i,j]);
subject to Abaixo {i in P, j in P: i <> j}:
    y[i] + h[i] <= y[j] + H * (1 - b[i,j]);
# Espelhar a caixa na horizontal/vertical preserva a viabilidade, então o
# maior item pode ficar no quadrante inferior esquerdo.
subject to SimetriaX {i in P: i = pivo}: 2 * x[i] <= W - w[i];
subject to SimetriaY {i in P: i = pivo}: 2 * y[i] <= H - h[i];

problem Mestre: beta, alpha, NumCaixas, Area, Atribui, Conflito, Geometria,
    FixaPrimeiro, Consecutivas, RestringeItem, PilhaLargos, FileiraAltos,
    Clique, Limitante;

problem OPP: x, y, l, b, Separa, Esquerda, Abaixo, SimetriaX, SimetriaY;

# ------------------ Parâmetros de execução (bppc.run) -----------------
param tlim default 3600;                     # tempo limite (s)
param arq_sol symbolic default 'solucao.sol';
param arq_csv symbolic default 'resultados.csv';
param dir_ampl symbolic default '.';         # pasta com testa_grupo.run
