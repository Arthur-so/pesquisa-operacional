# Dúvidas para levar ao professor

P1–P4 são as **principais** (marcadores vermelhos em `docs/fluxo/fluxo_projeto.pdf`); S1–S7 são secundárias (marcadores cinza) e podem ficar para depois.

# Principais

## P1. Os dois métodos resolvem as 64 instâncias muito rápido. Devemos usar instâncias sintéticas maiores ou deixar o problema mais difícil?
- Contexto: o exato prova os 64 ótimos em 150 s no total (pior caso: 41 s), e o BRKGA acha o ótimo em 100% das execuções, em 0,05 s em média. A comparação exato × metaheurística fica pouco informativa, porque os dois "ganham" sempre.
- Opções: (a) manter só as 64 da literatura; (b) gerar instâncias sintéticas maiores (n = 50, 100) pelo mesmo procedimento das originais (tipos I–IV, densidades 7–16%), onde o exato deve estourar 3600 s e a metaheurística passa a ser necessária; (c) deixar o problema mais difícil (ex.: permitir rotação, caixas de tamanhos diferentes), o que muda o modelo já escrito no artigo.
- O que os testes iniciais mostraram: exato com 150 s no total e máximo de 41,5 s (instância 53); BRKGA com 100% das 320 execuções no ótimo.
- Inclinação: (b): criar 16 instâncias novas, maiores, no mesmo formato das 64 (arquivos de dados de entrada). Por exemplo: 4 tipos (I–IV) × 2 tamanhos (n = 50 e n = 100 itens) × 2 densidades de conflito (7% e 16%). As 64 da literatura continuam sendo a base do artigo; as novas servem para ver os métodos em casos onde o exato não resolve tudo rápido.
- Resposta do professor:

## P2. É isso que o senhor espera da parte de metaheurísticas?
- Contexto: foi usado o RKO v2.0.1 com um decodificador próprio: as chaves dão a ordem dos itens; cada item vai para a primeira caixa sem conflito onde cabe (posicionamento Bottom-Left); a nota é o nº de caixas mais um desempate (área da caixa mais vazia). Toda solução é viável. O BRKGA do RKO sozinho foi comparado com o RKO completo (10 metaheurísticas), e foram testadas 12 variantes do decodificador.
- Opções: (a) manter assim (BRKGA × RKO); (b) comparar também as outras metaheurísticas do RKO sozinhas (SA, ILS, VNS, ...), todas com o mesmo decodificador, o que é barato porque muda só a configuração; (c) investir em outra representação ou decodificador.
- O que os testes iniciais mostraram: BRKGA com 100% das execuções no ótimo e 0,05 s até a melhor solução; RKO com 99,7% e 0,03 s. Das variantes, só o desempate tem efeito claro (instância 48: 0–20% de acerto sem ele, 60–100% com ele).
- Inclinação: (a) + (b), que atende ao "comparar metaheurísticas diferentes" pedido em aula.
- Resposta do professor:

## P3. O que fazer nas instâncias em que o LB não é atingível?
- Contexto: a metaheurística só sabe que achou o ótimo quando o nº de caixas é igual ao LB. Em 32 das 64 instâncias o ótimo é maior que o LB (em 25 por 1 caixa, em 7 por 2; quase todas dos tipos I e II). Nelas, a metaheurística acha o ótimo cedo, mas não consegue provar e segue até o tempo limite.
- Opções: (a) parar por tempo e avaliar pelo gap até o ótimo do exato, como a literatura faz com a melhor solução conhecida; (b) parar por estagnação, após N avaliações do decodificador sem melhora, como em Hammami, Rekik e Coelho (2020, Computers & Operations Research 123), critério que não depende da máquina; (c) usar um LB mais forte (o de Carlier et al., 2007, usado no artigo-base), para mais instâncias pararem cedo.
- O que os testes iniciais mostraram: com limite de 1 s de relógio, o resultado mudou com a carga da máquina: a BF+BL acertou 0 de 5 na instância 48 com 10 execuções simultâneas e 5 de 5 com cada execução num núcleo fixo (decisoes.md, C3a).
- Inclinação: (b) + (c), avaliando sempre pelo gap até o ótimo do exato.
- Resposta do professor:

