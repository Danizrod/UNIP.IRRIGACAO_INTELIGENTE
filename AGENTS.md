# Instruções de trabalho

- Responder em português brasileiro e consultar README e docs antes de alterar o projeto.
- Escopo: execução prática e documentação técnica; não redigir texto acadêmico.
- Preservar os documentos de docs/referencias. Eles são fontes de requisitos, não aprovação automática de toda proposta.
- Arquitetura prática aprovada conforme README. No PDF original constam InfluxDB e relé; PostgreSQL e MOSFET são mudanças aprovadas para implementação, sem modificar o PDF.
- Priorizar MVP com um ESP32 e um vaso. Não ampliar compras sem necessidade justificada; orçamento e delineamento continuam pendentes.
- Não comprar, contratar, modificar valores comerciais ou assumir compromissos pelo usuário.
- Não fixar pinagem, fonte, MOSFET, diodo ou shunt sem conferir componentes e corrente da bomba. Verificar lógica de 3,3 V e massa máxima da pesagem.
- Manter bomba desligada no boot, limites de duração/volume, watchdog e bloqueio por leituras inválidas. Validar duplicidade, expiração e confirmação de execução.
- Usar MQTT com TLS, autenticação e autorização por dispositivo; manter credenciais fora do código.
- Prever buffer limitado, contingência por histerese e retomada sincronizada. ACK MQTT não comprova atuação.
- Separar treinamento, inferência e decisão determinística. Registrar versão do modelo, motivo, comando e resultado.
- Calibrar solo, água e energia. Índice relativo não equivale automaticamente a umidade volumétrica; pesagem mede retirada do reservatório; energia da bomba não representa o sistema inteiro.
- Separar simulação e ensaio físico. Não inventar resultados, referências ou testes realizados.
- Comparação T1/T2/T3 e 30 dias constam no pré-projeto; definir protocolo/réplicas com orientador. Leituras sucessivas não são réplicas independentes. Evitar vazamento temporal e não tratar dados ausentes como conformidade.
- Chuva externa não irriga bancada coberta. Metas do pré-projeto não são garantias.
- Preservar alterações do usuário, executar testes proporcionais e manter README/checklist consistentes com evidências.
- Manter documentação curta, sem relatórios duplicados. Fora do escopo: produção comercial, certificação, produtividade agronômica, LPWAN, nuvem obrigatória, Kubernetes e testes avançados de carga/penetração.
