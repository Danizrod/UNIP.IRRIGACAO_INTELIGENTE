# Etapas da entrega prática

Entrega em **01/12/2026**. Opção A: 30 dias contínuos, um ESP32 e três vasos (um por tratamento, sem réplicas), orçamento fixo. Quinzenas são análises complementares. Texto acadêmico fora do escopo. Itens marcados correspondem ao trabalho já verificado.

## Planejamento e aquisição

- [x] Avaliar referências e registrar a arquitetura aprovada.
- [x] Revisar materiais para um ESP32 e três ramos, sem expansão de orçamento/reservas.
- [ ] Definir orçamento, peças disponíveis e componentes a comprar.
- [ ] Conferir anúncios e dimensionar fonte, acionamento e conexões.
- [ ] Definir local, substrato, planta e responsável pela inspeção diária.
- [x] Definir protocolo operacional econômico e registrar limite estatístico de n=1 por tratamento.
- [x] Adotar comparação descritiva de 30 dias e quinzenas, sem inferência generalizável ou falsas réplicas.
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

## Diagnóstico da bancada com LED

- [x] Registrar GPIOs do sketch, BD135/INA3221 e sensores A/B/C identificados pelo usuário.
- [x] Preparar observador HTTP somente leitura e sketch isolado para pulsos individuais nos LEDs.
- [x] Compilar o diagnóstico Arduino, verificar backup completo de 4 MB e restaurar programa original após o teste.
- [x] Identificar o borne original com LED como GPIO26 por teste e observação do usuário.
- [x] Mapear os três bornes por teste com LED: original D26, segundo D25 e último D27.
- [ ] Associar canais do INA3221 aos ramos e registrar sensor/bomba/tratamento.
- [ ] Conferir alimentação, proteção indutiva, circuito de base, corrente das bombas e fonte.
- [ ] Identificar capacidade da célula de carga e validar massa máxima.
- [ ] Integrar drivers físicos ao ESP-IDF e levar leituras calibradas ao Grafana.
- [ ] Replanejar início/fim dos 30 dias após preparação; testes com LED não contam como ensaio.

## Firmware e controle

- [x] Implementar contratos, controle T1/T2/T3, comandos e confirmação em simulação.
- [x] Verificar ciclo completo, duplicidade, rejeições, desconexão e contingência simulada.
- [x] Preparar núcleo de segurança, MQTT/TLS e compilar firmware ESP-IDF padrão/simulado.
- [x] Verificar retenção por expiração e persistência de eventos com falhas/reboot simulados; compilar firmware atualizado.
- [x] Preparar provisionamento separado do histórico, sem flash automático; verificar gerador NVS e validações.
- [ ] Validar cortes de energia, desgaste NVS e reconciliação de ciclos interrompidos no dispositivo real.
- [x] Preparar partição de aplicativo de 1,5 MiB e compilar núcleo de três canais.
- [ ] Conferir flash real/mapa antes de gravar; não sobrescrever históricos de mapa anterior.
- [x] Registrar decisões, ciclos simulados, previsões e rejeições; atualizar painéis.
- [x] Implementar configuração/telemetria/modelo por vaso e fila global; verificar ciclos sequenciais simulados.
- [ ] Validar medição compartilhada por ciclo e registro de reposições/intervenções.
- [x] Consolidar consultas Grafana por tratamento/período, qualidade, ciclos locais, falhas e intervenções.
- [x] Implementar relatório descritivo com limites de quinzena, deduplicação e ausência sem consumo zero.

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

Datas condicionadas à aquisição, calibração e dados suficientes. Três vasos fornecem um caso por tratamento; quinzenas e leituras sucessivas não são réplicas. Não abreviar os 30 dias nem declarar início antes da preparação. Replanejar se necessário, mantendo orçamento fixo e limitações explícitas. Metas de desempenho são expectativas a testar.