> **Antes da pergunta: o que é o laço de cortes.** O modelo exato precisa de uma restrição (5) para cada grupo de itens que não cabe numa caixa; com 25 itens são 2^25 ≈ 33 milhões de grupos, impossível escrever todas. O laço: (1) resolve o modelo sem essas restrições (o "mestre"), que distribui os itens respeitando área e conflitos, sem conferir a geometria; (2) confere, com um segundo modelo exato (2D-OPP), se os itens de cada caixa realmente cabem; (3) se um grupo não cabe, acrescenta uma restrição proibindo esse grupo (um "corte") e resolve de novo; (4) quando todas as caixas cabem, a solução é ótima. Na instância 53 foram 41 rodadas e 69 cortes. No artigo-base, os cortes entram durante uma única resolução (lazy constraints via callbacks, em C++ com CPLEX); o AMPL não tem esse recurso, por isso o laço é um script que chama o solver várias vezes.

## P4. O laço de cortes em script AMPL é aceito como "método exato"?
- Contexto: o AMPL não tem callbacks, então o modelo (1)–(14) é resolvido num laço `.run`: resolve o mestre, testa cada caixa com um 2D-OPP exato (PLI) e, se um grupo não cabe, acrescenta o corte (5) e resolve de novo.
- Opções: (a) aceitar o laço em AMPL como está; (b) exigir um único `solve`, o que não é possível com o número exponencial de restrições (5); (c) implementar com callbacks fora do AMPL.
- O que os testes iniciais mostraram: 64/64 instâncias com ótimo provado, 150 s no total (máx. 41,5 s na 53). Os cortes foram reconferidos por outro método exato (CP-SAT): todos válidos.
- Inclinação: (a), já implementado e validado.
- Resposta do professor:


# Secundárias (podem ficar para depois)

## S1. n chaves (só a ordem) ou 2n chaves (ordem + regra de escolha da caixa por item)?
- Contexto: as duas foram implementadas. Na versão 2n, a chave n+i decide se o item i usa First Fit ou Best Fit.
- Opções: (a) n chaves; (b) 2n chaves.
- O que os testes iniciais mostraram: 2n chaves não melhoraram nenhuma instância (96,9–98,5% no ótimo contra 100% da melhor variante com n chaves; 13 instâncias × 5 sementes × 2 s).
- Inclinação: (a); 2n fica como variante citada no artigo.
- Resposta do professor:

## S2. O desempate na avaliação (área da caixa mais vazia ÷ WH) é adequado?
- Contexto: valor = nº de caixas + área ocupada na caixa mais vazia ÷ WH, que fica em [0,1). Guia a busca para esvaziar uma caixa.
- Opções: (a) só o nº de caixas; (b) esse desempate; (c) outro (ex.: Σ ocupação², comum no bin packing).
- O que os testes iniciais mostraram: na instância 48, sem desempate, 0–20% das execuções chegam ao ótimo; com desempate, 60–100%. Nas demais, não há diferença.
- Inclinação: (b). Testar (c) se o senhor sugerir.
- Resposta do professor:

## S3. A forma de semear as threads do RKO está correta?
- Contexto: no `main.cpp` do RKO v2.0, `#pragma omp parallel private(rng)` dá a cada thread uma cópia do gerador com a semente padrão; a semente escolhida só afeta o pool inicial. No `main` adaptado, cada thread é semeada a partir da semente da execução (o código genérico do RKO ficou intocado).
- Opções: (a) manter a correção; (b) usar o main original.
- O que os testes iniciais mostraram: com a correção, sementes diferentes geram execuções diferentes e reprodutíveis.
- Inclinação: (a). Talvez seja útil avisar os mantenedores do RKO.
- Resposta do professor:

