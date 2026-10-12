# Protocolo prático T1/T2/T3

Decisão aprovada em 12/10/2026: **opção A — ensaio simultâneo contínuo de 30 dias**. Orçamento fixo, sem ampliar materiais. Objetivo: comparar economia e desempenho observados nesta bancada. Nenhuma medição física realizada.

## Bancada e alcance estatístico

Adotar três vasos equivalentes, um por tratamento fixo, com um ESP32 e três sensores/bombas/acionamentos. Compartilhar DHT22, reservatório, célula/HX711 e INA219. Manter tratamentos durante todo o ensaio e sortear qual vaso recebe cada um. Não ampliar compras automaticamente.

Este é o mínimo para observar os três tratamentos simultaneamente: **n=1 vaso por tratamento**. Permite estatística descritiva dos casos, séries temporais e avaliação técnica; não separa efeito do tratamento de particularidades da planta/vaso. Dias, ciclos e leituras não são réplicas independentes. Não usar teste entre tratamentos tratando milhares de leituras como tamanho amostral nem afirmar efeitos generalizáveis.

Analisar o total de 30 dias e, complementarmente, dias 1–15 e 16–30. **Não são duas rodadas nem duas réplicas**: manter plantas, substrato, tratamentos, modelo e parâmetros durante todo o período. A passagem pela quinzena não reinicia o controle nem o consumo acumulado.

