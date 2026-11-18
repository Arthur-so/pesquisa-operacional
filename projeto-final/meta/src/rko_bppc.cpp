// =====================================================================
//  main do RKO adaptado para o 2BPPC.
//  Baseado em RKO_Cpp_v2.0/Program/src/Main/main.cpp (Chaves et al., 2025).
//  Os arquivos genéricos do RKO (Data.h, Method.h, QLearning.h, MH/*.h)
//  são incluídos SEM modificação; só trocamos o Problem.h.
//
//  Diferenças em relação ao main original:
//   1. semente pela linha de comando, e cada thread é semeada (no original,
//      `private(rng)` cria cópias com a semente padrão do mt19937);
//   2. parada ao atingir o LB (ótimo provado), além do tempo;
//   3. arquivo de configuração e variante do decodificador por argumento;
//   4. saída numa linha "RESULTADO ..." + arquivo de solução (item caixa x y).
//
//  Uso: rko_bppc <instancia> --tempo T --semente S --conf arq.conf
//                [--escolha ff|bf|chave] [--posic bssf|bl]
//                [--aval caixas|desempate] [--sol arquivo.sol]
//  (rodar de dentro de meta/, pois o RKO lê config/Parameters*.txt)
// =====================================================================
#include <sys/time.h>
#include <math.h>
#include <cstring>
#include <ctime>
#include <iostream>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <vector>
#include <string.h>
#include <algorithm>
#include <utility>
#include <numeric>
#include <map>
#include <limits>
#include <random>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <fstream>
#include <omp.h>
#include <atomic>
#include <string>

#include "Data.h"

thread_local std::mt19937 rng;      // um gerador por thread (semeado em main)
std::atomic<bool> stop_execution(false);
std::vector<TSol> pool;

#include "Problem_2BPPC.h"
#include "Output.h"
#include "Method.h"
#include "QLearning.h"
#include "MH/BRKGA.h"
#include "MH/SA.h"
#include "MH/GRASP.h"
#include "MH/ILS.h"
#include "MH/VNS.h"
#include "MH/PSO.h"
#include "MH/GA.h"
#include "MH/BRKGA_CS.h"
#include "MH/LNS.h"
#include "MH/IPR.h"
#include "MH/MultiStart.h"

