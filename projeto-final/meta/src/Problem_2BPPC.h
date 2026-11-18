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
enum Escolha { FF = 0, BF = 1, CHAVE = 2, CAIXA = 3 };  // regra de escolha da caixa
enum Posic   { BSSF = 0, BL = 1, PCHAVE = 2 };           // regra de posicionamento
enum Aval    { SO_CAIXAS = 0, DESEMPATE = 1 };           // função de avaliação
enum PlanoB  { PB_BF = 0, PB_SEGUINTE = 1, PB_NOVA = 2 }; // modo CAIXA: item não cabe na caixa da chave

struct DecoderConfig {
    int escolha = FF;       // CHAVE => 2n chaves (ordem + FF/BF por item)
                            // CAIXA => a chave do item escolhe a caixa (ver DecodificaCaixa)
    int posic = BSSF;       // PCHAVE => uma chave por item escolhe BL (<0,5) ou BSSF (>=0,5)
    int aval = DESEMPATE;
    int planob = PB_BF;     // só no modo CAIXA
    bool lamarck = true;    // só no modo CAIXA: reescreve a chave quando o plano B muda a caixa
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

// Estatística do plano B (modo CAIXA): quantos itens foram decodificados e quantos não
// couberam na caixa escolhida pela chave (foram para outra caixa aberta ou para uma nova).
struct EstatPlanoB { long itens = 0, outra = 0, nova = 0; };
std::atomic<long> g_pb_itens(0), g_pb_outra(0), g_pb_nova(0);

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

    if (g_cfg.escolha == CAIXA)                  // ordem + caixa (+ posição, se PCHAVE)
        data.n = (g_cfg.posic == PCHAVE) ? 3 * n : 2 * n;
    else
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

// ===================== Decodificador modo CAIXA ========================
// Vetor: rk[0..n)   = ordem dos itens (menor chave primeiro)
//        rk[n..2n)  = caixa de cada item: com K caixas abertas, caixa = floor(r*K)
//        rk[2n..3n) = regra de posição de cada item (só se posic == PCHAVE)
// Começa com K0 = LB caixas abertas (vazias). Se o item não cabe na caixa da chave,
// entra o plano B: BF (a mais cheia que serve; senão caixa nova), caixa seguinte
// (k+1, k+2, ... com volta; senão nova) ou caixa nova direto.
// Lamarck: se o plano B pôs o item noutra caixa ABERTA, a chave dele é reescrita para
// apontar essa caixa ((k+0,5)/K), e decodificar de novo dá a mesma solução sem plano B.
// Se foi para uma caixa nova, a chave fica como está (nenhuma chave aponta caixa ainda
// não aberta, e o resultado já se repete).
static inline bool cabeNaCaixa(const Caixa &c, int i, const TProblemData &data, int regra,
                               int &x, int &y)
{
    const long WH = (long)data.W * data.H;
    if (c.itens & data.conf[i]) return false;                          // conflito
    if (c.area + (long)data.w[i] * data.h[i] > WH) return false;       // área
    long s1 = 0, s2 = 0;
    return acharPosicao(c, data.w[i], data.h[i], regra, x, y, s1, s2); // geometria
}

double DecodificaCaixa(std::vector<double> &rk, const TProblemData &data,
                       std::vector<Posicao> *saida, bool reescrever, EstatPlanoB *est)
{
    const int n = data.nItems;
    const long WH = (long)data.W * data.H;
    int ordem[32];
    for (int i = 0; i < n; i++) ordem[i] = i;
    std::sort(ordem, ordem + n, [&](int a, int b) { return rk[a] < rk[b]; });

    std::vector<Caixa> caixas(std::max(1, data.LB));                  // K0 = LB completo
    for (Caixa &c : caixas) c.livres.push_back({0, 0, data.W, data.H});
    if (saida) saida->clear();

    for (int t = 0; t < n; t++) {
        const int i = ordem[t];
        const int regra = (g_cfg.posic == PCHAVE) ? ((rk[2 * n + i] < 0.5) ? BL : BSSF) : g_cfg.posic;
        const int K = (int)caixas.size();
        int k = std::min((int)(rk[n + i] * K), K - 1);                 // caixa da chave
        int x = 0, y = 0;
        int kSel = -1, xSel = 0, ySel = 0;
        if (cabeNaCaixa(caixas[k], i, data, regra, x, y)) {
            kSel = k; xSel = x; ySel = y;
        } else if (g_cfg.planob == PB_BF) {                            // a mais cheia que serve
            for (int j = 0; j < K; j++) {
                if (j == k || !cabeNaCaixa(caixas[j], i, data, regra, x, y)) continue;
                if (kSel < 0 || caixas[j].area > caixas[kSel].area) { kSel = j; xSel = x; ySel = y; }
            }
        } else if (g_cfg.planob == PB_SEGUINTE) {                      // k+1, k+2, ... (volta)
            for (int d = 1; d < K && kSel < 0; d++) {
                int j = (k + d) % K;
                if (cabeNaCaixa(caixas[j], i, data, regra, x, y)) { kSel = j; xSel = x; ySel = y; }
            }
        }                                                              // PB_NOVA: não procura
        if (est) est->itens++;
        if (kSel < 0) {                                                // caixa nova
            Caixa nova;
            nova.livres.push_back({0, 0, data.W, data.H});
            caixas.push_back(nova);
            kSel = (int)caixas.size() - 1; xSel = 0; ySel = 0;
            if (est) est->nova++;
        } else if (kSel != k) {
            if (est) est->outra++;
            if (reescrever) rk[n + i] = (kSel + 0.5) / K;               // Lamarck
        }
        colocar(caixas[kSel], xSel, ySel, data.w[i], data.h[i]);
        caixas[kSel].itens |= (1u << i);
        if (saida) saida->push_back({i, kSel, xSel, ySel});
    }

    // caixas usadas (as K0 iniciais podem ter sobrado vazias) e renumeração compacta
    std::vector<int> novoNum(caixas.size(), -1);
    int usadas = 0;
    long menor = WH;
    for (size_t k = 0; k < caixas.size(); k++)
        if (caixas[k].itens) { novoNum[k] = usadas++; menor = std::min(menor, caixas[k].area); }
    if (saida) for (Posicao &p : *saida) p.caixa = novoNum[p.caixa];
    double ofv = (double)usadas;
    if (g_cfg.aval == DESEMPATE) ofv += (double)menor / (double)WH;   // em [0,1)
    return ofv;
}

double Decoder(TSol &s, const TProblemData &data)
{
    double ofv;
    if (g_cfg.escolha == CAIXA) {
        EstatPlanoB est;
        ofv = DecodificaCaixa(s.rk, data, nullptr, g_cfg.lamarck, &est);
        g_pb_itens.fetch_add(est.itens, std::memory_order_relaxed);
        g_pb_outra.fetch_add(est.outra, std::memory_order_relaxed);
        g_pb_nova.fetch_add(est.nova, std::memory_order_relaxed);
    } else {
        ofv = Decodifica(s.rk, data, nullptr);
    }
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
