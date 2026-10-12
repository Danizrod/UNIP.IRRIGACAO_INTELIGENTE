# Materiais para montagem do TCC

Lista para o MVP com **um ESP32 e um vaso**. Quantidades sem peças de reserva. A expansão experimental será definida separadamente com o orientador.

As quantidades indicam o que deve estar disponível, não o que obrigatoriamente precisa ser comprado. Reutilizar cabo USB, fonte compatível, recipientes, vaso, bandeja, suportes e ferramentas; emprestar instrumentos quando possível. Não há exigência explícita de mais de um vaso nos documentos iniciais. O pré-projeto exige comparação T1/T2/T3 por 30 dias, mas não fixa quantidade de vasos; definir o protocolo com o orientador.

## Componentes e montagem

| Material | Quantidade | Para que será usado |
| --- | --- | --- |
| ESP32 DevKit com módulo WROOM e conexão USB | 1 | Ler sensores, enviar dados e controlar a bomba com proteções locais. |
| Cabo USB de dados compatível com a placa | 1 | Programar e alimentar o ESP32 pelo notebook. |
| Sensor capacitivo de umidade do solo | 1 | Medir a condição de umidade do substrato após calibração. |
| DHT22 | 1 | Medir temperatura e umidade do ar na bancada. |
| Célula de carga de barra, ponte completa, capacidade candidata de 5 kg | 1 | Pesar o reservatório para estimar a água retirada em cada ciclo. |
| Módulo HX711 | 1 | Converter o sinal da célula de carga para leitura pelo ESP32. |
| Módulo INA219 | 1 | Medir tensão e corrente do ramo da bomba para calcular energia. |
| Mini bomba submersível DC compatível com operação a 5 V | 1 | Transferir água do reservatório ao vaso. |
| MOSFET compatível com comando de 3,3 V | 1 | Ligar e desligar a bomba pelo ESP32. |
| Diodo de proteção e resistores do acionamento | 1 conjunto | Proteger o circuito e manter a bomba desligada quando não houver comando. |
| Fonte de 5 V para a bomba | 1 | Alimentar o motor sem usar a alimentação da placa ESP32. |
| Fios de potência, bornes e fusível/proteção | 1 conjunto | Conectar e proteger a alimentação e o acionamento. |
| Protoboard/placa de montagem e jumpers de sinal | 1 conjunto | Montar as conexões dos sensores e do controlador. |
| Reservatório com tampa, aproximadamente 1 litro | 1 | Armazenar a água e permitir a medição por pesagem. |
| Plataforma de pesagem, parafusos e suportes | 1 conjunto | Fixar a célula de carga e apoiar o reservatório. |
| Mangueira compatível com a bomba | Cerca de 1–2 m | Conduzir a água até o vaso. |
| Conexões e fixadores da mangueira | 1 conjunto | Evitar vazamentos e manter o ponto de irrigação estável. |
| Vaso de aproximadamente 3 litros | 1 | Receber o substrato, a planta e o sensor de solo. |
| Bandeja de drenagem | 1 | Coletar a água drenada e proteger a bancada. |
| Substrato comercial para hortaliças, de lote único | Cerca de 5 litros | Preencher o vaso e realizar a calibração inicial. |
| Muda de alface uniforme | 1 | Servir como condição de referência do protótipo com planta. |

Fonte, MOSFET, diodo, resistores e fusível serão especificados após conferir a bomba e os módulos escolhidos. A capacidade da célula de carga deve considerar toda a montagem com o reservatório cheio. Alface, volume do vaso e substrato são propostas de bancada ainda sujeitas à definição do experimento.

## Instrumentos e recursos de apoio

| Recurso | Quantidade | Para que será usado |
| --- | --- | --- |
| Multímetro | 1, próprio ou emprestado | Conferir alimentação e medições elétricas. |
| Balança de referência e massas conhecidas | 1 conjunto, próprio ou emprestado | Calibrar e verificar a pesagem do reservatório. |
| Recipiente de coleta e utensílio graduado | 1 conjunto | Conferir água entregue e vazão da bomba. |
| Ferramentas de montagem e, se necessário, solda | 1 conjunto, próprio ou emprestado | Preparar fios, fixar componentes e concluir conexões. |
| Notebook | 1, já disponível | Executar backend, banco, MQTT, Grafana e treinamento dos modelos. |
| Rede Wi-Fi e tomada próximas | Disponíveis na bancada | Conectar o ESP32 ao ambiente local e alimentar o sistema. |

O software será executado localmente com ESP-IDF, Docker Compose, Mosquitto, FastAPI, PostgreSQL, Grafana e bibliotecas Python de dados/ML. A base de integração já foi verificada com dados simulados.

## Expansão opcional para três vasos

Acrescentar **dois sensores de solo, duas bombas, dois conjuntos de acionamento, dois vasos com bandejas e duas mudas**, além de substrato e mangueiras suficientes. Manter o mesmo ESP32. Compartilhar reservatório, pesagem e INA219 exige validar uma bomba por vez e identificar as medições de cada ciclo.

Essa expansão permite comparação descritiva entre T1, T2 e T3, mas não fornece réplicas por tratamento. Não é uma compra obrigatória para demonstrar o MVP.

Orçamento ainda a definir. Não comprar reservas ou expansão antecipadamente. Conferir os modelos reais antes de fechar fonte e acionamento; priorizar reaproveitamento e instrumentos emprestados.
