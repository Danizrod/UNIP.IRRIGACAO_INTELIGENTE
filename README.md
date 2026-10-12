# TCC de irrigação inteligente

Execução prática de um protótipo de baixo custo com ESP32, sensores, controle de bomba e aprendizado de máquina. Entrega em **01/12/2026**. Redação acadêmica fora do escopo.

## Documentação

- [MVP](docs/mvp.md): definição, funcionamento e critérios de demonstração.
- [Materiais](docs/materiais-tcc.md): quantidades, funções e reaproveitamento.
- [Tarefas](docs/tasks-tcc.md): checklist até a entrega prática.
- [Ambiente local](docs/ambiente-local.md): execução, acesso e testes.
- `docs/referencias/`: três documentos originais preservados.

## Escopo e estado

Arquitetura prática aprovada: ESP32/C++/ESP-IDF, MQTT/Mosquitto, Python/FastAPI, PostgreSQL, Grafana, pesagem com célula/HX711, medição de energia com INA219/INA226 e acionamento por MOSFET. Treinamento separado da inferência; decisão determinística e proteções locais no ESP32.

Software verificado com dados simulados em 12/10/2026: ingestão, controle T1/T2/T3, confirmação de ciclos, contingência, treinamento/inferência, painéis e restauração de backup. Firmware ESP-IDF preparado com núcleo de segurança; drivers, montagem, calibração e validação física ainda pendentes. O estado dos serviços deve ser consultado com `docker compose ps`.

Compra mínima proposta: **um ESP32 e um vaso**, sem reservas obrigatórias. Nenhum dos documentos originais fixa quantidade mínima de vasos. A seção 7.1 do pré-projeto menciona vasos genericamente; a seção 7.2 exige T1/T2/T3 e comparação por pelo menos 30 dias. A demonstração em um vaso não comprova automaticamente a avaliação estatística. Definir protocolo e réplicas com o orientador antes de ampliar a compra.

Orçamento e modelos dos componentes ainda não definidos. Fonte, acionamento e pinagem dependem das peças reais. Cultura sugerida: alface em vaso de cerca de 3 litros; confirmar condições de bancada e calibração.

Janela proposta para comparação: 28/10 a 27/11, com análise até 30/11. Depende de aquisição, calibração e dados úteis; replanejar se não for viável. Metas de economia >20%, MAE <3 pontos e conformidade ≥95% são expectativas, não resultados garantidos.

## Estrutura

`firmware/`: ESP32; `backend/`: ingestão e serviços; `infra/`: configurações; `tests/`: testes; `tools/`: scripts; `data/`: dados; `models/`: modelos; `docs/`: documentação.
