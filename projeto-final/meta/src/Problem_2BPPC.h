// *******************************************************************
//   Problem.h do RKO para o 2BPPC (empacotamento 2D com conflitos)
//   Interface exigida pelo RKO: TProblemData (com campo n = nº de
//   chaves), ReadData, Decoder e FreeMemoryProblem.
// *******************************************************************
#ifndef _PROBLEM_2BPPC_H
#define _PROBLEM_2BPPC_H

#include <atomic>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

// ------------------- Variantes do decodificador ----------------------
// Definidas pela linha de comando ANTES de ReadData (ver rko_bppc.cpp).
enum Escolha { FF = 0, BF = 1, CHAVE = 2 };      // regra de escolha da caixa
enum Posic   { BSSF = 0, BL = 1 };               // regra de posicionamento
enum Aval    { SO_CAIXAS = 0, DESEMPATE = 1 };   // função de avaliação

struct DecoderConfig {
    int escolha = FF;       // CHAVE => vetor de 2n chaves
    int posic = BSSF;
    int aval = DESEMPATE;
};
DecoderConfig g_cfg;

struct TProblemData
{
    int n;                                  // tamanho do vetor de chaves (n ou 2n)

    int nItems;                             // nº de itens
    int W, H;                               // dimensões da caixa
    std::vector<int> w, h;                  // dimensões dos itens
    std::vector<uint32_t> conf;             // conf[i]: bit j = 1 se i e j em conflito
    int nArestas;
    int LB;                                 // limitante inferior (para parar cedo)
};

struct Rect { int x, y, w, h; };
struct Posicao { int item, caixa, x, y; };

// ------------- Melhor solução global e parada por alvo ---------------
// O RKO só guarda soluções no pool quando a metaheurística as entrega;
// guardamos aqui a melhor decodificada, para não perder a que atinge o LB.
std::atomic<bool> g_alvo(false);                 // atingiu o LB (ótimo provado)
std::atomic<double> g_best_ofv(1e18);
std::vector<double> g_best_rk;
double g_best_time = 0.0, g_start_time = 0.0;
double get_time_in_seconds();                    // definida em Method.h
// O IPR do RKO v2.0 não confere stop_execution, só o relógio (runData.MAXTIME).
// Ao atingir o alvo, zeramos MAXTIME do objeto do main (não-const) por este
// ponteiro; todas as metaheurísticas o releem a cada iteração e param.
TRunData *g_runData = nullptr;

// ===================== Leitura da instância ==========================
// Limitante inferior: max(ceil(área/WH), maior clique no grafo estendido)
static int maiorClique(const std::vector<uint32_t> &adj, uint32_t P, int tam, int melhor)
{
    if (P == 0) return std::max(tam, melhor);
    if (tam + __builtin_popcount(P) <= melhor) return melhor;
    while (P) {
        if (tam + __builtin_popcount(P) <= melhor) break;
        int v = __builtin_ctz(P);
        P &= P - 1;
        melhor = maiorClique(adj, P & adj[v], tam + 1, melhor);
    }
    return melhor;
}

void ReadData(char name[], TProblemData &data)
{
    std::ifstream f(name);
    if (!f) { printf("\nERRO: arquivo (%s) não encontrado!\n", name); exit(1); }
    int m;
    f >> data.nItems >> m >> data.W >> data.H;
    int n = data.nItems;
    if (n > 32) { printf("\nERRO: máscara de 32 bits suporta até 32 itens\n"); exit(1); }
    data.w.assign(n, 0); data.h.assign(n, 0); data.conf.assign(n, 0);
    for (int i = 0; i < n; i++) { int v; f >> data.w[i] >> data.h[i] >> v; }
    for (int e = 0; e < m; e++) {
        int a, b; f >> a >> b; a--; b--;
        if (a == b) continue;
        data.conf[a] |= (1u << b); data.conf[b] |= (1u << a);
    }
    data.nArestas = m;

    // LB (o decodificador respeita só os conflitos originais; as arestas por
    // dimensão entram aqui apenas para a clique, pois são implícitas).
    long area = 0;
    std::vector<uint32_t> ext = data.conf;
    for (int i = 0; i < n; i++) {
        area += (long)data.w[i] * data.h[i];
        for (int j = 0; j < n; j++)
            if (i != j && data.w[i] + data.w[j] > data.W && data.h[i] + data.h[j] > data.H)
                ext[i] |= (1u << j);
    }
    int lbArea = (int)((area + (long)data.W * data.H - 1) / ((long)data.W * data.H));
    int clq = maiorClique(ext, (n == 32) ? 0xFFFFFFFFu : ((1u << n) - 1), 0, 0);
    data.LB = std::max(lbArea, clq);

    data.n = (g_cfg.escolha == CHAVE) ? 2 * n : n;
}

// ====================== Maximal Rectangles ===========================
struct Caixa {
    std::vector<Rect> livres;
    long area = 0;
    uint32_t itens = 0;
};

