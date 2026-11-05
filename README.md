# TCC de irrigação inteligente

Execução prática de um protótipo de baixo custo com ESP32, sensores, controle de bomba e aprendizado de máquina. Entrega em **01/12/2026**. Redação acadêmica fora do escopo.

![Bancada atual de diagnóstico com LED e sensores](docs/imagens/bancada-diagnostico-led.png)

Ilustração conceitual da bancada atual, não esquema elétrico validado. [Fluxo de diagnóstico com LED](.archify/workflow-bancada-led-20261101-120000/bancada-led.html). O ensaio final com três vasos continua planejado; ainda não iniciado.

[Diagrama interativo do ensaio contínuo](.archify/workflow-ensaio-continuo-20261012-210000/ensaio-continuo.html).

Pastas anteriores em `.archify/` são versões históricas; o link acima identifica o fluxo atual.

## Documentação

- [MVP](docs/mvp.md): definição, funcionamento e critérios de demonstração.
- [Materiais](docs/materiais-tcc.md): quantidades, funções e reaproveitamento.
- [Ligações do protótipo](docs/ligacoes-prototipo.md): sinais, identificação das peças e sequência de montagem; GPIOs identificados, conectores de saída e potência pendentes.
- [Tarefas](docs/tasks-tcc.md): checklist até a entrega prática.
- [Ambiente local](docs/ambiente-local.md): execução, acesso e testes.
- [Protocolo de testes](docs/protocolo-testes.md): tratamentos, medição compartilhada, métricas e calendário.
- `docs/referencias/`: três documentos originais preservados.

## Escopo e estado

Arquitetura prática aprovada: ESP32/C++/ESP-IDF, MQTT/Mosquitto, Python/FastAPI, PostgreSQL, Grafana, pesagem com quatro sensores de carga de três fios e um HX711, medição de energia com INA3221 e acionamento de bancada por BD135 NPN (motores ainda não validados). Treinamento separado da inferência; decisão determinística e proteções locais no ESP32.

Software verificado com dados simulados em 12/10/2026: ingestão, controle T1/T2/T3, confirmação de ciclos, contingência, treinamento/inferência, painéis e restauração de backup. Firmware ESP-IDF com núcleo de segurança e drivers de sensores (05/11), publicando pelo Wi-Fi no broker do notebook; atuação das bombas bloqueada até validação do circuito. Calibração e validação física pendentes. O estado dos serviços deve ser consultado com `docker compose ps`.

Decisão aprovada: **opção A — 30 dias contínuos, um ESP32 e três vasos**, um por T1/T2/T3, com bombas sequenciais e medidores compartilhados. Orçamento fixo, sem ampliação de materiais ou troca de plantas na quinzena. Resultados descritivos com n=1 por tratamento; os períodos de 15 dias não são réplicas. Backend, simulador e núcleo do firmware foram adaptados para três unidades; operação física depende dos drivers e calibração. Configuração de referência: `config/experiment.json`.

Bancada identificada em 01/11/2026: ESP32 de 30 pinos, DHT22 configurado, HX711, INA3221 e três BD135 NPN. Sensores A/B/C correspondem a GPIO33/32/34. Os três bornes foram identificados com LED/resistor: original GPIO26, segundo testado GPIO25 e último GPIO27. A imagem conceitual foi produzida antes dessa identificação; o mapa atualizado está no guia. Bombas permanecem desconectadas; potência e calibração não estão validadas. Ver [ligações e diagnóstico](docs/ligacoes-prototipo.md). Cultura sugerida: alface em vasos de cerca de 3 litros; confirmar condições de bancada e calibração.

Planejamento original: bancada/modelo até 31/10 e comparação de 01/11 00:00 a 01/12 00:00 (São Paulo). Em 01/11 a bancada ainda está em diagnóstico com LED; não há evidência de início do ensaio físico. Replanejar a janela após calibração e preparação, sem contabilizar diagnóstico ou reduzir os 30 dias. Entrega em 01/12 deixa poucas horas após os 30 dias completos. Depende de aquisição, calibração e dados úteis; replanejar se não for viável. Metas de economia >20%, MAE <3 pontos e conformidade ≥95% são expectativas, não resultados garantidos. Grafana centraliza os painéis por vaso/período, qualidade, ciclos e intervenções; resultados físicos continuam pendentes.

## Estrutura

`firmware/`: ESP32; `backend/`: ingestão e serviços; `infra/`: configurações; `tests/`: testes; `tools/`: scripts; `data/`: dados; `models/`: modelos; `docs/`: documentação.
