# Etapas da entrega prática

Entrega em **01/12/2026**. Ensaio planejado com um ESP32 e três vasos (um por tratamento, sem réplicas); unidade mínima demonstrável com um vaso. Texto acadêmico fora do escopo. Itens marcados correspondem ao trabalho já verificado.

## Planejamento e aquisição

- [x] Avaliar referências e registrar a arquitetura aprovada.
- [x] Revisar materiais para um único circuito, sem reservas obrigatórias.
- [ ] Definir orçamento, peças disponíveis e componentes a comprar.
- [ ] Conferir anúncios e dimensionar fonte, acionamento e conexões.
- [ ] Definir local, substrato, planta e responsável pela inspeção diária.
- [x] Definir protocolo operacional econômico e registrar limite estatístico de n=1 por tratamento.
- [ ] Resolver delineamento se for exigida inferência estatística generalizável; três vasos fixos não fornecem réplicas.
- [ ] Comprar e receber os materiais.

## Ambiente e montagem

- [x] Preparar backend, PostgreSQL, MQTT/TLS e Grafana.
- [x] Verificar ingestão e persistência com dados simulados.
- [ ] Preparar notebook definitivo, ESP-IDF, identidade do dispositivo e acesso pela rede.
- [x] Implementar backup e verificar restauração em banco temporário isolado.
- [x] Preparar serviço de backup diário enquanto Docker estiver ativo.
- [ ] Configurar backup e cópia adicional no notebook definitivo.
- [ ] Definir pinagem e montar circuito elétrico, hidráulico e plataforma de pesagem.
- [ ] Calibrar solo, pesagem e medição elétrica; registrar método e erro.
- [ ] Medir vazão/água entregue e testar vazamento, sifonamento e estabilidade.
- [ ] Definir faixa de umidade e limites de duração, volume e intervalo.

## Firmware e controle

- [x] Implementar contratos, controle T1/T2/T3, comandos e confirmação em simulação.
- [x] Verificar ciclo completo, duplicidade, rejeições, desconexão e contingência simulada.
- [x] Preparar núcleo de segurança, MQTT/TLS e compilar firmware ESP-IDF padrão/simulado.
- [x] Registrar decisões, ciclos simulados, previsões e rejeições; atualizar painéis.
- [ ] Implementar configuração/telemetria/modelo por vaso e fila global justa para três bombas sequenciais.
- [ ] Validar medição compartilhada por ciclo e registro de reposições/intervenções.
- [ ] Consolidar Grafana com resultados por tratamento, qualidade/cobertura, ciclos locais, falhas e intervenções.

Os itens seguintes exigem integração/validação com os componentes físicos:

- [ ] Implementar sensores e telemetria com identificação, calibração e horário.
- [ ] Implementar comandos, validade, deduplicação e confirmação de execução.
- [ ] Implementar desligamento no boot, watchdog e bloqueios de segurança.
- [ ] Implementar buffer, reenvio, contingência por histerese e retomada sincronizada.
- [ ] Implementar T1 fixo, T2 por histerese e decisão determinística de T3.
- [ ] Completar registros de decisões, ciclos, água, energia, falhas e painéis.
- [ ] Testar ciclo completo, desconexão, reinicialização, leituras inválidas e comandos rejeitados.

## Dados e aprendizado de máquina

- [x] Implementar exportação, alvo de seis horas e separação temporal com expurgo.
- [x] Implementar comparação de três algoritmos/persistência e modelo JSON versionado.
- [x] Verificar treinamento, inferência e decisão T3 com dados sintéticos separados.

Os itens seguintes dependem de dados físicos e do protocolo:

- [ ] Coletar dados físicos preliminares e registrar intervenções/reposições.
- [ ] Definir atributos, alvo de seis horas e uso de meteorologia aplicável à bancada.
- [ ] Separar treino, validação e teste temporal sem vazamento de dados.
- [ ] Comparar três algoritmos candidatos e previsão de persistência; avaliar MAE/RMSE.
- [ ] Versionar modelo e integrar inferência, separada do treinamento.
- [ ] Congelar modelo, parâmetros e protocolo antes da comparação.

## Avaliação e entrega

- [ ] Preparar condições equivalentes conforme o delineamento definido.
- [ ] Executar comparação T1/T2/T3 por pelo menos 30 dias, após preparação.
- [ ] Inspecionar diariamente, registrar falhas/fallback e preservar dados.
- [ ] Analisar água, energia da bomba, umidade, erro preditivo e métricas técnicas.
- [ ] Realizar simulações complementares separadas dos ensaios físicos.
- [ ] Usar análise adequada às réplicas e dependência temporal; registrar limitações.
- [ ] Finalizar gráficos, registros, esquema de montagem, calibração e instruções de execução.
- [ ] Organizar código, dados, modelos e configurações sem credenciais.
- [ ] Ensaiar demonstração, revisar critérios de aceite e entregar artefatos técnicos.

## Marcos propostos

- [ ] Coleta piloto, calibração, modelo e bancada prontos até **31/10**.
- [ ] Comparação de **01/11 00:00 a 01/12 00:00**, com 30 dias completos (São Paulo).
- [ ] Análise incremental em novembro e fechamento/entrega em **01/12**.

Datas condicionadas à aquisição, calibração e dados suficientes. Um vaso demonstra o MVP, mas não comprova automaticamente a comparação estatística. Não tratar leituras sucessivas como réplicas nem abreviar os 30 dias; replanejar com o orientador se necessário. Metas de desempenho são expectativas a testar.