Base metodológica: [NIST — princípios de delineamento](https://itl.nist.gov/div898/handbook/pmd/section3/pmd33.htm). Não há aprovação estatística inferencial presumida.

## Condições e parâmetros

- Vasos do mesmo modelo (~3 L), substrato do mesmo lote e mesma massa seca inicial; mudas de alface semelhantes, mesma data e preparo. Registrar diferenças iniciais.
- Bancada coberta, mesmo regime de luz, suportes e drenagem individuais. Sortear posições iniciais e usar rodízio de posições previamente registrado, sem mudar tratamento nem forçar fios/mangueiras.
- Sensor em posição/profundidade equivalente, calibrado individualmente; calibrar pesagem, água entregue e energia de cada ramo. Condição inicial definida por pesagem/solo após drenagem estabilizada.
- Aquisição proposta: leitura por vaso a cada 60 s; pesagem/corrente mais frequentes durante ciclos, frequência final definida por ensaio de ruído e resposta. DHT22 comum, sem atribuir três medições ambientais independentes.
- Piloto anterior ao ensaio: medir secagem e resposta a doses pequenas, drenagem, vazão e tempo de estabilização. Definir faixa operacional do índice relativo e histerese maior que a oscilação de medição. Não chamar esse índice de umidade volumétrica.
- T1: escolher dose e intervalo com base na demanda do piloto, congelar ambos; referência competente, sem excesso proposital para favorecer T2/T3.
- T2: dose calibrada, limite inferior e rearme superior; verificar que a lógica rearmará no piloto. T3: mesma faixa/dose/proteções, antecipação baseada na previsão de seis horas. Modelo prevê solo observado sob a política coletada, não secagem sem irrigação.
- Mesmos limites de segurança (água mínima, dose máxima, duração máxima e intervalo mínimo) para todos. Valores dependem dos componentes e das medições; não importar limites sintéticos.
- Congelar parâmetros, modelo, critérios de validade e protocolo antes do início. Contingência de T3 identificada separadamente, inclusive tempo operando sem previsão.

## Reservatório e medidores compartilhados

As leituras dos vasos ocorrerão no mesmo período; ciclos de irrigação serão **sequenciais**. Configurações e históricos separados por dispositivo/experimento/vaso; uma fila global por ESP32 protege a instrumentação comum. Não liberar bomba publicada/iniciada apenas porque o comando expirou: exigir resultado terminal e estabilização.

1. Fila identificada por experimento, vaso, tratamento e UUID; intertravamento global permite uma única bomba ativa, inclusive em contingência. Evitar prioridade fixa que favoreça um tratamento; registrar espera.
2. Confirmar bombas desligadas, estabilizar pesagem e registrar massa inicial. Acionar somente o ramo associado ao vaso.
3. Integrar tensão × corrente no ramo comum das bombas, desligar, estabilizar e registrar massa final. Atribuir retirada/energia somente ao ciclo ativo; leituras comuns do reservatório não são consumo por vaso.
4. Persistir resultado, qualidade, horários, versão de calibração e confirmação antes de liberar o próximo ciclo. Falta de confirmação impede presumir que o ramo desligou.
5. Reposição de água somente com todos os ramos desligados, fora de ciclos; registrar intervenção e nova referência. Reposição, vibração, vazamento, sifonamento ou peso instável invalidam a medição afetada, sem fabricar volume zero.

Pesar retirada não garante água entregue: verificar drenagem, vazamentos e variação de água nas mangueiras. INA219 mede bombas, não o consumo total do sistema. Dimensionar reservatório pela demanda conjunta e frequência de inspeção; ~1 L pode exigir reposição frequente. Dimensionar célula para toda a massa e fonte para o ramo escolhido, sem pressupor componentes comerciais.

## Resultados e visibilidade

Grafana será a visualização central; não criar segunda interface. API/scripts continuam responsáveis por configuração/provisionamento, sem expor segredos no painel.

Resultado principal: água retirada acumulada por vaso na janela válida comum, acompanhada obrigatoriamente da condição do solo. Menor consumo com solo fora da faixa não será classificado automaticamente como desempenho melhor. Energia, confiabilidade e erro preditivo são resultados complementares.

- Por vaso/tratamento: água e energia acumuladas e diárias, quantidade/duração de ciclos, solo na faixa e fora dela, validade/cobertura de dados, erros/falhas e espera na fila.
- Economia observada: `100 × (1 − consumo_Tx / consumo_T1)` na mesma janela com cobertura comparável; T1=0 gera resultado indefinido. Mostrar consumo bruto e ciclos sem medição válida; não apresentar economia completa quando consumo está ausente.
- T3: MAE/RMSE contra observação válida de seis horas depois, pareada por vaso/calibração/modelo; avaliar teste temporal separado do treinamento. Mostrar quantidade de pares válidos e cobertura, sem erro fictício para alvos ausentes.
- Falhas/intervenções: identidade, horário, motivo, responsável, efeito na medição, início/fim e ação tomada. Incluir reposição, manutenção, reboot, contingência, leituras inválidas, perda de dados e ciclo incompleto.
- Manter dados brutos e metadados. Estatística de dias/ciclos descreve a série observada; não é evidência de replicação biológica.

Grafana centraliza linhas de solo por vaso/tratamento, comandos, ciclos, decisões, consumo válido observado, cobertura, contingência, intervenções e rejeições. Seletor total30/primeira15/ultima15 é período de análise, não réplica. Relatório descritivo: `tools/experiment_analysis.py`, usando `config/experiment.json`. Ciclos são alocados pelo horário do resultado terminal; comandos sem resultado são apontados, não estimados como consumo zero. Gráficos e alertas adicionais dependem de evidências físicas.

## Calendário e início

- Até 31/10: componentes, montagem, calibração, coleta piloto, modelo e testes físicos aprovados. Software sem drivers físicos não significa bancada concluída.
- Ensaio: **01/11/2026 00:00 a 01/12/2026 00:00**, horário de São Paulo — 30 dias completos. Usar intervalo fechado no início e aberto no fim; definir esses limites explicitamente na análise.
- Durante novembro: backups, inspeção diária, gráficos e análise incremental; congelar a coleta só no fim. Entrega em 01/12 deixa poucas horas para fechamento. Modelo T3 precisa existir antes de novembro; treinamento em novembro não substitui 30 dias de avaliação de um modelo congelado.
- Sem bancada/calibração/modelo prontos, não declarar início dos 30 dias nem substituir falhas por simulação. Replanejar prazo ou alcance se não cumprir critérios.

Manter identidade e tratamento de cada vaso; congelar calibração, parâmetros e modelo antes da coleta. Próximas etapas: notebook, drivers, montagem, calibração e ensaio físico. Aquisição e preparação do notebook serão executadas quando o usuário indicar.