// Melhor posição de um item w x h na caixa; devolve false se não cabe.
static inline bool acharPosicao(const Caixa &c, int w, int h, int regra, int &bx, int &by,
                                long &s1, long &s2)
{
    bool achou = false;
    for (const Rect &r : c.livres) {
        if (r.w < w || r.h < h) continue;
        long a = 0, b = 0;
        if (regra == BSSF) {
            long dw = r.w - w, dh = r.h - h;
            a = std::min(dw, dh); b = std::max(dw, dh);
        } else {               // Bottom-Left: menor topo, depois mais à esquerda
            a = r.y + h; b = r.x;
        }
        if (!achou || a < s1 || (a == s1 && b < s2)) {
            achou = true; s1 = a; s2 = b; bx = r.x; by = r.y;
        }
    }
    return achou;
}

static inline void colocar(Caixa &c, int x, int y, int w, int h)
{
    std::vector<Rect> novos;
    novos.reserve(c.livres.size() * 2 + 4);
    for (const Rect &r : c.livres) {
        if (x >= r.x + r.w || x + w <= r.x || y >= r.y + r.h || y + h <= r.y) {
            novos.push_back(r); continue;
        }
        if (x > r.x)             novos.push_back({r.x, r.y, x - r.x, r.h});
        if (x + w < r.x + r.w)   novos.push_back({x + w, r.y, r.x + r.w - (x + w), r.h});
        if (y > r.y)             novos.push_back({r.x, r.y, r.w, y - r.y});
        if (y + h < r.y + r.h)   novos.push_back({r.x, y + h, r.w, r.y + r.h - (y + h)});
    }
    // remove retângulos contidos em outros (e duplicatas)
    c.livres.clear();
    for (size_t i = 0; i < novos.size(); i++) {
        const Rect &a = novos[i];
        bool contido = false;
        for (size_t j = 0; j < novos.size() && !contido; j++) {
            if (i == j) continue;
            const Rect &b = novos[j];
            if (b.x <= a.x && b.y <= a.y && a.x + a.w <= b.x + b.w && a.y + a.h <= b.y + b.h) {
                bool igual = (a.x == b.x && a.y == b.y && a.w == b.w && a.h == b.h);
                if (!igual || j < i) contido = true;
            }
        }
        if (!contido) c.livres.push_back(a);
    }
    c.area += (long)w * h;
}

// ========================= Decodificador ==============================
// Devolve o valor da solução; se `saida` != nullptr, também as posições.
double Decodifica(const std::vector<double> &rk, const TProblemData &data,
                  std::vector<Posicao> *saida)
{
    const int n = data.nItems;
    const long WH = (long)data.W * data.H;

    // 1. ordem dos itens pelas chaves
    int ordem[32];
    for (int i = 0; i < n; i++) ordem[i] = i;
    std::sort(ordem, ordem + n, [&](int a, int b) { return rk[a] < rk[b]; });

    std::vector<Caixa> caixas;
    caixas.reserve(n);
    if (saida) saida->clear();

    // 2. insere item a item
    for (int t = 0; t < n; t++) {
        const int i = ordem[t];
        int esc = g_cfg.escolha;
        if (esc == CHAVE) esc = (rk[n + i] < 0.5) ? FF : BF;
        const long ai = (long)data.w[i] * data.h[i];

        int kSel = -1, xSel = 0, ySel = 0;
        for (int k = 0; k < (int)caixas.size(); k++) {
            const Caixa &c = caixas[k];
            if (c.itens & data.conf[i]) continue;          // conflito
            if (c.area + ai > WH) continue;                // área
            int x = 0, y = 0; long s1 = 0, s2 = 0;
            if (!acharPosicao(c, data.w[i], data.h[i], g_cfg.posic, x, y, s1, s2)) continue;
            if (esc == FF) { kSel = k; xSel = x; ySel = y; break; }
            if (kSel < 0 || c.area > caixas[kSel].area) { kSel = k; xSel = x; ySel = y; }
        }
        if (kSel < 0) {                                     // abre caixa nova
            Caixa nova;
            nova.livres.push_back({0, 0, data.W, data.H});
            caixas.push_back(nova);
            kSel = (int)caixas.size() - 1; xSel = 0; ySel = 0;
        }
        colocar(caixas[kSel], xSel, ySel, data.w[i], data.h[i]);
        caixas[kSel].itens |= (1u << i);
        if (saida) saida->push_back({i, kSel, xSel, ySel});
    }

    // 3. avaliação
    double ofv = (double)caixas.size();
    if (g_cfg.aval == DESEMPATE) {
        long menor = WH;
        for (const Caixa &c : caixas) menor = std::min(menor, c.area);
        ofv += (double)menor / (double)WH;                 // em [0,1)
    }
    return ofv;
}

double Decoder(TSol &s, const TProblemData &data)
{
    double ofv = Decodifica(s.rk, data, nullptr);
    if (ofv < g_best_ofv.load()) {
        #pragma omp critical(melhor_global)
        {
            if (ofv < g_best_ofv.load()) {
                g_best_ofv.store(ofv);
                g_best_rk = s.rk;
                g_best_time = get_time_in_seconds() - g_start_time;
            }
        }
    }
    if ((int)ofv <= data.LB) g_alvo.store(true);    // ótimo provado
    if (g_alvo.load()) {                            // avisa as metaheurísticas
        stop_execution.store(true);
        if (g_runData) g_runData->MAXTIME = 0;
    }
    return ofv;
}

void FreeMemoryProblem(TProblemData &data)
{
    data.w.clear(); data.h.clear(); data.conf.clear();
}

#endif