static const char *arg(int argc, char **argv, const char *nome, const char *padrao)
{
    for (int i = 2; i + 1 < argc; i++)
        if (strcmp(argv[i], nome) == 0) return argv[i + 1];
    return padrao;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        printf("uso: %s <instancia> --tempo T --semente S --conf arq.conf "
               "[--escolha ff|bf|chave] [--posic bssf|bl] [--aval caixas|desempate] "
               "[--sol saida.sol]\n", argv[0]);
        return 1;
    }
    char nameInstance[256];
    strncpy(nameInstance, argv[1], 255);
    TRunData runData;
    runData.MAXTIME = atoi(arg(argc, argv, "--tempo", "10"));
    unsigned semente = (unsigned)atol(arg(argc, argv, "--semente", "1"));
    const char *conf = arg(argc, argv, "--conf", "config/brkga.conf");
    std::string esc = arg(argc, argv, "--escolha", "ff");
    std::string pos = arg(argc, argv, "--posic", "bssf");
    std::string ava = arg(argc, argv, "--aval", "desempate");
    const char *arqSol = arg(argc, argv, "--sol", "");

    g_cfg.escolha = (esc == "bf") ? BF : (esc == "chave") ? CHAVE : FF;
    g_cfg.posic = (pos == "bl") ? BL : BSSF;
    g_cfg.aval = (ava == "caixas") ? SO_CAIXAS : DESEMPATE;

    // ----- metaheurísticas e parâmetros do arquivo de configuração -----
    #define TOTAL_MH 11
    const char *all_algorithms[TOTAL_MH] = {
        "BRKGA", "SA", "GRASP", "ILS", "VNS", "PSO", "GA", "LNS", "BRKGA-CS", "MultiStart", "IPR"};
    void (*all_functions[TOTAL_MH])(const TRunData &, const TProblemData &) = {
        BRKGA, SA, GRASP, ILS, VNS, PSO, GA, LNS, BRKGA_CS, MultiStart, IPR};
    #define MAX_MH 100
    void (*functions_MH[MAX_MH])(const TRunData &, const TProblemData &);
    const char *algorithms[MAX_MH];
    int NUM_MH = 0;

    FILE *fileConf = fopen(conf, "r");
    if (!fileConf) { printf("\nERRO: %s não encontrado\n", conf); exit(1); }
    char line[250];
    runData.MAXRUNS = 1; runData.debug = 0; runData.control = 0;
    runData.strategy = 1; runData.restart = 1; runData.sizePool = 10;
    while (fgets(line, sizeof(line), fileConf)) {
        line[strcspn(line, "\r\n")] = '\0';
        for (int i = 0; i < TOTAL_MH; ++i)
            if (strcmp(line, all_algorithms[i]) == 0) {
                functions_MH[NUM_MH] = all_functions[i];
                algorithms[NUM_MH] = all_algorithms[i];
                NUM_MH++;
            }
        if (strncmp(line, "control", 7) == 0) sscanf(line, "control %d", &runData.control);
        else if (strncmp(line, "strategy", 8) == 0) sscanf(line, "strategy %d", &runData.strategy);
        else if (strncmp(line, "restart", 7) == 0) sscanf(line, "restart %f", &runData.restart);
        else if (strncmp(line, "sizePool", 8) == 0) sscanf(line, "sizePool %d", &runData.sizePool);
    }
    fclose(fileConf);
    if (NUM_MH == 0) { printf("\nERRO: nenhuma metaheurística em %s\n", conf); exit(1); }

    TProblemData data;
    ReadData(nameInstance, data);
    const int tempoMax = runData.MAXTIME;     // MAXTIME vira 0 se o alvo for atingido
    g_runData = &runData;

    // ------------------------------ execução ------------------------------
    rng.seed(semente);
    double start_time = get_time_in_seconds(), end_time = start_time;
    g_start_time = start_time;
    stop_execution.store(false);

    pool.clear();
    pool.resize(runData.sizePool);
    CreatePoolSolutions(data, runData.sizePool);

    omp_set_num_threads(NUM_MH);
    #pragma omp parallel shared(pool, stop_execution)
    {
        // cada thread com sua própria semente (reprodutível dada a semente)
        rng.seed(semente * 1000003u + 7919u * (omp_get_thread_num() + 1));
        while (end_time - start_time < tempoMax && !g_alvo.load()) {
            stop_execution.store(false);
            #pragma omp for
            for (int i = 0; i < NUM_MH; ++i) {
                #pragma omp cancellation point for
                functions_MH[i](runData, data);
                stop_execution.store(true);
                #pragma omp cancel for
            }
            #pragma omp single
            {
                end_time = get_time_in_seconds();
                if (end_time - start_time < tempoMax && !g_alvo.load())
                    CreatePoolSolutions(data, runData.sizePool);
            }
        }
    }
    end_time = get_time_in_seconds();

    // ------------------------------ saída ---------------------------------
    std::vector<Posicao> sol;
    double ofv = Decodifica(g_best_rk, data, &sol);
    int caixas = 0;
    for (auto &p : sol) caixas = std::max(caixas, p.caixa + 1);
    std::string mhs;
    for (int i = 0; i < NUM_MH; i++) { if (i) mhs += "+"; mhs += algorithms[i]; }
    printf("RESULTADO %s semente=%u caixas=%d ofv=%.6f LB=%d tempo_melhor=%.3f "
           "tempo_total=%.3f alvo=%d mh=%s escolha=%s posic=%s aval=%s\n",
           nameInstance, semente, caixas, ofv, data.LB, g_best_time, end_time - start_time,
           (int)g_alvo.load(), mhs.c_str(), esc.c_str(), pos.c_str(), ava.c_str());
    if (arqSol[0]) {
        FILE *f = fopen(arqSol, "w");
        fprintf(f, "# %s caixas=%d mh=%s semente=%u\n", nameInstance, caixas, mhs.c_str(), semente);
        for (auto &p : sol) fprintf(f, "%d %d %d %d\n", p.item + 1, p.caixa + 1, p.x, p.y);
        fclose(f);
    }
    FreeMemoryProblem(data);
    return 0;
}