## S4. Quantas execuções independentes por instância e quais métricas reportar?
- Contexto: em aula foram sugeridas ~100 sementes. Hammami et al. (2020) usam 20 execuções por instância e reportam: nº de soluções ótimas/BKS encontradas, gap médio até a BKS, melhor e média das execuções, desvio entre melhor e média (estabilidade) e tempo até achar a BKS. Neste projeto, a referência é o ótimo do método exato.
- Opções: (a) 100 execuções; (b) 20–30 execuções; (c) 100 no BRKGA e menos no RKO completo, que usa 10 threads por execução.
- O que os testes iniciais mostraram: 100 execuções × 1 s custam ~5 min de máquina para o BRKGA (10 em paralelo) e ~1 h para o RKO completo. Com parada por estagnação, o custo cai.
- Inclinação: (a), se o critério de estagnação for aceito, reportando as métricas acima + performance profile e testes estatísticos (Wilcoxon/Friedman), que o artigo citado não usa.
- Resposta do professor:

## S5. Comparar o RKO completo (10 threads) com o BRKGA (1 thread) e com o exato (1 thread) é justo?
- Contexto: o RKO roda 10 metaheurísticas em paralelo, uma por thread. Além disso, nos testes o BRKGA sozinho usou parâmetros fixos (`control 0`, ParametersOffline.txt) e o RKO usou ajuste automático por Q-Learning (`control 1`), o que também influencia a comparação.
- Opções: (a) mesmo tempo de parede, informando os núcleos; (b) mesmo tempo de CPU (RKO com 1/10 do tempo de parede); (c) RKO com menos metaheurísticas; e, em qualquer caso, usar o mesmo modo de parâmetros (fixos ou Q-Learning) nos dois.
- O que os testes iniciais mostraram: 64 inst. × 5 sementes × 1 s: BRKGA 100% e RKO 99,7% das execuções no ótimo. Tempo médio até a melhor solução: BRKGA 0,052 s (1 thread) e RKO 0,030 s (10 threads). Na qualidade, empatam; o RKO é ~1,7× mais rápido usando 10× mais threads (que dividem 4 núcleos rápidos e 4 lentos).
- Inclinação: (a), deixando claro na tabela o número de threads de cada método.
- Resposta do professor:

## S6. Os dados: a instância 01 do zip é cópia da 02, e as 53–64 não vieram no zip. Podemos reconstruí-las?
- Contexto: a 01 foi reconstruída como "49 com caixa 30×30" e as 53–64 foram geradas copiando as originais indicadas no artigo-base com caixa 60×60. A regra foi conferida nas cópias existentes (50≡18, 51≡35, 52≡04).
- Opções: (a) usar as reconstruídas; (b) excluir a 01 e as 53–64.
- O que os testes iniciais mostraram: as reconstruídas têm os tipos, densidades e o comportamento esperados (a 53 e a 55 seguem entre as mais difíceis do exato).
- Inclinação: (a), declarando isso no artigo.
- Resposta do professor:

## S7. O IPR do RKO v2.0 não confere a flag de parada: é intencional?
- Contexto: o IPR só olha `runData.MAXTIME`. Quando outra metaheurística sinaliza parada (por exemplo, ótimo provado), as demais threads esperam o IPR até o fim do tempo. Contorno adotado: o decodificador zera o `MAXTIME`, sem alterar o RKO.
- Opções: (a) manter o contorno; (b) remover o IPR da configuração; (c) avisar os mantenedores.
- O que os testes iniciais mostraram: na 55, o RKO achava o ótimo em 0,03 s e terminava em 5 s; com o contorno, termina em 0,008 s.
- Inclinação: (a) + (c).
- Resposta do professor:
